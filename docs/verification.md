# Localhost Verification & Evaluation Guide

This guide provides exact, tested step-by-step commands to independently verify the **S&P Sentinel** repository foundation on any standard Linux or macOS workstation.

---

## 1. Prerequisites

- **Python:** 3.11+
- **Package & Virtual Environment Manager:** `uv` (recommended) or standard `python3 -m venv` / `pip`
- **Node.js:** v20+ or v22 LTS (includes `npm`)
- **System Tools:** `curl`, `jq` (optional, for JSON formatting)

---

## 2. Step-by-Step Verification Procedure

### Step 1: Clone Repository
```bash
git clone https://github.com/amaannn08/iit-kharagpur-aman-gupta-hackathon.git
cd iit-kharagpur-aman-gupta-hackathon
```

### Step 2: Set Up Python Virtual Environment & Sync Dependencies
```bash
# Using uv (fast, deterministic)
uv venv --python 3.11 .venv
source .venv/bin/activate
uv sync

# Or using standard python3 venv fallback
# python3 -m venv .venv
# source .venv/bin/activate
# pip install -r requirements.txt
```

### Step 3: Run Backend Code Quality & Linter
```bash
uv run ruff check .
```
*Expected Result:* `All checks passed!`

### Step 4: Run Cryptographic Manifest & Repository Hygiene Verification
```bash
python scripts/verify_hygiene.py
```
*Expected Result:*
- Checks all 10 datasets in `data/manifest.json` against their on-disk byte sizes and SHA-256 hashes.
- Scans for forbidden secrets (`.env`, `.pem`, `.key`, `secrets.json`), database files (`.sqlite`), and large binaries (>20MB).
- Verifies zero external runtime calls in `src/sentinel`.
- Prints `ALL HYGIENE AND MANIFEST CHECKS PASSED SUCCESSFULLY.` with exit code 0.

### Step 5: Run Backend Test Suite
```bash
uv run pytest -v
```
*Expected Result:* 12 passed tests covering Pydantic contracts, news/social adapters, wholesale portfolio schemas, and FastAPI endpoints.

### Step 6: Verify Frontend Build & Test Suite
```bash
cd frontend
npm ci
npm test
npm run build
cd ..
```
*Expected Result:*
- Vitest passes all tests with active honesty badge assertion.
- TypeScript compiler (`tsc`) reports zero errors.
- Vite creates production bundle in `frontend/dist/`.

### Step 7: Live Backend Smoke Test
Start the backend server:
```bash
uv run uvicorn sentinel.api.app:app --host 127.0.0.1 --port 8000
```

In another terminal, test the operational endpoints:
```bash
# Verify health endpoint
curl -s http://127.0.0.1:8000/api/health | jq .

# Verify datasets catalog
curl -s http://127.0.0.1:8000/api/datasets | jq .

# Verify scenario catalog
curl -s http://127.0.0.1:8000/api/datasets/scenarios | jq .
```
*Expected Result:* HTTP 200 responses confirming `"status": "ok"`, `"datasets_ready": true`, and `"offline_only": true`.
