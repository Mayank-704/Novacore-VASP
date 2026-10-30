"""Address profiles and bounded backward Bitcoin source tracing."""

from collections import defaultdict, deque

from .models import btc


def _aggregate(table, labels, names, limit):
    """Convert counterparty statistics into frontend-friendly rows."""
    rows = []

    for address, info in table.items():
        times = info["times"]

        rows.append(
            {
                "address": address,
                "name": names.get(address, "Unknown wallet"),
                "label": labels.get(address),
                "total": btc(info["sats"]),
                "sats": info["sats"],
                "tx_count": len(info["txids"]),
                "first_seen": min(times).isoformat() if times else None,
                "last_seen": max(times).isoformat() if times else None,
            }
        )

    rows.sort(key=lambda row: -row["sats"])

    for row in rows:
        row.pop("sats", None)

    return rows[:limit]


def build_profile(
    address,
    txs,
    labels,
    names,
    analysis,
    truncated,
    limit=10,
):
    """Build totals, balance, counterparties, and address-history metadata."""
    received = 0
    sent = 0
    times = []
    pending = 0

    incoming = defaultdict(
        lambda: {"sats": 0, "txids": set(), "times": []}
    )
    outgoing = defaultdict(
        lambda: {"sats": 0, "txids": set(), "times": []}
    )

    confirmed_count = 0

    for tx in txs:
        if not tx.get("confirmed", False):
            pending += 1
            continue

        confirmed_count += 1

        tx_time = tx.get("time")
        if tx_time is not None:
            times.append(tx_time)

        inputs = tx.get("inputs", [])
        outputs = tx.get("outputs", [])

        input_addresses = {
            item["address"]
            for item in inputs
            if item.get("address")
        }

        received += sum(
            output["value"]
            for output in outputs
            if output.get("address") == address
        )

        sent += sum(
            item.get("value") or 0
            for item in inputs
            if item.get("address") == address
        )

        if address not in input_addresses:
            for item in inputs:
                counterparty = item.get("address")

                if not counterparty:
                    continue

                row = incoming[counterparty]
                row["sats"] += item.get("value") or 0
                row["txids"].add(tx["txid"])

                if tx_time is not None:
                    row["times"].append(tx_time)

        else:
            for output in outputs:
                counterparty = output.get("address")

                if (
                    not counterparty
                    or counterparty in input_addresses
                ):
                    continue

                row = outgoing[counterparty]
                row["sats"] += output["value"]
                row["txids"].add(tx["txid"])

                if tx_time is not None:
                    row["times"].append(tx_time)

    return {
        "address": address,
        "name": names.get(address, "Unknown wallet"),
        "label": labels.get(address),
        "tx_count": confirmed_count,
        "pending_count": pending,
        "first_seen": min(times).isoformat() if times else None,
        "last_seen": max(times).isoformat() if times else None,
        "total_received": btc(received),
        "total_sent": btc(sent),
        "balance": btc(received - sent),
        "incoming_counterparties": _aggregate(
            incoming, labels, names, limit
        ),
        "outgoing_counterparties": _aggregate(
            outgoing, labels, names, limit
        ),
        "deposit_like": analysis.get("deposit_like", False),
        "related_addresses": analysis.get("mates", []),
        "history_complete": not truncated,
    }


def trace_back(
    seed,
    history,
    usable,
    labels,
    names,
    max_hops,
    max_states=300,
    max_steps=500,
):
    """Trace funding sources with bounded address and evidence exploration.

    The returned boundary flag indicates that tracing stopped at a hop
    boundary or because the exploration budget was exhausted.
    """
    max_states = max(1, min(int(max_states), 40))
    max_steps = max(1, min(int(max_steps), 500))

    queue = deque([(seed, 0)])
    seen_addresses = {seed}

    # Prevent repeating the same transaction/address examination.
    examined_pairs = set()

    steps = {}
    table = defaultdict(
        lambda: {
            "sats": 0,
            "txids": set(),
            "times": [],
            "hops": 99,
        }
    )

    boundaries = set()
    coinbase_inputs = 0
    expansions = 0
    budget_exhausted = False

    while queue:
        if expansions >= max_states:
            budget_exhausted = True
            break

        address, depth = queue.popleft()
        expansions += 1

        address_history = history(address)

        for tx in address_history:
            pair = (address, tx["txid"])

            if pair in examined_pairs:
                continue

            examined_pairs.add(pair)

            inputs = tx.get("inputs", [])
            outputs = tx.get("outputs", [])

            input_addresses = {
                item["address"]
                for item in inputs
                if item.get("address")
            }

            # We want transactions that paid this address, not transactions
            # in which the address was itself a sender.
            if address in input_addresses:
                continue

            if not any(
                output.get("address") == address
                for output in outputs
            ):
                continue

            if not usable(tx):
                continue

            tx_time = tx.get("time")

            funders = defaultdict(int)

            for item in inputs:
                funder = item.get("address")

                if funder:
                    funders[funder] += item.get("value") or 0
                else:
                    coinbase_inputs += 1

            for funder, sats in funders.items():
                step_id = (
                    f"{tx['txid']}:{funder[:12]}>{address[:12]}"
                )

                if step_id not in steps and len(steps) >= max_steps:
                    budget_exhausted = True
                    break

                if step_id not in steps:
                    steps[step_id] = {
                        "id": step_id,
                        "txid": tx["txid"],
                        "from": funder,
                        "to": address,
                        "amount": btc(sats),
                        "asset": "BTC",
                        "timestamp": (
                            tx_time.isoformat()
                            if tx_time is not None
                            else None
                        ),
                        "kind": "source",
                        "direction": "in",
                    }

                row = table[funder]
                row["sats"] += sats
                row["txids"].add(tx["txid"])

                if tx_time is not None:
                    row["times"].append(tx_time)

                row["hops"] = min(row["hops"], depth + 1)

                # A known label is an endpoint; don't continue past it.
                if funder in seen_addresses or funder in labels:
                    continue

                if depth + 1 >= max_hops:
                    boundaries.add(funder)
                    continue

                if expansions + len(queue) >= max_states:
                    budget_exhausted = True
                    continue

                seen_addresses.add(funder)
                queue.append((funder, depth + 1))

            if budget_exhausted:
                break

        if budget_exhausted:
            break

    rows = []

    for address, info in table.items():
        times = info["times"]

        rows.append(
            {
                "address": address,
                "name": names.get(address, "Unknown wallet"),
                "label": labels.get(address),
                "hops": info["hops"],
                "total": btc(info["sats"]),
                "sats": info["sats"],
                "tx_count": len(info["txids"]),
                "first_seen": min(times).isoformat() if times else None,
                "last_seen": max(times).isoformat() if times else None,
            }
        )

    rows.sort(
        key=lambda row: (
            row["hops"],
            -row["sats"],
        )
    )

    for row in rows:
        row.pop("sats", None)

    return {
        "sources": rows[:60],
        "steps": list(steps.values()),
        "boundary": bool(boundaries) or bool(queue) or budget_exhausted,
        "coinbase_inputs": coinbase_inputs,
        "budget_exhausted": budget_exhausted,
        "states_examined": expansions,
        "steps_recorded": len(steps),
    }