import csv
import io
from html import escape


def markdown_report(r):
    lines = [
        "# VASP Desk Investigation"
        + (" (SYNTHETIC DEMO DATA)" if r.get("mode") == "fixture" else ""),
        "",
        f"Case: {r['case_ref']}",
        f"Investigation ID: {r['id']}",
        f"Created (UTC): {r['created']}",
        f"Seed: {r['seed']}",
        f"Network: {r['network']}",
        f"Trace status: {r['status']}",
        f"Review status: {r['review_status']}",
        f"Hop limit: {r['max_hops']}",
        f"Date filters: {r['filters']}",
        "",
        "## Candidate findings",
    ]

    if not r["candidates"]:
        lines.append(
            "No exchange endpoint was found in the explored data. "
            "This does not prove absence of an exchange."
        )

    for c in r["candidates"]:
        label = c.get("label") or {}
        verified = label.get("verified") is True

        attribution_status = c.get("attribution_status")
        if not attribution_status:
            attribution_status = (
                "verified_label"
                if verified
                else "unverified_candidate"
            )

        if attribution_status == "verified_label":
            status_text = "Label marked verified"
        else:
            status_text = "UNVERIFIED CANDIDATE — requires independent confirmation"

        lines.extend([
            f"- {c.get('vasp', 'Unknown entity')}: "
            f"{c.get('hops', 'unknown')} hops, address {c.get('address', 'unknown')}",
            f"  Attribution status: {status_text}",
            f"  Source: {label.get('source', 'Unknown')}",
            f"  Match type: {c.get('match', 'unknown')}",
            f"  Confidence: {c.get('confidence', 'Unknown')} "
            f"(score {c.get('confidence_score', 'unknown')})",
        ])

        amount = c.get("amount")
        if amount is None:
            lines.append("  Transaction output value: unavailable")
        else:
            amount_line = f"  Transaction output value: {amount} BTC"
            share = c.get("share_upper_bound")

            if isinstance(share, (int, float)) and not isinstance(share, bool):
                amount_line += (
                    f" (estimated upper bound: {share * 100:.1f}% "
                    "of funds received by the seed)"
                )
            else:
                amount_line += (
                    " (seed-origin share unknown; transaction inputs may "
                    "combine funds from multiple sources)"
                )

            lines.append(amount_line)

        if c.get("amount_note"):
            lines.append(f"  Amount note: {c['amount_note']}")

        for reason in c.get("reasons", []):
            lines.append(f"  Why: {reason}")

        transactions = c.get("transactions") or []
        path = ", ".join(
            t.get("id", "unknown transaction") for t in transactions
        ) or "Labeled seed"

        lines.append(f"  Path: {path}")

    p = r.get("profile")
    if p:
        lines.extend([
            "",
            "## Address profile",
            f"Address: {p.get('address', 'unknown')}",
            f"Transactions: {p.get('tx_count', 'unknown')} confirmed, "
            f"{p.get('pending_count', 'unknown')} pending",
            f"First / last activity: {p.get('first_seen')} / {p.get('last_seen')}",
            f"Received: {p.get('total_received')} BTC | "
            f"Sent: {p.get('total_sent')} BTC | "
            f"Balance: {p.get('balance')} BTC",
            "History complete: "
            + (
                "yes"
                if p.get("history_complete")
                else "NO, cut off by the fetch limit"
            ),
        ])

    lines.extend(["", "## Where the money came from (sources)"])

    for source in r.get("sources", []):
        label = source.get("label")
        tag = label.get("entity", "unlabeled") if label else "unlabeled"

        lines.append(
            f"- {source.get('address', 'unknown')} ({tag}): "
            f"{source.get('total', 'unknown')} BTC in "
            f"{source.get('tx_count', 'unknown')} tx, "
            f"{source.get('hops', 'unknown')} hop(s) back"
        )

    if not r.get("sources"):
        lines.append("No sources found in the explored data.")

    lines.extend(["", "## Transactions"])

    for tx in r.get("transactions", []):
        lines.append(
            f"- {tx.get('id', 'unknown')}: "
            f"{tx.get('from', 'unknown')} to {tx.get('to', 'unknown')}, "
            f"{tx.get('amount', 'unknown')} {tx.get('asset', 'unknown')}, "
            f"{tx.get('timestamp', 'unknown')}"
        )

    lines.extend(["", "## Investigator notes"])

    notes = r.get("notes") or []
    if isinstance(notes, str):
        notes = [notes]

    lines.extend(notes or ["No notes recorded."])

    lines.extend(["", "## Limitations"])
    lines.extend(
        "- " + str(limitation)
        for limitation in r.get("limitations", [])
    )

    lines.extend([
        "",
        "Attribution findings are investigative leads, not proof of ownership.",
        "A label marked verified indicates the label's recorded verification "
        "status; it does not independently prove control of the address.",
        "No real disclosure or freezing request was sent. SAHYOG is not connected.",
    ])

    return "\n".join(lines)


def csv_report(r):
    output = io.StringIO(newline="")
    writer = csv.writer(output)

    writer.writerow([
        "case_ref",
        "mode",
        "reference",
        "from",
        "to",
        "amount",
        "asset",
        "timestamp_utc",
    ])

    for tx in r.get("transactions", []):
        writer.writerow([
            r.get("case_ref", ""),
            r.get("mode", "live"),
            tx.get("id", ""),
            tx.get("from", ""),
            tx.get("to", ""),
            tx.get("amount", ""),
            tx.get("asset", ""),
            tx.get("timestamp", ""),
        ])

    return output.getvalue()


def printable_report(r):
    text = escape(markdown_report(r))

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>VASP Desk Report</title>
<style>
body {{
    font-family: Arial, sans-serif;
    color: #172d43;
    max-width: 1000px;
    margin: 40px auto;
    padding: 0 24px;
}}
button {{
    padding: 12px 20px;
    background: #087f8c;
    color: white;
    border: 0;
    border-radius: 7px;
}}
pre {{
    white-space: pre-wrap;
    overflow-wrap: anywhere;
    line-height: 1.7;
    font-family: Arial, sans-serif;
    font-size: 14px;
}}
@media print {{
    button {{
        display: none;
    }}
    body {{
        margin: 0;
        max-width: none;
    }}
}}
</style>
</head>
<body>
<button onclick="window.print()">Print / Save as PDF</button>
<pre>{text}</pre>
</body>
</html>"""
