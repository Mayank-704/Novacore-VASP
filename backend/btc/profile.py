"""Everything an investigator wants to know about one address: totals, balance, counterparties, and where money came from."""
from collections import defaultdict, deque

from .models import btc


def _aggregate(table, labels, names, limit):
    rows = []
    for address, info in table.items():
        rows.append({'address': address, 'name': names.get(address, 'Unknown wallet'), 'label': labels.get(address),
                     'total': btc(info['sats']), 'sats': info['sats'], 'tx_count': len(info['txids']),
                     'first_seen': min(info['times']).isoformat(), 'last_seen': max(info['times']).isoformat()})
    rows.sort(key=lambda r: -r['sats'])
    for row in rows:
        del row['sats']
    return rows[:limit]


def build_profile(address, txs, labels, names, analysis, truncated, limit=10):
    received = sent = 0
    times, pending = [], 0
    incoming = defaultdict(lambda: {'sats': 0, 'txids': set(), 'times': []})
    outgoing = defaultdict(lambda: {'sats': 0, 'txids': set(), 'times': []})
    confirmed_count = 0
    for tx in txs:
        if not tx['confirmed']:
            pending += 1
            continue
        confirmed_count += 1
        times.append(tx['time'])
        in_addrs = {i['address'] for i in tx['inputs'] if i['address']}
        received += sum(o['value'] for o in tx['outputs'] if o['address'] == address)
        mine = sum(i['value'] or 0 for i in tx['inputs'] if i['address'] == address)
        sent += mine
        if address not in in_addrs:
            for i in tx['inputs']:
                if i['address']:
                    row = incoming[i['address']]
                    row['sats'] += i['value'] or 0
                    row['txids'].add(tx['txid'])
                    row['times'].append(tx['time'])
        else:
            for o in tx['outputs']:
                if o['address'] and o['address'] not in in_addrs:
                    row = outgoing[o['address']]
                    row['sats'] += o['value']
                    row['txids'].add(tx['txid'])
                    row['times'].append(tx['time'])
    return {'address': address, 'name': names.get(address, 'Unknown wallet'), 'label': labels.get(address),
            'tx_count': confirmed_count, 'pending_count': pending,
            'first_seen': min(times).isoformat() if times else None, 'last_seen': max(times).isoformat() if times else None,
            'total_received': btc(received), 'total_sent': btc(sent), 'balance': btc(received - sent),
            'incoming_counterparties': _aggregate(incoming, labels, names, limit),
            'outgoing_counterparties': _aggregate(outgoing, labels, names, limit),
            'deposit_like': analysis['deposit_like'], 'related_addresses': analysis['mates'],
            'history_complete': not truncated}


def trace_back(seed, history, usable, labels, names, max_hops, max_states=300):
    """Walk backwards: who paid this address, who paid them, and so on. Stops at labeled addresses."""
    queue, seen, expansions = deque([(seed, 0)]), {seed}, 0
    steps, table, boundaries, coinbase = {}, defaultdict(lambda: {'sats': 0, 'txids': set(), 'times': [], 'hops': 99}), set(), 0
    while queue and expansions < max_states:
        address, depth = queue.popleft()
        expansions += 1
        for tx in history(address):
            in_addrs = {i['address'] for i in tx['inputs'] if i['address']}
            if address in in_addrs or not any(o['address'] == address for o in tx['outputs']) or not usable(tx):
                continue
            funders = defaultdict(int)
            for i in tx['inputs']:
                if i['address']:
                    funders[i['address']] += i['value'] or 0
                else:
                    coinbase += 1
            for funder, sats in funders.items():
                step = {'id': f"{tx['txid']}:{funder[:12]}>{address[:12]}", 'txid': tx['txid'], 'from': funder, 'to': address,
                        'amount': btc(sats), 'asset': 'BTC', 'timestamp': tx['time'].isoformat(), 'kind': 'source',
                        'direction': 'in'}
                steps[step['id']] = step
                row = table[funder]
                row['sats'] += sats
                row['txids'].add(tx['txid'])
                row['times'].append(tx['time'])
                row['hops'] = min(row['hops'], depth + 1)
                if funder in seen or funder in labels:
                    continue
                if depth + 1 >= max_hops:
                    boundaries.add(funder)
                    continue
                seen.add(funder)
                queue.append((funder, depth + 1))
    rows = []
    for address, info in table.items():
        rows.append({'address': address, 'name': names.get(address, 'Unknown wallet'), 'label': labels.get(address),
                     'hops': info['hops'], 'total': btc(info['sats']), 'sats': info['sats'], 'tx_count': len(info['txids']),
                     'first_seen': min(info['times']).isoformat(), 'last_seen': max(info['times']).isoformat()})
    rows.sort(key=lambda r: (r['hops'], -r['sats']))
    for row in rows:
        del row['sats']
    return {'sources': rows[:60], 'steps': list(steps.values()), 'boundary': bool(boundaries) or bool(queue),
            'coinbase_inputs': coinbase}
