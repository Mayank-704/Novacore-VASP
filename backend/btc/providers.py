"""Where transactions come from. Both providers return the same normalized shape.

FixtureProvider reads a local JSON file (offline demo, tests).
EsploraProvider reads a public Esplora-style API (for example Blockstream or mempool.space).
"""
import json
import time
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path

from .models import normalize_tx


class ProviderError(Exception):
    pass


class FixtureProvider:
    name = 'fixture'

    def __init__(self, path):
        data = json.loads(Path(path).read_text(encoding='utf-8'))
        self.examples = data.get('examples', [])
        self.names = data.get('names', {})
        self._index = defaultdict(dict)
        for raw in data['txs']:
            tx = normalize_tx(raw)
            for item in tx['inputs'] + tx['outputs']:
                if item['address']:
                    self._index[item['address']][tx['txid']] = tx

    def knows(self, address):
        return address in self._index

    def address_txs(self, address, limit):
        txs = sorted(self._index.get(address, {}).values(),
                     key=lambda t: (t['time'].timestamp() if t['time'] else 1e18, t['txid']))
        return txs[:limit], len(txs) > limit


class EsploraProvider:
    name = 'esplora'
    PAGE = 25  # Esplora returns 25 confirmed transactions per page

    def __init__(self, base_url='https://blockstream.info/api', fetch=None, pause=0.2):
        self.base_url = base_url.rstrip('/')
        self.names = {}
        self.examples = []
        self._fetch = fetch or self._http_get
        self._pause = pause

    def knows(self, address):
        return True

    def _http_get(self, url):
        last = None
        for attempt in range(4):
            try:
                request = urllib.request.Request(url, headers={'User-Agent': 'vasp-desk/0.3'})
                with urllib.request.urlopen(request, timeout=20) as response:
                    return json.loads(response.read().decode('utf-8'))
            except urllib.error.HTTPError as error:
                last = error
                if error.code not in (429, 500, 502, 503, 504):
                    break
            except (urllib.error.URLError, TimeoutError) as error:
                last = error
            time.sleep(1.5 * (attempt + 1))
        raise ProviderError(f'Data provider request failed: {last}')

    def address_txs(self, address, limit):
        raw, seen = [], set()
        url = f'{self.base_url}/address/{address}/txs'
        while True:
            page = self._fetch(url)
            fresh = [t for t in page if t['txid'] not in seen]
            for t in fresh:
                seen.add(t['txid'])
            raw.extend(fresh)
            confirmed = [t for t in page if (t.get('status') or {}).get('confirmed')]
            if len(raw) >= limit or len(confirmed) < self.PAGE or not fresh:
                break
            url = f'{self.base_url}/address/{address}/txs/chain/{confirmed[-1]["txid"]}'
            time.sleep(self._pause)
        truncated = len(raw) > limit or (len(raw) >= limit and len(confirmed) >= self.PAGE)
        txs = [normalize_tx(t) for t in raw[:limit]]
        return txs, truncated
