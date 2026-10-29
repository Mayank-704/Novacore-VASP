"""Bitcoin mainnet address validation with real checksums (Base58Check, Bech32, Bech32m)."""
import hashlib

B58 = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
B32 = 'qpzry9x8gf2tvdw0s3jn54khce6mua7l'
GEN = [0x3b6a57b2, 0x26508e6d, 0x1ea119fa, 0x3d4233dd, 0x2a1462b3]


def _base58check(address):
    number = 0
    for char in address:
        index = B58.find(char)
        if index < 0:
            return False
        number = number * 58 + index
    try:
        raw = number.to_bytes(25, 'big')
    except OverflowError:
        return False
    checksum = hashlib.sha256(hashlib.sha256(raw[:-4]).digest()).digest()[:4]
    return raw[0] in (0, 5) and checksum == raw[-4:]


def _polymod(values):
    chk = 1
    for value in values:
        top = chk >> 25
        chk = (chk & 0x1ffffff) << 5 ^ value
        for i in range(5):
            if (top >> i) & 1:
                chk ^= GEN[i]
    return chk


def _bech32(address):
    if address != address.lower() and address != address.upper():
        return False
    address = address.lower()
    pos = address.rfind('1')
    if pos != 2 or address[:2] != 'bc' or len(address) > 90:
        return False
    data = [B32.find(c) for c in address[pos + 1:]]
    if -1 in data or len(data) < 7:
        return False
    check = _polymod([ord(c) >> 5 for c in 'bc'] + [0] + [ord(c) & 31 for c in 'bc'] + data)
    version = data[0]
    if version == 0:
        return check == 1
    return 1 <= version <= 16 and check == 0x2bc830a3


def normalize_address(address):
    address = address.strip()
    return address.lower() if address.lower().startswith('bc1') else address


def is_valid_address(address):
    address = normalize_address(address)
    if address.startswith(('1', '3')):
        return _base58check(address)
    if address.lower().startswith('bc1'):
        return _bech32(address)
    return False
