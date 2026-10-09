# Localhost Verification & Evaluation Guide

**Repository:** S&P Sentinel — Financial Text Risk Intelligence & Wholesale Portfolio Stress Platform  
**Author:** Aman Gupta (Indian Institute of Technology Kharagpur)  

This guide provides tested, reproducible step-by-step commands to independently verify the complete **S&P Sentinel** platform on any standard Linux or macOS workstation with zero external cloud dependencies.

---

## 1. Prerequisites

- **Python:** 3.11+
- **Package Manager:** `uv` (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- **Node.js:** v20+ or v22 LTS (includes `npm`)
- **System Tools:** `curl`, `jq` (optional, for JSON inspection)

---

## 2. Step-by-Step Verification Procedure

### Step 1: Clone Repository
```bash
git clone https://github.com/amaannn08/iit-kharagpur-aman-gupta-hackathon.git
cd iit-kharagpur-aman-gupta-hackathon
```

### Step 2: Install Dependencies
```bash
# Backend dependencies (FastAPI, PyTorch, Transformers, ReportLab, Matplotlib)
uv sync --all-extras

# Frontend dependencies (React 18, TypeScript, Tailwind CSS, Lucide)
cd frontend && npm install && cd ..
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
- Checks all **15 datasets** listed in `data/manifest.json` against their on-disk byte sizes and SHA-256 cryptographic hashes.
- Scans for forbidden secrets (`.env`, `.pem`, `.key`, `secrets.json`), database files (`.sqlite`), and large binaries (>20MB).
- Verifies zero external runtime calls in `src/sentinel`.
- Prints `ALL HYGIENE AND MANIFEST CHECKS PASSED SUCCESSFULLY.` with exit code 0.

### Step 5: Run Full Backend Test Suite
```bash
uv run pytest -v
```
*Expected Result:* **71 passed tests** covering:
- Pydantic v2 data contracts (`test_contracts.py`)
- Multi-source news and social adapters (`test_ingestion.py`)
- True character offset entity linking (`test_nlp_entities.py`)
- FinBERT sentiment calibration and probability sums (`test_nlp_sentiment.py`)
- 10-class event classification and abstention (`test_nlp_events.py`)
- Additive 1–10 severity scoring rubric (`test_nlp_severity.py`)
- Jaccard & containment near-duplicate deduplication (`test_dedup.py`)
- Replay clock and controller (`test_replay_clock.py`, `test_replay_controller.py`)
- Multi-hop contagion propagation and wholesale valuation (`test_stress_valuation.py`)
- FastAPI endpoints, signals file sink, and crisis scenarios (`test_api.py`, `test_api_signals.py`, `test_api_stress.py`)

### Step 6: Verify Frontend Build & Test Suite
```bash
cd frontend
npm test
npm run build
cd ..
```
*Expected Result:*
- Vitest passes all **4 test suites** confirming terminal rendering, signals inspector, and honesty badge.
- TypeScript compiler (`tsc`) reports zero errors.
- Vite generates production bundle in `frontend/dist/`.

### Step 7: Reproduce De-Leaked NLP Benchmark Evaluation
```bash
uv run python scripts/run_evaluation.py
```
*Expected Result:*
- Evaluates the NLP risk engine against the independent 105-sample holdout dataset (`data/eval/holdout_seed.csv`).
- Displays confusion matrices, per-class support tables, continuous MAE, and comparison against keyword/lexicon baselines.
- Regenerates `docs/evaluation_report.md`.


### Step 9: Re-generate Architecture Diagram & Presentation Deck
```bash
# Generate high-resolution architecture schematic
python scripts/generate_architecture_diagram.py

# Generate 7-slide institutional presentation deck PDF
uv run python scripts/generate_presentation_pdf.py
```
*Expected Result:*
- Produces `docs/architecture.png` (high-res dark theme architecture diagram).
- Produces `docs/presentation.pdf` (7-slide institutional presentation deck).

### Step 10: Live Backend & Terminal Smoke Test
Start the backend server:
```bash
uv run uvicorn sentinel.api.app:app --host 127.0.0.1 --port 8000
```

In another terminal, test operational endpoints:
```bash
# 1. Operational health check
curl -s http://127.0.0.1:8000/api/health | jq .

# 2. Registered datasets catalog
curl -s http://127.0.0.1:8000/api/datasets | jq .

# 3. Stream signals with since filtering
curl -s "http://127.0.0.1:8000/api/signals?since=2026-01-01T00:00:00Z" | jq .

# 4. Trigger wholesale stress scenario run
curl -s -X POST http://127.0.0.1:8000/api/stress/run \
  -H "Content-Type: application/json" \
  -d '{"scenario_name": "credit_crunch"}' | jq .
```

Verify that signals are appended to the literal file sink:
```bash
head -n 5 data/signals.jsonl
```

Launch the frontend terminal:
```bash
cd frontend && npm run dev
```
Navigate to `http://localhost:5173` in your browser.
