"""Simple, explainable Bitcoin heuristics. Every one of them can be wrong; the tracer records when it relied on one."""

ROUND_SATS = 10_000  # 0.0001 BTC


def detect_change(tx, input_addresses):
    """Guess which output is change. Returns (output_index or None, 'strong' | 'weak' | None).

    Rule 1: only one output has the same script type as the inputs.
    Rule 2: only one output is a non-round amount while the others are round.
    Both rules agreeing is 'strong'. One rule alone is 'weak'. Address reuse is handled by the tracer.
    """
    outs = [o for o in tx['outputs'] if o['address'] and o['address'] not in input_addresses]
    if len(outs) < 2:
        return None, None
    input_types = {i['type'] for i in tx['inputs'] if i['type']}
    by_type = None
    if len(input_types) == 1:
        same = [o for o in outs if o['type'] in input_types]
        if len(same) == 1:
            by_type = same[0]['n']
    non_round = [o for o in outs if o['value'] % ROUND_SATS != 0]
    by_amount = non_round[0]['n'] if len(non_round) == 1 else None
    if by_type is not None and by_type == by_amount:
        return by_type, 'strong'
    if by_type is not None and by_amount is None:
        return by_type, 'weak'
    if by_amount is not None and by_type is None:
        return by_amount, 'weak'
    return None, None


def analyze_address(address, txs, labels, min_senders=5):
    """Look at one address's history for exchange evidence.

    cluster: another address spent together with it (same owner, common-input rule) has a label.
    deposit_like: many different senders paid it, and every time it spends it sweeps to a single output.
    """
    mates, funders, funding_txs, spends = set(), set(), 0, []
    for tx in txs:
        if not tx['confirmed']:
            continue
        in_addrs = {i['address'] for i in tx['inputs'] if i['address']}
        if address in in_addrs:
            mates |= in_addrs - {address}
            spends.append(tx)
        elif any(o['address'] == address for o in tx['outputs']):
            funding_txs += 1
            funders |= in_addrs
    cluster = next(((labels[m], m) for m in sorted(mates) if m in labels), None)
    deposit_like = (funding_txs >= min_senders and len(funders) >= min_senders and bool(spends)
                    and all(len([o for o in tx['outputs'] if o['address']]) == 1 for tx in spends))
    return {'cluster': cluster, 'deposit_like': deposit_like,
            'funding_txs': funding_txs, 'senders': len(funders), 'mates': len(mates)}
