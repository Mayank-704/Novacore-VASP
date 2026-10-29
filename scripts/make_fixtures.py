"""Build synthetic Bitcoin fixtures in Esplora format. Every address and txid here is invented."""
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / 'backend' / 'data'
P2WPKH, P2WSH = 'v0_p2wpkh', 'v0_p2wsh'
names, txs = {}, []


def addr(key, label=None):
    a = 'bc1q' + hashlib.sha256(key.encode()).hexdigest()[:38]
    if label:
        names[a] = label
    return a


def tid(key):
    return hashlib.sha256(('tx:' + key).encode()).hexdigest()


def when(minute, hour=10, day=1):
    return int(datetime(2026, 10, day, hour, minute, tzinfo=timezone.utc).timestamp())


def tx(key, ins, outs, t, confirmed=True):
    """ins: (prev_tx_key, vout, addr_key, value[, type]); outs: (addr_key, value[, type])."""
    vin = [{'txid': tid(i[0]), 'vout': i[1], 'prevout': {'scriptpubkey_address': addr(i[2]), 'value': i[3],
            'scriptpubkey_type': i[4] if len(i) > 4 else P2WPKH}} for i in ins]
    vout = [{'scriptpubkey_address': addr(o[0]), 'value': o[1], 'scriptpubkey_type': o[2] if len(o) > 2 else P2WPKH} for o in outs]
    fee = sum(i[3] for i in ins) - sum(o[1] for o in outs)
    assert fee >= 0, key
    status = {'confirmed': True, 'block_height': 900000 + t % 1000, 'block_time': t} if confirmed else {'confirmed': False}
    txs.append({'txid': tid(key), 'vin': vin, 'vout': vout, 'fee': fee, 'status': status})


# Scenario 1: direct deposit into a labeled address (plus an unconfirmed double-spend that must be ignored)
addr('scam1', 'Scenario 1 seed'); addr('victim1', 'Victim 1'); addr('dep1', 'Exchange X deposit')
tx('fund1', [('coin1', 0, 'victim1', 80_100_000)], [('scam1', 80_000_000)], when(0))
tx('direct1', [('fund1', 0, 'scam1', 80_000_000)], [('dep1', 79_990_000)], when(30))
tx('unconf1', [('fund1', 0, 'scam1', 80_000_000)], [('shady1', 79_990_000)], 0, confirmed=False)

# Scenario 2: split with change, a pattern-only deposit, a direct label, and a cluster-only label
addr('scam2', 'Scenario 2 seed'); addr('victim2', 'Victim 2'); addr('mule_a', 'Mule A'); addr('change2', 'Change of seed')
addr('mule_b', 'Mule B'); addr('dep2', 'Unlabeled deposit (cluster)'); addr('dep2_known', 'Exchange Y known deposit')
addr('hot2', 'Exchange Y hot wallet'); addr('pat_dep', 'Unlabeled deposit (pattern)'); addr('hot3', 'Exchange X hot wallet')
tx('fund2', [('coin2', 0, 'victim2', 200_100_000)], [('scam2', 200_000_000)], when(0))
tx('s2a', [('fund2', 0, 'scam2', 200_000_000)], [('mule_a', 100_000_000, P2WSH), ('change2', 99_954_321)], when(10))
tx('s2b', [('s2a', 0, 'mule_a', 100_000_000, P2WSH)], [('mule_b', 99_990_000, P2WSH)], when(20))
tx('s2c', [('s2b', 0, 'mule_b', 99_990_000, P2WSH)], [('dep2', 99_980_000)], when(30))
tx('fund_known', [('coin3', 0, 'someone', 5_100_000)], [('dep2_known', 5_000_000)], when(0, 9))
tx('cons2', [('s2c', 0, 'dep2', 99_980_000), ('fund_known', 0, 'dep2_known', 5_000_000)], [('hot2', 104_900_000)], when(40))
tx('s2d', [('s2a', 1, 'change2', 99_954_321)], [('pat_dep', 99_940_000)], when(15))
ins = []
for k in range(6):
    tx(f'pat_fund{k}', [(f'pcoin{k}', 0, f'user{k}', 3_000_000 + k * 1000)], [('pat_dep', 2_000_000 + k * 777), (f'user{k}', 900_000)], when(k, 9))
    ins.append((f'pat_fund{k}', 0, 'pat_dep', 2_000_000 + k * 777))
tx('sweep3', ins + [('s2d', 0, 'pat_dep', 99_940_000)], [('hot3', 99_900_000 + sum(2_000_000 + k * 777 for k in range(6)) - 60_000)], when(25))

# Scenario 3: trail ends at unlabeled wallets, funds still unspent
addr('scam3', 'Scenario 3 seed'); addr('victim3', 'Victim 3'); addr('u1', 'Unlabeled wallet 1'); addr('u2', 'Unlabeled wallet 2'); addr('u2c', 'Unlabeled change')
tx('fund3', [('coin4', 0, 'victim3', 50_100_000)], [('scam3', 50_000_000)], when(0))
tx('s3a', [('fund3', 0, 'scam3', 50_000_000)], [('u1', 49_990_000)], when(10))
tx('s3b', [('s3a', 0, 'u1', 49_990_000)], [('u2', 20_000_000), ('u2c', 29_976_543)], when(20))

examples = [
    {'name': 'Direct exchange deposit', 'address': addr('scam1'), 'description': 'One transfer reaches a labeled exchange deposit address. An unconfirmed double-spend is ignored.'},
    {'name': 'Split with change and three endpoints', 'address': addr('scam2'), 'description': 'Change is detected and followed. Finds a pattern-only deposit, a direct label and a cluster-only label.'},
    {'name': 'Exchange unknown', 'address': addr('scam3'), 'description': 'The trail ends at unlabeled wallets with unspent funds. No exchange is invented.'},
]
(OUT / 'fixtures').mkdir(exist_ok=True)
(OUT / 'fixtures' / 'bitcoin_demo.json').write_text(json.dumps({'_meta': 'SYNTHETIC. Invented addresses and txids.', 'examples': examples, 'names': names, 'txs': txs}, indent=1))
with open(OUT / 'labels.sample.csv', 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['address', 'entity', 'type', 'source', 'verified'])
    for key, entity, kind in [('dep1', 'Demo Exchange X', 'deposit'), ('dep2_known', 'Demo Exchange Y', 'deposit'), ('hot3', 'Demo Exchange X', 'hot-wallet')]:
        w.writerow([addr(key), entity, kind, 'Synthetic fixture / manually assigned', 'false'])
print(len(txs), 'transactions written')
