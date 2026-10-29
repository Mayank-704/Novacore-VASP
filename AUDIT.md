# NOVACORE / VASP Attribution — Baseline Audit

**Audited release:** `vasp-attribution-v0.3 updated.zip`  
**Audit date:** 2026-10-28  
**Purpose:** establish a factual baseline before implementation changes.

## 1. Current implementation

- Frontend: React, TypeScript, Vite, React Flow.
- Backend: FastAPI and Pydantic.
- Persistence: SQLite (`backend/cases.sqlite3` at runtime).
- Blockchain scope: Bitcoin only.
- Data providers: local synthetic fixture provider and an Esplora-compatible live provider.
- Tracing: transaction-output-oriented forward tracing plus address profile/backward-source analysis.
- Attribution: CSV labels, heuristics, rule-based High/Medium/Low scoring.
- Outputs: case history, Markdown/JSON/CSV exports, printable report, sample request draft.
- Tests: `backend/tests/test_btc.py` and `backend/tests/test_api.py`.

## 2. Baseline verification

Command executed from the project root:

```bash
python -m pytest -q
```

Result: **20 passed**.

Coverage includes address checksum validation, fixture tracing, hop limits, unknown labels, date filtering, state-budget limitations, provider pagination/parsing with test data, profile summaries, API validation, case persistence, and report/export endpoints.

This result verifies the current automated tests only. It does not prove real-world attribution accuracy, production security, or live-provider reliability.

## 3. Findings and risks

### P0 — Establish data truth before claiming attribution

- `backend/data/labels.csv` contains headers/instructions but no real VASP labels.
- `backend/data/labels.sample.csv` and fixture-mode entities are synthetic and must never be presented as real entities.
- Add labels only with source provenance, licensing review, collection date, verification status, and review history.

### P0 — Validate live provider behavior

- `EsploraProvider` has pagination and retry logic, but the existing test suite validates it using controlled test data.
- Live behavior has not been verified as part of this audit.
- Test real API responses, confirmed/unconfirmed transactions, pagination boundaries, rate limits, timeouts, malformed responses, and large address histories before relying on live results.

### P1 — Fix reproducible frontend installation/build

- `npm ci` was attempted from the frontend directory but did not complete within the available execution window.
- The frontend production build therefore remains **unverified**. Retry in a normal development environment with network access, then run `npm ci` and `npm run build` from `frontend/`.
- Do not replace the lockfile blindly; first reproduce the installation problem and preserve dependency reproducibility.

### P1 — Correct architecture documentation

- Ensure README and structure documents describe the current `backend/btc/` modules, SQLite persistence, fixture/live modes, and actual feature limitations.
- Do not claim NetworkX, PostgreSQL, multi-chain support, verified exchange clusters, SAHYOG integration, or beneficial-owner identification unless implemented and validated.

### P1 — Improve evidence and confidence semantics

- Separate observed transaction facts, public labels, heuristic clustering, and behavioral patterns.
- Every label and attribution should preserve source, timestamp, verification state, supporting transaction IDs, limitations, and contradictions.
- A heuristic association must not be displayed as confirmed ownership.

### P2 — Security and deployment

- Current README says the app has no authentication and is not ready for public hosting.
- Before shared/production deployment, implement and test authentication, authorization, case isolation, secret management, audit logging, secure report access, and operational monitoring.

## 4. Implementation order

1. Baseline audit (this document).
2. Architecture and API/data contracts.
3. Bitcoin transaction normalization and live-provider validation.
4. Evidence model and explainable attribution scoring.
5. VASP label/entity intelligence data model and provenance.
6. Investigation UI and graph behavior.
7. Evidence-backed reports and reproducibility.
8. Security controls and audit trail.
9. Evaluation dataset, metrics, and performance tests.
10. Additional chain adapters and deployment hardening.

## 5. Acceptance criteria for the next step

Before substantial feature work, agree on versioned contracts for normalized transactions, graph nodes/edges, attribution candidates, evidence records, and API errors. Preserve chain-specific transaction details so normalization does not erase important evidence.
