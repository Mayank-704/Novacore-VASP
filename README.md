# VASP Desk v0.3: Bitcoin investigation tool

> v0.3 replaced the Ethereum demo with a Bitcoin engine. See STRUCTURE.md for the current layout and status. Sections below that mention Ethereum, ETH or engine.py describe v0.2 and are out of date.


An editable local learning project for the user-provided SIH 2026 PS 26182.
React + TypeScript frontend, Python FastAPI backend, SQLite case history.
This version uses synthetic transactions and manually assigned demo labels.

## Quick start

Start with **START_HERE.txt**. The compiled React frontend is included.
Windows: Python 3.11+ installed, then run `start-demo.cmd`. The launcher tries `py -3` and `python`.
macOS/Linux: Python 3.11+ with venv support, then run `sh start-demo.sh`.
First setup downloads Python dependencies. Afterwards the demo requires no external API.
Open `http://127.0.0.1:8000` after the server starts. Keep the terminal open.
The app binds to your local computer. It has no authentication and is not ready for public hosting.


## Website features

- Overview with actual saved-case counts, recent investigations, and activity.
- Investigation forms with hop limits and optional UTC dates; interactive graph,
  address inspection, path highlighting, transaction search, and label sources.
- Persistent case references, investigator notes, and Open / Reviewed / Archived status.
- Searchable case workspace and service directory; browser-local hop preferences.
- Markdown, JSON, CSV, printable reports, and editable sample request drafts.
- English interface, responsive layout, and clear offline data coverage notices.

## Upgrade safely

Stop your previous server first. Extract this release into a separate folder.
To retain history, back up and copy the old `backend/cases.sqlite3` into the new
`backend` folder before startup. Existing case records are preserved while the
new notes, review status, and activity schema is added automatically.
Do not copy the previous `.venv` or compiled frontend over this release.

## Demo expectations

| Example | Expected result |
|---|---|
| Direct deposit | Demo Exchange X, one hop |
| Multiple wallets | Demo Exchange Y at two hops, X at three hops |
| Multiple wallets, hop limit 1 | Limited result, no labeled endpoint yet |
| Unknown exchange | One observed transfer, no service label |
| Address outside sample dataset | Not in demo, no claim about live activity |

The multi-wallet fixture includes a transfer before the incoming transfer and a failed transaction.
Both are excluded. Service endpoints stop a branch. Case runs save to `backend/cases.sqlite3`.
The Cases and Reports pages load the latest 200 runs. Overview totals cover all saved runs.
Reports export Markdown, JSON, and transaction CSV. The printable report supports the
browser Print / Save as PDF dialog. These are prototype reports, not certified legal evidence.

## VS Code development

Open the project root folder in VS Code.
Install Node.js 22.12+ (or a newer supported LTS) for frontend development.

Terminal 1, project root:

```sh
py -3 -m venv .venv  # Windows; use python3 on macOS/Linux
```

Windows:

```powershell
.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

macOS/Linux:

```sh
.venv/bin/python -m pip install -r backend/requirements-dev.txt
.venv/bin/python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Terminal 2:

```sh
cd frontend
npm ci
npm run dev
```

Open the URL Vite prints (normally `http://127.0.0.1:5173`).
Vite proxies `/api` to the Python server. No CORS configuration or API key is needed.
Run `npm run build` after UI edits, then restart Python to use the compiled UI on port 8000.

## Tests

From project root, with dev requirements installed:

```powershell
.venv\Scripts\python.exe -m pytest backend/tests -q
```

Or `.venv/bin/python -m pytest backend/tests -q` on macOS/Linux.
Tests cover chronological paths, branch ranking, hop truncation, unknown labels,
date filters, invalid requests, persistence and report retrieval.

## Architecture

- `frontend/src/main.tsx`: overview, investigation graph, cases, reports, directory, settings, and guide.
- `backend/exports.py`: evidence exports and escaped printable reports.
- `backend/main.py`: HTTP API, input validation, SQLite storage and report endpoint.
- `backend/engine.py`: bounded traversal with per-path timestamps and cycle avoidance.
- `backend/data/demo.json`: explicit synthetic records and label provenance.
- `frontend/dist`: compiled frontend for Python-only startup.

Tracing uses a small purpose-built queue for this fixture. NetworkX can be added
when broader graph analysis is required. SQLite and built-in Python types keep setup small.
Amounts are strings so display does not introduce binary floating-point rounding.

## Actual scope and limits

The graph proves connectivity only within this synthetic fixture. It does not establish
exact provenance of blended balances. Equal-time transfers are excluded conservatively
because fixture records have no intra-block execution ordering. Paths are bounded by
hops and 250 explored states. No token events, internal transfers, bridges, mixers,
Bitcoin UTXO logic, verified exchange clusters or risk classification are implemented.
Every label is unvalidated. There is no live data provider, login, AI inference,
SAHYOG connector, KYC access or freezing capability in this version.

The next implementation step is an address-history data adapter for one selected chain,
with pagination, timestamps, transaction ordering, failures, provenance and coverage limits.
Only after that should verified label data be integrated and attribution measured on
independent cases. Existing demo labels must never be reused as real exchange evidence.

## Troubleshooting

- Python not found: reinstall with PATH enabled, restart the terminal.
- Port 8000 busy: close an older server or use `--port 8001` and open that URL.
  For Vite development, update the proxy if changing the backend port.
- UI edits not visible: use the Vite development URL or rebuild frontend and refresh.
- Blank compiled UI: ensure `frontend/dist` exists and restart Python after building.
- Internet installation error: check connectivity; setup does not need paid API access.

## Primary documentation

- FastAPI testing: https://fastapi.tiangolo.com/tutorial/testing/
- Vite setup: https://vite.dev/guide/
- React Flow: https://reactflow.dev/

Dependency versions used during validation are recorded in backend/requirements-lock.txt
and frontend/package-lock.json. No real case data or secrets ship in this archive.
