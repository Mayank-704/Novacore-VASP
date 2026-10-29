"""Follow Bitcoin outputs forward from a seed address until they reach a labeled or exchange-like address.

Unlike an account-based chain, Bitcoin spends specific outputs. The tracer follows the exact output
(txid:vout) the seed received, finds the transaction that spent it, and moves on to that
transaction's outputs. A 'hop' is a payment to a different owner; change back to the sender does not count.
"""
from collections import deque

from .heuristics import analyze_address, detect_change
from .models import btc
from .profile import build_profile, trace_back
from .scoring import score
from .validate import normalize_address


def trace(seed, provider, labels, max_hops=3, start=None, end=None, max_states=300, max_txs=100):
    seed = normalize_address(seed)
    history_cache, analysis_cache, excluded = {}, {}, set()
    truncated_addresses = set()

    def history(address):
        if address not in history_cache:
            txs, cut = provider.address_txs(address, max_txs)
            history_cache[address] = txs
            if cut:
                truncated_addresses.add(address)
        return history_cache[address]

    def analysis(address):
        if address not in analysis_cache:
            analysis_cache[address] = analyze_address(address, history(address), labels)
        return analysis_cache[address]

    def usable(tx):
        if not tx['confirmed']:
            excluded.add(tx['txid'])
            return False
        if (start and tx['time'] < start) or (end and tx['time'] > end):
            excluded.add(tx['txid'])
            return False
        return True

    seed_txs = history(seed)
    received = [(tx, o) for tx in seed_txs if usable(tx) for o in tx['outputs'] if o['address'] == seed]
    total_received = sum(o['value'] for _, o in received) or 1
    candidates, seen_candidates, unspent_ends, boundaries = [], set(), set(), set()
    discovered, used_steps = {seed}, {}

    def add_candidate(match, label, via, address, hops, steps, flags, value):
        key = (address, tuple(s['id'] for s in steps))
        if key in seen_candidates:
            return
        seen_candidates.add(key)
        level, points, reasons = score(match, label, hops, flags['weak'], flags['unresolved'],
                                       address in truncated_addresses)
        if via:
            reasons.append(f'Matched through related address {via}')
        candidates.append({'vasp': label['entity'], 'address': address, 'hops': hops, 'transactions': steps,
                           'label': label, 'match': match, 'via': via, 'confidence': level,
                           'confidence_score': points, 'reasons': reasons, 'amount': btc(value),
                           'share_upper_bound': round(min(1.0, value / total_received), 4)})

    if seed in labels:
        add_candidate('label', labels[seed], None, seed, 0, [], {'weak': 0, 'unresolved': 0}, total_received)

    queue = deque()
    if seed not in labels:
        for tx, o in received:
            queue.append((tx['txid'], o['n'], seed, 0, [], {'weak': 0, 'unresolved': 0}))
    seen_outputs, expansions = set(), 0

    while queue and expansions < max_states:
        txid, vout, address, hops, steps, flags = queue.popleft()
        if (txid, vout) in seen_outputs:
            continue
        seen_outputs.add((txid, vout))
        expansions += 1
        spender = next((tx for tx in history(address) if usable(tx)
                        and any(i['txid'] == txid and i['vout'] == vout for i in tx['inputs'])), None)
        if spender is None:
            unspent_ends.add(address)
            continue
        input_addresses = {i['address'] for i in spender['inputs'] if i['address']}
        outs = [o for o in spender['outputs'] if o['address']]
        change_index, strength = detect_change(spender, input_addresses)
        others = [o for o in outs if o['address'] not in input_addresses]
        unresolved = len(others) >= 2 and change_index is None
        for o in outs:
            if o['address'] in input_addresses:
                kind = 'change-reuse'
            elif o['n'] == change_index:
                kind = 'change'
            else:
                kind = 'payment'
            step = {'id': f"{spender['txid']}:{o['n']}", 'txid': spender['txid'], 'from': address,
                    'to': o['address'], 'amount': btc(o['value']), 'asset': 'BTC',
                    'timestamp': spender['time'].isoformat(), 'kind': kind, 'direction': 'out'}
            new_flags = {'weak': flags['weak'] + (kind == 'change' and strength == 'weak'),
                         'unresolved': flags['unresolved'] + (kind == 'payment' and unresolved)}
            new_steps = steps + [step]
            if kind != 'payment':
                discovered.add(o['address'])
                used_steps[step['id']] = step
                queue.append((spender['txid'], o['n'], o['address'], hops, new_steps, new_flags))
                continue
            if hops + 1 > max_hops:
                boundaries.add(address)
                continue
            discovered.add(o['address'])
            used_steps[step['id']] = step
            found = analysis(o['address'])
            if o['address'] in labels:
                add_candidate('label', labels[o['address']], None, o['address'], hops + 1, new_steps, new_flags, o['value'])
                continue
            if found['cluster']:
                label, via = found['cluster']
                add_candidate('cluster', label, via, o['address'], hops + 1, new_steps, new_flags, o['value'])
                continue
            if found['deposit_like']:
                pattern = {'entity': 'Possible exchange deposit address (no label)', 'type': 'deposit-pattern',
                           'source': f"Heuristic: {found['senders']} different senders, then single-output sweeps",
                           'verified': False}
                add_candidate('pattern', pattern, None, o['address'], hops + 1, new_steps, new_flags, o['value'])
            queue.append((spender['txid'], o['n'], o['address'], hops + 1, new_steps, new_flags))

    def rank(c):
        return (c['hops'], -c['confidence_score'], c['address'])

    candidates.sort(key=rank)
    labeled = [c for c in candidates if c['match'] != 'pattern']
    nearest = labeled[0] if labeled else (candidates[0] if candidates else None)
    limited = bool(queue) or bool(boundaries) or bool(truncated_addresses)
    if not seed_txs:
        status = 'not_in_demo' if provider.name == 'fixture' else 'no_activity'
    else:
        status = 'limited' if limited and not labeled else 'completed'
    limitations = [
        'Leads, not proof. Labels and heuristics can be wrong. A human investigator must confirm every step.',
        'Mixers, CoinJoin, cross-chain bridges and swaps are not detected. Funds that enter them cannot be followed.',
        'When one transaction spends several inputs, amounts are blended. Share values are upper bounds.',
        'Change-address detection is a guess. Paths that relied on a guess are marked and lose confidence points.',
    ]
    if provider.name == 'fixture':
        limitations.insert(0, 'Synthetic fixture data. No live blockchain or exchange intelligence was queried.')
    if boundaries:
        limitations.append('Hop limit reached. More labeled endpoints may exist beyond the displayed paths.')
    if queue:
        limitations.append('Exploration budget reached. The result is incomplete.')
    if truncated_addresses:
        limitations.append('Some addresses have more transactions than the fetch limit. Their history was cut off.')
    if unspent_ends:
        limitations.append(f'{len(unspent_ends)} followed output(s) are still unspent. The trail stops there until they move.')
    if not seed_txs:
        limitations.append('No transactions were found for this address in the data source. Nothing can be said about it.')
    names = getattr(provider, 'names', {})
    back = trace_back(seed, history, usable, labels, names, max_hops, max_states)
    if back['boundary']:
        limitations.append('Source tracing stopped at the hop limit. Older funding sources may exist.')
    if back['coinbase_inputs']:
        limitations.append('Some funds trace back to newly mined coins (coinbase).')
    profile = build_profile(seed, seed_txs, labels, names, analysis(seed), seed in truncated_addresses)
    for step in back['steps']:
        discovered.update([step['from'], step['to']])
    all_steps = list(used_steps.values()) + back['steps']
    return {'status': status, 'seed': seed, 'network': 'Bitcoin', 'asset': 'BTC', 'mode': provider.name,
            'max_hops': max_hops, 'transactions': sorted(all_steps, key=lambda s: (s['timestamp'], s['id'])),
            'profile': profile, 'sources': back['sources'],
            'nodes': [{'address': a, 'name': names.get(a, 'Unknown wallet'), 'label': labels.get(a)} for a in sorted(discovered)],
            'candidates': candidates, 'nearest': nearest, 'excluded_time_transfers': sorted(excluded),
            'limitations': limitations}
