"""Simple, explainable Bitcoin heuristics.

Every heuristic can be wrong. Results are investigative leads, not proof
of wallet ownership or exchange attribution.
"""

ROUND_SATS = 10_000  # 0.0001 BTC


def detect_change(tx, input_addresses):
    """Guess which output is change. Returns (output_index, strength)."""
    inputs = tx.get("inputs", [])
    outputs = tx.get("outputs", [])
    input_addresses = set(input_addresses or ())

    eligible_outputs = [
        output for output in outputs
        if output.get("address") and output["address"] not in input_addresses
    ]
    if len(eligible_outputs) < 2:
        return None, None

    input_types = {item.get("type") for item in inputs if item.get("type")}
    by_type = None
    if len(input_types) == 1:
        matching = [
            output for output in eligible_outputs
            if output.get("type") in input_types
        ]
        if len(matching) == 1:
            by_type = matching[0].get("n")

    non_round = []
    for output in eligible_outputs:
        value = output.get("value")
        if isinstance(value, int) and not isinstance(value, bool):
            if value % ROUND_SATS != 0:
                non_round.append(output)
    by_amount = non_round[0].get("n") if len(non_round) == 1 else None

    if by_type is not None and by_type == by_amount:
        return by_type, "strong"
    if by_type is not None and by_amount is not None:
        return None, None
    if by_type is not None:
        return by_type, "weak"
    if by_amount is not None:
        return by_amount, "weak"
    return None, None


def analyze_address(address, txs, labels, min_senders=5):
    """Analyze possible exchange-related behavior; never prove ownership."""
    labels = labels or {}
    try:
        min_senders = max(1, int(min_senders))
    except (TypeError, ValueError):
        min_senders = 5

    mates, funders, funding_txs, spends = set(), set(), 0, []

    for tx in txs or []:
        if not tx.get("confirmed", False):
            continue

        inputs = tx.get("inputs", [])
        outputs = tx.get("outputs", [])
        input_addresses = {
            item.get("address") for item in inputs if item.get("address")
        }
        received_here = any(
            output.get("address") == address for output in outputs
        )

        if address in input_addresses:
            # Common-input clustering is uncertain for collaborative transactions.
            mates.update(input_addresses - {address})
            spends.append(tx)
        elif received_here:
            funding_txs += 1
            funders.update(input_addresses)

    cluster = None
    for mate in sorted(mates):
        if mate in labels:
            cluster = (labels[mate], mate)
            break

    deposit_like = (
        funding_txs >= min_senders
        and len(funders) >= min_senders
        and bool(spends)
        and all(
            len([
                output for output in tx.get("outputs", [])
                if output.get("address")
            ]) == 1
            for tx in spends
        )
    )

    return {
        "cluster": cluster,
        "deposit_like": deposit_like,
        "funding_txs": funding_txs,
        "senders": len(funders),
        "mates": len(mates),
    }
