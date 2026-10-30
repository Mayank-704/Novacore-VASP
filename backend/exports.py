import csv
import io
from html import escape


def markdown_report(r):
    lines = ['# VASP Desk Investigation' + (' (SYNTHETIC DEMO DATA)' if r.get('mode') == 'fixture' else ''), '', f"Case: {r['case_ref']}",
             f"Investigation ID: {r['id']}", f"Created (UTC): {r['created']}",
             f"Seed: {r['seed']}", f"Network: {r['network']}", f"Trace status: {r['status']}",
             f"Review status: {r['review_status']}", f"Hop limit: {r['max_hops']}",
             f"Date filters: {r['filters']}", '', '## Candidate findings']
    if not r['candidates']:
        lines.append('No exchange endpoint was found in the explored data. This does not prove absence of an exchange.')
    for c in r['candidates']:
        share = c.get('share_upper_bound')
        if share is None:
            share_text = 'Attributable share: unknown; no percentage established'
        else:
            share_text = f"At most {share * 100:.1f}% of funds received by the seed"
        amount = c.get('amount')
        if amount is None:
            received = c.get('address_total_received')
            amount_text = ('unknown as attributable; address total received was ' + str(received) + ' BTC'
                           if received is not None else 'unknown as attributable')
        else:
            amount_text = str(amount) + ' BTC'
        lines += [f"- {c['vasp']}: {c['hops']} hops, address {c['address']}",
                  f"  Source: {c['label']['source']}", f"  Match type: {c['match']}",
                  f"  Confidence: {c['confidence']} (score {c['confidence_score']})",
                  f"  Amount reaching it: {amount_text}",
                  f"  Attribution: {share_text}",
                  *['  Why: ' + reason for reason in c['reasons']],
                  '  Path: ' + (', '.join(t['id'] for t in c['transactions']) or 'Labeled seed')]
    p = r.get('profile')
    if p:
        lines[lines.index('## Candidate findings'):lines.index('## Candidate findings')] = [
            '## Address profile', f"Address: {p['address']}", f"Transactions: {p['tx_count']} confirmed, {p['pending_count']} pending",
            f"First / last activity: {p['first_seen']} / {p['last_seen']}",
            f"Received: {p['total_received']} BTC | Sent: {p['total_sent']} BTC | Balance: {p['balance']} BTC",
            'History complete: ' + ('yes' if p['history_complete'] else 'NO, cut off by the fetch limit'), '']
    lines += ['', '## Where the money came from (sources)']
    for s in r.get('sources', []):
        tag = s['label']['entity'] if s['label'] else 'unlabeled'
        lines.append(f"- {s['address']} ({tag}): {s['total']} BTC in {s['tx_count']} tx, {s['hops']} hop(s) back")
    if not r.get('sources'):
        lines.append('No sources found in the explored data.')
    lines += ['', '## Transactions']
    for tx in r['transactions']:
        lines.append(f"- {tx['id']}: {tx['from']} to {tx['to']}, {tx['amount']} {tx['asset']}, {tx['timestamp']}")
    lines += ['', '## Investigator notes', r['notes'] or 'No notes recorded.', '', '## Limitations']
    lines += ['- ' + text for text in r['limitations']]
    lines += ['', 'No real disclosure or freezing request was sent. SAHYOG is not connected.']
    return '\n'.join(lines)


def csv_report(r):
    output = io.StringIO(newline='')
    writer = csv.writer(output)
    writer.writerow(['case_ref', 'mode', 'reference', 'from', 'to', 'amount', 'asset', 'timestamp_utc'])
    for tx in r['transactions']:
        writer.writerow([r['case_ref'], r.get('mode', 'live'), tx['id'], tx['from'], tx['to'], tx['amount'], tx['asset'], tx['timestamp']])
    return output.getvalue()


def printable_report(r):
    text = escape(markdown_report(r))
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>VASP Desk Report</title>
    <style>body{{font-family:Arial,sans-serif;color:#172d43;max-width:1000px;margin:40px auto;padding:0 24px}}button{{padding:12px 20px;background:#087f8c;color:white;border:0;border-radius:7px}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.7;font-family:Arial,sans-serif;font-size:14px}}@media print{{button{{display:none}}body{{margin:0;max-width:none}}}}</style></head><body><button onclick="window.print()">Print / Save as PDF</button><pre>{text}</pre></body></html>'''
