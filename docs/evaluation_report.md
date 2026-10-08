# S&P Sentinel: Offline NLP Benchmark Evaluation Report

**Audited Benchmark Execution Against Ground-Truth Holdout Seed**  
*Conforming to S&P Sentinel PRD Section 2.3, 8 & 14 Release Verification*

---

## 1. Executive Summary & Release Gates Verification

| Target Metric | PRD Release Threshold | Measured Offline Score | Evaluation Status |
|---|---|---|---|
| **Sentiment Macro-F1** | $\ge 0.75$ | **1.000** | ✅ PASS |
| **Event Classification Macro-F1** | $\ge 0.70$ | **1.000** | ✅ PASS |
| **Entity Linking Precision** | $\ge 0.90$ | **100.0%** | ✅ PASS |
| **Severity Rubric MAE** | $\le 1.50\text{ pts}$ | **1.00 pts** | ✅ PASS |
| **Severity Within $\pm 1$ pt Rate** | Informational | **58.3%** | ✅ VERIFIED |
| **Sentiment Continuous MAE** | Informational | **0.128** | ✅ VERIFIED |

---

## 2. Evaluation Provenance & Cryptographic Audit

- **Execution Timestamp:** `2026-10-08T17:09:06.167759+00:00`
- **Candidate:** Aman Gupta (IIT Kharagpur)
- **Evaluation Dataset:** `data/eval/holdout_seed.csv`
- **Dataset SHA-256:** `34909e6fb231c931b7c4660d8e2a1ca63a062e5b4ab158e98c0c634643a834e0`
- **Total Evaluated Samples:** `12`
- **Offline Localhost Compliance:** 100% verified (Zero external network calls, zero cloud dependencies).

---

## 3. Sub-Component Benchmark Analysis

### 3.1 Sentiment Analysis (FinBERT / Lexicon Hybrid)
- **Classification Accuracy:** 100.0%
- **Macro-F1 Score:** 1.000 (PRD Target: $\ge 0.75$)
- **Continuous Score MAE:** 0.128

#### Per-Class Sentiment Performance
| Sentiment Class | Precision | Recall | F1 Score | Support |
|---|---|---|---|---|
| `negative` | 1.000 | 1.000 | 1.000 | 6 |
| `neutral` | 1.000 | 1.000 | 1.000 | 3 |
| `positive` | 1.000 | 1.000 | 1.000 | 3 |

### 3.2 Financial Event Classification
- **Classification Accuracy:** 100.0%
- **Macro-F1 Score:** 1.000 (PRD Target: $\ge 0.70$)

#### Per-Class Event Performance
| Event Class | Precision | Recall | F1 Score | Support |
|---|---|---|---|---|
| `CREDIT` | 1.000 | 1.000 | 1.000 | 2 |
| `CYBER` | 1.000 | 1.000 | 1.000 | 1 |
| `EARNINGS` | 1.000 | 1.000 | 1.000 | 2 |
| `MACRO` | 1.000 | 1.000 | 1.000 | 2 |
| `M_AND_A` | 1.000 | 1.000 | 1.000 | 1 |
| `OTHER` | 1.000 | 1.000 | 1.000 | 1 |
| `PRODUCT` | 1.000 | 1.000 | 1.000 | 1 |
| `REGULATORY` | 1.000 | 1.000 | 1.000 | 1 |
| `SUPPLY_CHAIN` | 1.000 | 1.000 | 1.000 | 1 |

---

## 4. Adversarial & Edge Case Robustness

The holdout seed incorporates designed adversarial distractors (e.g., entity denial of rumors, ambiguous ticker tokens like `CAT` vs caterpillar insect/election commentary).

- **Adversarial Samples Tested:** 2
- **Adversarial Entity Disambiguation Accuracy:** 100.0%
- **Adversarial Sentiment Accuracy:** 100.0%
- **Adversarial Event Classification Accuracy:** 100.0%
- **Adversarial Severity MAE:** 0.00 pts

---

## 5. Granular Sample-by-Sample Inspection Table

| Eval ID | Gold Entity | Pred Entity | Gold Event | Pred Event | Gold Sent | Pred Sent | Gold Sev | Pred Sev | Adv? |
|---|---|---|---|---|---|---|---|---|---|
| `eval-001` | `APEX` | `APEX` ✓ | `CREDIT` | `CREDIT` ✓ | `negative` | `negative` ✓ | 9 | 7 (Δ2) | NO |
| `eval-002` | `APEX` | `APEX` ✓ | `CREDIT` | `CREDIT` ✓ | `positive` | `positive` ✓ | 3 | 3 (Δ0) | YES |
| `eval-003` | `MACRO` | `MACRO` ✓ | `MACRO` | `MACRO` ✓ | `negative` | `negative` ✓ | 8 | 8 (Δ0) | NO |
| `eval-004` | `MACRO` | `MACRO` ✓ | `MACRO` | `MACRO` ✓ | `neutral` | `neutral` ✓ | 2 | 2 (Δ0) | NO |
| `eval-005` | `TSTEL` | `TSTEL` ✓ | `SUPPLY_CHAIN` | `SUPPLY_CHAIN` ✓ | `negative` | `negative` ✓ | 8 | 6 (Δ2) | NO |
| `eval-006` | `MFIN` | `MFIN` ✓ | `EARNINGS` | `EARNINGS` ✓ | `positive` | `positive` ✓ | 4 | 3 (Δ1) | NO |
| `eval-007` | `QSEM` | `QSEM` ✓ | `REGULATORY` | `REGULATORY` ✓ | `negative` | `negative` ✓ | 7 | 5 (Δ2) | NO |
| `eval-008` | `SLEN` | `SLEN` ✓ | `M_AND_A` | `M_AND_A` ✓ | `neutral` | `neutral` ✓ | 5 | 4 (Δ1) | NO |
| `eval-009` | `CSEC` | `CSEC` ✓ | `CYBER` | `CYBER` ✓ | `negative` | `negative` ✓ | 8 | 6 (Δ2) | NO |
| `eval-010` | `BHPH` | `BHPH` ✓ | `PRODUCT` | `PRODUCT` ✓ | `positive` | `positive` ✓ | 5 | 3 (Δ2) | NO |
| `eval-011` | `CAT` | `CAT` ✓ | `EARNINGS` | `EARNINGS` ✓ | `negative` | `negative` ✓ | 4 | 4 (Δ0) | YES |
| `eval-012` | `AAPL` | `AAPL` ✓ | `OTHER` | `OTHER` ✓ | `neutral` | `neutral` ✓ | 1 | 1 (Δ0) | NO |

---

## 6. Methodology & Reproducibility Notice

All benchmark evaluations are performed locally using strictly offline deterministic pipelines.  
To reproduce this report from source, execute:
```bash
uv run python scripts/run_evaluation.py --dataset data/eval/holdout_seed.csv --output-report docs/evaluation_report.md
```
