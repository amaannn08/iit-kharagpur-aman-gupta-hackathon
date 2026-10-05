# Evaluation Framework & Release Gates Specification

**Repository:** S&P Sentinel  
**Conforming PRD Sections:** Section 2.3 (Operational vs Quality Gates), Section 8 (Annotation Rubric), and Section 14 (Release Gates).

---

## 1. Binary Release Gates (Must Pass at Every Milestone)

Binary gates are non-negotiable architectural requirements that must strictly pass before any milestone release is accepted:

| Gate ID | Requirement | Acceptance Criterion | Verification Method |
|---|---|---|---|
| **BG-01** | Multi-Source Ingestion | News and Social CSV adapters successfully parse records into `InputRecord` models | `pytest tests/test_ingestion.py` |
| **BG-02** | Typed Data Contracts | Pydantic v2 validation enforces strict character bounds and sentiment probability sums ($P \approx 1.0$) | `pytest tests/test_contracts.py` |
| **BG-03** | Localhost Isolation | Zero runtime calls to external web APIs, cloud LLMs, or paid endpoints | `python scripts/verify_hygiene.py` |
| **BG-04** | Cryptographic Manifest | All bundled datasets match recorded SHA-256 and byte sizes in `data/manifest.json` | `python scripts/verify_hygiene.py` |
| **BG-05** | Local API Health Service | `GET /api/health` returns HTTP 200 with `"offline_only": true` and `"datasets_ready": true` | `pytest tests/test_api.py` |
| **BG-06** | Dark Terminal UI Build | React/TypeScript/Vite frontend builds cleanly with zero TypeScript errors | `npm run build && npm test` |
| **BG-07** | Replay Deduplication | Duplicate event shocks within 24 hours are suppressed from compound portfolio degradation | Replay test suite (M2) |

---

## 2. Quantitative NLP Quality Targets (Evaluated in Milestone M7)

Quality targets represent statistical performance benchmarks evaluated against the frozen gold-standard evaluation holdout dataset (`data/eval/holdout_seed.csv`):

| Task | Evaluation Metric | Minimum Target | Stretch Benchmark | Evaluation Method |
|---|---|---|---|---|
| **Domain Sentiment** | Macro-F1 (3-class) | $\ge 0.75$ | $\ge 0.85$ | Evaluated against `gold_sentiment_label` |
| **Event Classification** | Macro-F1 (9-class) | $\ge 0.70$ | $\ge 0.80$ | Evaluated against `gold_event_class` |
| **Entity Extraction & Linking** | Precision | $\ge 0.90$ | $\ge 0.95$ | Strict match to `gold_entity` ticker |
| **Impact Severity Scoring** | Mean Absolute Error (MAE) | $\le 1.50\text{ pts}$ | $\le 1.00\text{ pt}$ | Calculated on 1–10 scale against `gold_severity_score` |
| **Inference Latency** | CPU P95 Latency | $\le 150\text{ ms/item}$ | $\le 80\text{ ms/item}$ | Measured on local 4-core standard CPU |

---

## 3. Evaluation Holdout Dataset Structure

The ground truth holdout seed is frozen in [`data/eval/holdout_seed.csv`](../data/eval/holdout_seed.csv). Each evaluation row contains:

1. `eval_id`: Unique identifier (e.g. `eval-0001`).
2. `text`: Unstructured news or social post sentence.
3. `gold_entity`: Canonical ticker symbol of the impacted company (e.g. `APEX`, `QSEM`, `MACRO`).
4. `gold_sentiment_label`: Expert-labeled sentiment (`positive`, `negative`, `neutral`).
5. `gold_sentiment_score`: Continuous numerical score in $[-1.0, +1.0]$.
6. `gold_event_class`: Event taxonomy class from the 9 PRD classes (`CREDIT`, `MACRO`, `SUPPLY_CHAIN`, etc.).
7. `gold_severity_score`: Integer severity from 1 to 10 computed via the additive rubric.
8. `is_adversarial`: Boolean indicating adversarial test cases (negation, irony, complex clause syntax).

---

## 4. Evaluation Execution Procedure (Milestone M7)

In milestone M7, the evaluation runner script will be invoked as follows:

```bash
uv run python scripts/evaluate_models.py --dataset data/eval/holdout_seed.csv --output eval_report.json
```

The script produces a JSON and Markdown report comparing model predictions to gold labels, computing per-class precision, recall, F1, confusion matrices, and severity error distributions.
