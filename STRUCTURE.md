# VASP Desk v0.3: Project structure (Bitcoin)

```
vasp-attribution/
  backend/
    main.py                API, validation, SQLite cases, mode switch (fixture / live)
    exports.py             Markdown, CSV, JSON, printable reports (include match type, score, reasons)
    btc/
      validate.py          Real address checksums (Base58Check, Bech32, Bech32m)
      models.py            Raw Esplora transaction -> one small normalized shape
      providers.py         FixtureProvider (offline) and EsploraProvider (live, paginated, retries)
      labels.py            Loads label CSV files
      heuristics.py        Change-address guess, same-owner clustering, deposit-address pattern
      scoring.py           Points -> High / Medium / Low, with written reasons
      tracer.py            Follows exact outputs (txid:vout) forward up to N hops
      profile.py           Address profile (totals, balance, counterparties) and backward source tracing
    data/
      fixtures/bitcoin_demo.json   Synthetic transactions (invented addresses)
      labels.sample.csv            Synthetic labels, used in fixture mode
      labels.csv                   YOUR real labels go here (live mode)
    tests/                 test_btc.py (engine, rules, provider), test_api.py (endpoints)
  scripts/make_fixtures.py Regenerates the synthetic fixtures
  frontend/                React + TypeScript UI (rebuilt, now says Bitcoin / BTC)
```

## What an investigator gets for one address
1. Address profile: balance, total received and sent, transaction count, first and last activity.
2. Sources: who funded the address, and who funded them, up to the hop limit. Stops at labeled addresses.
3. Destinations: direct recipients, then onward tracing up to the hop limit.
4. Graph with both directions, plus exchange leads with High / Medium / Low confidence and reasons.
5. Report export (Markdown, JSON, CSV, print/PDF) with all of the above.
Limit: an address is not a person. Naming the owner needs the exchange's own records through legal process.

## Modes
- Default: `VASP_MODE=fixture`. Offline, synthetic data.
- Live: `VASP_MODE=live` (optional `VASP_ESPLORA_URL`, `VASP_LABELS`). Queries public Bitcoin mainnet
  transaction history through Blockstream Esplora by default. Windows users can run `start-live.cmd`.
  Live mode is read-only; it does not broadcast transactions. The empty-by-default `labels.csv`
  must be populated only with independently verified, appropriately licensed labels.

## Status against the pitch deck
| Pitch promise | Status |
|---|---|
| Enter a Bitcoin wallet | Done (checksum validated) |
| Show where the money came from and where it went, with a graph | Done: profile tab, sources table, destinations table, graph (amber = in, blue = out) |
| Trace up to 3 steps | Done. Exact-output tracing; change is followed without adding a hop |
| Match public exchange labels | Code done. Real labels file is EMPTY: the team must collect them |
| High / Medium / Low with reasons | Done, rule based |
| Report with path, source, confidence, limits | Done |
| Free public blockchain API | Blockstream Esplora adapter is available in live mode; independent accuracy validation remains |
| Accuracy and speed validation | NOT done |
| NetworkX | Not used. Remove from the slide or add later |
| PostgreSQL | Not used (SQLite). Change slide to "SQLite now, PostgreSQL later" |

## Next phases
1. Validate live mode and rate/coverage behavior on public addresses.
2. Collect real labels (check each licence) into labels.csv.
3. Build the validation set: 5-10 public cases; record right / wrong / time.
4. Fix the slides to match what is built.
