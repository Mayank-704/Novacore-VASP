"""Turn raw Esplora-format transactions into one small, predictable shape."""
from datetime import datetime, timezone
from decimal import Decimal


def btc(sats):
    return f"{Decimal(sats) / Decimal(10 ** 8):.8f}"


def normalize_tx(raw):
    status = raw.get('status') or {}
    confirmed = bool(status.get('confirmed'))
    block_time = status.get('block_time')
    when = datetime.fromtimestamp(block_time, tz=timezone.utc) if confirmed and block_time else None
    inputs = []
    for vin in raw.get('vin', []):
        prev = vin.get('prevout') or {}
        inputs.append({'address': prev.get('scriptpubkey_address'), 'value': prev.get('value'),
                       'type': prev.get('scriptpubkey_type'), 'txid': vin.get('txid'), 'vout': vin.get('vout')})
    outputs = []
    for n, vout in enumerate(raw.get('vout', [])):
        outputs.append({'n': n, 'address': vout.get('scriptpubkey_address'),
                        'value': vout.get('value', 0), 'type': vout.get('scriptpubkey_type')})
    return {'txid': raw['txid'], 'time': when, 'confirmed': confirmed and when is not None,
            'inputs': inputs, 'outputs': outputs, 'fee': raw.get('fee')}
