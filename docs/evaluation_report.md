# S&P Sentinel: Offline NLP Benchmark Evaluation Report

**Audited Benchmark Execution Against Frozen Holdout Dataset (105 Samples)**
*Conforming to S&P Sentinel PRD Section 2.3, 4.2, 8 & 13.1 Release Verification*

---

## 1. Executive Summary & Baseline Comparison

| Evaluation Target | PRD Threshold | Rule Baseline | Sentinel Model | Status |
|---|---|---|---|---|
| **Event Classification Macro-F1** | $\ge 0.70$ | 0.651 | **0.382** | ❌ FAIL |
| **Sentiment Macro-F1** | $\ge 0.75$ | 0.340 | **0.340** | ❌ FAIL |
| **Entity Disambiguation Precision** | $\ge 0.90$ | N/A | **48.6%** | ❌ FAIL |
| **Severity Rubric MAE** | $\le 1.50\text{ pts}$ | N/A | **2.70 pts** | ❌ FAIL |
| **Severity Within $\pm 1$ pt Rate** | Informational | N/A | **31.4%** | ✅ VERIFIED |
| **Sentiment Continuous MAE** | Informational | N/A | **0.498** | ✅ VERIFIED |

---

## 2. Evaluation Provenance & Cryptographic Audit

- **Execution Timestamp:** `2026-10-09T06:37:11.955943+00:00`
- **Author / Candidate:** Aman Gupta (IIT Kharagpur)
- **Holdout Dataset:** `data/eval/holdout_seed.csv`
- **Holdout SHA-256:** `3e58b8c449507921811a31d940854b8509a50d5b5044db589cd8343abb801260`
- **Total Evaluated Samples:** `105` (Exceeds PRD §4.2 gate of $\ge 100$)
- **Data Leakage Check:** Clean (Held-out samples strictly separated from training seeds; no phrase overrides).
- **Offline Execution:** 100% verified (Zero external API keys, zero cloud inference).

---

## 3. Detailed Component Benchmark Analysis

### 3.1 Financial Event Classification
- **Overall Accuracy:** 34.3%
- **Macro-F1 Score:** 0.382 (PRD Target: $\ge 0.70$ | Baseline: 0.651)

#### Per-Class Event Performance & Support
| Event Class | Precision | Recall | F1 Score | Support |
|---|---|---|---|---|
| `CREDIT` | 1.000 | 0.455 | 0.625 | 11 |
| `CYBER` | 1.000 | 0.300 | 0.462 | 10 |
| `EARNINGS` | 1.000 | 0.091 | 0.167 | 11 |
| `GEOPOLITICAL` | 1.000 | 0.273 | 0.429 | 11 |
| `MACRO` | 1.000 | 0.636 | 0.778 | 11 |
| `M_AND_A` | 1.000 | 0.100 | 0.182 | 10 |
| `OTHER` | 0.127 | 1.000 | 0.225 | 10 |
| `PRODUCT` | 1.000 | 0.100 | 0.182 | 10 |
| `REGULATORY` | 1.000 | 0.300 | 0.462 | 10 |
| `SUPPLY_CHAIN` | 1.000 | 0.182 | 0.308 | 11 |

#### Event Classification Confusion Matrix (Rows = True, Columns = Predicted)

| True \ Pred | `CREDI` | `CYBER` | `EARNI` | `GEOPO` | `MACRO` | `M_AND` | `OTHER` | `PRODU` | `REGUL` | `SUPPL` |
|---|---|---|---|---|---|---|---|---|---|---|
| `CREDIT` | 5 | 0 | 0 | 0 | 0 | 0 | 6 | 0 | 0 | 0 |
| `CYBER` | 0 | 3 | 0 | 0 | 0 | 0 | 7 | 0 | 0 | 0 |
| `EARNINGS` | 0 | 0 | 1 | 0 | 0 | 0 | 10 | 0 | 0 | 0 |
| `GEOPOLITICAL` | 0 | 0 | 0 | 3 | 0 | 0 | 8 | 0 | 0 | 0 |
| `MACRO` | 0 | 0 | 0 | 0 | 7 | 0 | 4 | 0 | 0 | 0 |
| `M_AND_A` | 0 | 0 | 0 | 0 | 0 | 1 | 9 | 0 | 0 | 0 |
| `OTHER` | 0 | 0 | 0 | 0 | 0 | 0 | 10 | 0 | 0 | 0 |
| `PRODUCT` | 0 | 0 | 0 | 0 | 0 | 0 | 9 | 1 | 0 | 0 |
| `REGULATORY` | 0 | 0 | 0 | 0 | 0 | 0 | 7 | 0 | 3 | 0 |
| `SUPPLY_CHAIN` | 0 | 0 | 0 | 0 | 0 | 0 | 9 | 0 | 0 | 2 |

### 3.2 Sentiment Analysis (FinBERT / Lexicon Hybrid)
- **Overall Accuracy:** 34.3%
- **Macro-F1 Score:** 0.340 (PRD Target: $\ge 0.75$ | Baseline: 0.340)
- **Continuous Score MAE:** 0.498

#### Per-Class Sentiment Performance & Support
| Sentiment Class | Precision | Recall | F1 Score | Support |
|---|---|---|---|---|
| `negative` | 0.917 | 0.244 | 0.386 | 45 |
| `neutral` | 0.230 | 0.773 | 0.354 | 22 |
| `positive` | 0.421 | 0.211 | 0.281 | 38 |

#### Sentiment Confusion Matrix (Rows = True, Columns = Predicted)

| True \ Pred | `negative` | `neutral` | `positive` |
|---|---|---|---|
| `negative` | 11 | 28 | 6 |
| `neutral` | 0 | 17 | 5 |
| `positive` | 1 | 29 | 8 |

---

## 4. Adversarial & Edge Case Robustness

The holdout dataset incorporates designed adversarial test cases (rumor denials, routine filings with buzzwords, in-line guidance).
- **Adversarial Samples Tested:** 10
- **Entity Precision:** 30.0%
- **Sentiment Accuracy:** 60.0%
- **Event Classification Accuracy:** 30.0%
- **Severity MAE:** 1.60 pts

---

## 5. Granular Sample-by-Sample Inspection Table

| Eval ID | Gold Entity | Pred Entity | Gold Event | Pred Event | Gold Sent | Pred Sent | Gold Sev | Pred Sev | Adv? |
|---|---|---|---|---|---|---|---|---|---|
| `eval-001` | `APEX` | `APEX` ✓ | `CREDIT` | `CREDIT` ✓ | `negative` | `negative` ✓ | 8 | 6 (Δ2) | NO |
| `eval-002` | `APEX` | `APEX` ✓ | `CREDIT` | `CREDIT` ✓ | `negative` | `neutral` ✗ | 9 | 6 (Δ3) | NO |
| `eval-003` | `SLEN` | `SLEN` ✓ | `CREDIT` | `OTHER` ✗ | `positive` | `neutral` ✗ | 3 | 2 (Δ1) | NO |
| `eval-004` | `TSTEL` | `TSTEL` ✓ | `CREDIT` | `OTHER` ✗ | `neutral` | `neutral` ✓ | 5 | 2 (Δ3) | NO |
| `eval-005` | `GLOG` | `GLOG` ✓ | `CREDIT` | `OTHER` ✗ | `negative` | `negative` ✓ | 6 | 5 (Δ1) | NO |
| `eval-006` | `FSBK` | `FSBK` ✓ | `CREDIT` | `CREDIT` ✓ | `negative` | `negative` ✓ | 8 | 5 (Δ3) | NO |
| `eval-007` | `MFIN` | `MFIN` ✓ | `CREDIT` | `OTHER` ✗ | `negative` | `positive` ✗ | 4 | 1 (Δ3) | NO |
| `eval-008` | `APEX` | `APEX` ✓ | `CREDIT` | `CREDIT` ✓ | `positive` | `neutral` ✗ | 3 | 5 (Δ2) | YES |
| `eval-009` | `QSEM` | `QSEM` ✓ | `CREDIT` | `CREDIT` ✓ | `negative` | `neutral` ✗ | 6 | 7 (Δ1) | NO |
| `eval-010` | `MACRO` | `Unknown Entity` ✗ | `CREDIT` | `OTHER` ✗ | `positive` | `neutral` ✗ | 2 | 1 (Δ1) | NO |
| `eval-011` | `APEX` | `Unknown Entity` ✗ | `CREDIT` | `OTHER` ✗ | `negative` | `neutral` ✗ | 8 | 1 (Δ7) | NO |
| `eval-012` | `MACRO` | `MACRO` ✓ | `MACRO` | `MACRO` ✓ | `negative` | `negative` ✓ | 8 | 7 (Δ1) | NO |
| `eval-013` | `MACRO` | `MACRO` ✓ | `MACRO` | `MACRO` ✓ | `positive` | `neutral` ✗ | 7 | 7 (Δ0) | NO |
| `eval-014` | `MACRO` | `Unknown Entity` ✗ | `MACRO` | `OTHER` ✗ | `negative` | `positive` ✗ | 6 | 1 (Δ5) | NO |
| `eval-015` | `MACRO` | `MACRO` ✓ | `MACRO` | `MACRO` ✓ | `negative` | `positive` ✗ | 7 | 7 (Δ0) | NO |
| `eval-016` | `MACRO` | `MACRO` ✓ | `MACRO` | `MACRO` ✓ | `neutral` | `neutral` ✓ | 2 | 5 (Δ3) | NO |
| `eval-017` | `MACRO` | `Unknown Entity` ✗ | `MACRO` | `OTHER` ✗ | `positive` | `neutral` ✗ | 4 | 1 (Δ3) | NO |
| `eval-018` | `MACRO` | `Unknown Entity` ✗ | `MACRO` | `OTHER` ✗ | `negative` | `neutral` ✗ | 5 | 1 (Δ4) | NO |
| `eval-019` | `MACRO` | `MACRO` ✓ | `MACRO` | `MACRO` ✓ | `positive` | `positive` ✓ | 4 | 7 (Δ3) | NO |
| `eval-020` | `MACRO` | `Unknown Entity` ✗ | `MACRO` | `MACRO` ✓ | `negative` | `neutral` ✗ | 6 | 5 (Δ1) | NO |
| `eval-021` | `MACRO` | `Unknown Entity` ✗ | `MACRO` | `OTHER` ✗ | `neutral` | `neutral` ✓ | 2 | 1 (Δ1) | NO |
| `eval-022` | `MACRO` | `MACRO` ✓ | `MACRO` | `MACRO` ✓ | `neutral` | `neutral` ✓ | 3 | 7 (Δ4) | YES |
| `eval-023` | `LITH` | `Unknown Entity` ✗ | `GEOPOLITICAL` | `GEOPOLITICAL` ✓ | `negative` | `neutral` ✗ | 8 | 7 (Δ1) | NO |
| `eval-024` | `SLEN` | `Unknown Entity` ✗ | `GEOPOLITICAL` | `GEOPOLITICAL` ✓ | `negative` | `neutral` ✗ | 8 | 5 (Δ3) | NO |
| `eval-025` | `CAT` | `Unknown Entity` ✗ | `GEOPOLITICAL` | `GEOPOLITICAL` ✓ | `positive` | `neutral` ✗ | 4 | 5 (Δ1) | NO |
| `eval-026` | `QSEM` | `Unknown Entity` ✗ | `GEOPOLITICAL` | `OTHER` ✗ | `negative` | `neutral` ✗ | 7 | 1 (Δ6) | NO |
| `eval-027` | `SLEN` | `Unknown Entity` ✗ | `GEOPOLITICAL` | `OTHER` ✗ | `negative` | `neutral` ✗ | 9 | 1 (Δ8) | NO |
| `eval-028` | `SLEN` | `Unknown Entity` ✗ | `GEOPOLITICAL` | `OTHER` ✗ | `negative` | `neutral` ✗ | 8 | 1 (Δ7) | NO |
| `eval-029` | `PTEL` | `Unknown Entity` ✗ | `GEOPOLITICAL` | `OTHER` ✗ | `positive` | `neutral` ✗ | 3 | 1 (Δ2) | NO |
| `eval-030` | `VAUTO` | `Unknown Entity` ✗ | `GEOPOLITICAL` | `OTHER` ✗ | `negative` | `neutral` ✗ | 7 | 1 (Δ6) | NO |
| `eval-031` | `GLOG` | `Unknown Entity` ✗ | `GEOPOLITICAL` | `OTHER` ✗ | `positive` | `neutral` ✗ | 3 | 1 (Δ2) | NO |
| `eval-032` | `MACRO` | `Unknown Entity` ✗ | `GEOPOLITICAL` | `OTHER` ✗ | `negative` | `neutral` ✗ | 8 | 1 (Δ7) | NO |
| `eval-033` | `MACRO` | `Unknown Entity` ✗ | `GEOPOLITICAL` | `OTHER` ✗ | `neutral` | `neutral` ✓ | 2 | 1 (Δ1) | YES |
| `eval-034` | `TSTEL` | `TSTEL` ✓ | `SUPPLY_CHAIN` | `OTHER` ✗ | `negative` | `negative` ✓ | 8 | 5 (Δ3) | NO |
| `eval-035` | `GLOG` | `Unknown Entity` ✗ | `SUPPLY_CHAIN` | `SUPPLY_CHAIN` ✓ | `negative` | `neutral` ✗ | 8 | 5 (Δ3) | NO |
| `eval-036` | `VAUTO` | `VAUTO` ✓ | `SUPPLY_CHAIN` | `OTHER` ✗ | `negative` | `neutral` ✗ | 7 | 1 (Δ6) | NO |
| `eval-037` | `LITH` | `LITH` ✓ | `SUPPLY_CHAIN` | `OTHER` ✗ | `positive` | `positive` ✓ | 4 | 1 (Δ3) | NO |
| `eval-038` | `GLOG` | `Unknown Entity` ✗ | `SUPPLY_CHAIN` | `OTHER` ✗ | `positive` | `neutral` ✗ | 3 | 1 (Δ2) | NO |
| `eval-039` | `GLOG` | `Unknown Entity` ✗ | `SUPPLY_CHAIN` | `OTHER` ✗ | `negative` | `neutral` ✗ | 6 | 1 (Δ5) | NO |
| `eval-040` | `TSTEL` | `Unknown Entity` ✗ | `SUPPLY_CHAIN` | `SUPPLY_CHAIN` ✓ | `negative` | `negative` ✓ | 7 | 7 (Δ0) | NO |
| `eval-041` | `GLOG` | `GLOG` ✓ | `SUPPLY_CHAIN` | `OTHER` ✗ | `positive` | `neutral` ✗ | 3 | 3 (Δ0) | NO |
| `eval-042` | `QSEM` | `Unknown Entity` ✗ | `SUPPLY_CHAIN` | `OTHER` ✗ | `positive` | `positive` ✓ | 3 | 1 (Δ2) | NO |
| `eval-043` | `TSTEL` | `TSTEL` ✓ | `SUPPLY_CHAIN` | `OTHER` ✗ | `neutral` | `neutral` ✓ | 2 | 1 (Δ1) | YES |
| `eval-044` | `GLOG` | `Unknown Entity` ✗ | `SUPPLY_CHAIN` | `OTHER` ✗ | `negative` | `neutral` ✗ | 4 | 1 (Δ3) | NO |
| `eval-045` | `MFIN` | `MFIN` ✓ | `EARNINGS` | `EARNINGS` ✓ | `positive` | `positive` ✓ | 4 | 3 (Δ1) | NO |
| `eval-046` | `CAT` | `CAT` ✓ | `EARNINGS` | `OTHER` ✗ | `negative` | `neutral` ✗ | 5 | 3 (Δ2) | NO |
| `eval-047` | `AAPL` | `AAPL` ✓ | `EARNINGS` | `OTHER` ✗ | `positive` | `positive` ✓ | 4 | 1 (Δ3) | NO |
| `eval-048` | `APEX` | `APEX` ✓ | `EARNINGS` | `OTHER` ✗ | `negative` | `positive` ✗ | 7 | 1 (Δ6) | NO |
| `eval-049` | `MSFT` | `MSFT` ✓ | `EARNINGS` | `OTHER` ✗ | `positive` | `positive` ✓ | 4 | 1 (Δ3) | NO |
| `eval-050` | `XOM` | `Unknown Entity` ✗ | `EARNINGS` | `OTHER` ✗ | `negative` | `positive` ✗ | 5 | 1 (Δ4) | NO |
| `eval-051` | `JPM` | `JPM` ✓ | `EARNINGS` | `OTHER` ✗ | `positive` | `negative` ✗ | 4 | 1 (Δ3) | NO |
| `eval-052` | `BA` | `Unknown Entity` ✗ | `EARNINGS` | `OTHER` ✗ | `negative` | `negative` ✓ | 7 | 2 (Δ5) | NO |
| `eval-053` | `SLEN` | `SLEN` ✓ | `EARNINGS` | `OTHER` ✗ | `positive` | `neutral` ✗ | 3 | 1 (Δ2) | NO |
| `eval-054` | `WMT` | `Unknown Entity` ✗ | `EARNINGS` | `OTHER` ✗ | `positive` | `neutral` ✗ | 3 | 1 (Δ2) | NO |
| `eval-055` | `AAPL` | `Unknown Entity` ✗ | `EARNINGS` | `OTHER` ✗ | `neutral` | `positive` ✗ | 2 | 1 (Δ1) | YES |
| `eval-056` | `SLEN` | `SLEN` ✓ | `M_AND_A` | `OTHER` ✗ | `positive` | `neutral` ✗ | 6 | 1 (Δ5) | NO |
| `eval-057` | `APEX` | `APEX` ✓ | `M_AND_A` | `OTHER` ✗ | `neutral` | `neutral` ✓ | 7 | 1 (Δ6) | NO |
| `eval-058` | `MFIN` | `MFIN` ✓ | `M_AND_A` | `OTHER` ✗ | `positive` | `neutral` ✗ | 4 | 1 (Δ3) | NO |
| `eval-059` | `DCLD` | `CSEC` ✗ | `M_AND_A` | `OTHER` ✗ | `negative` | `negative` ✓ | 6 | 1 (Δ5) | NO |
| `eval-060` | `LITH` | `LITH` ✓ | `M_AND_A` | `M_AND_A` ✓ | `positive` | `neutral` ✗ | 6 | 4 (Δ2) | NO |
| `eval-061` | `VAUTO` | `VAUTO` ✓ | `M_AND_A` | `OTHER` ✗ | `positive` | `neutral` ✗ | 4 | 1 (Δ3) | NO |
| `eval-062` | `GLOG` | `Unknown Entity` ✗ | `M_AND_A` | `OTHER` ✗ | `neutral` | `neutral` ✓ | 5 | 1 (Δ4) | NO |
| `eval-063` | `PTEL` | `Unknown Entity` ✗ | `M_AND_A` | `OTHER` ✗ | `positive` | `neutral` ✗ | 4 | 1 (Δ3) | NO |
| `eval-064` | `PFE` | `Unknown Entity` ✗ | `M_AND_A` | `OTHER` ✗ | `positive` | `neutral` ✗ | 5 | 1 (Δ4) | NO |
| `eval-065` | `APEX` | `Unknown Entity` ✗ | `M_AND_A` | `OTHER` ✗ | `neutral` | `neutral` ✓ | 4 | 1 (Δ3) | YES |
| `eval-066` | `QSEM` | `QSEM` ✓ | `REGULATORY` | `REGULATORY` ✓ | `negative` | `negative` ✓ | 7 | 5 (Δ2) | NO |
| `eval-067` | `APEX` | `Unknown Entity` ✗ | `REGULATORY` | `REGULATORY` ✓ | `negative` | `positive` ✗ | 7 | 5 (Δ2) | NO |
| `eval-068` | `FSBK` | `FSBK` ✓ | `REGULATORY` | `REGULATORY` ✓ | `negative` | `neutral` ✗ | 6 | 4 (Δ2) | NO |
| `eval-069` | `CAT` | `Unknown Entity` ✗ | `REGULATORY` | `OTHER` ✗ | `positive` | `neutral` ✗ | 3 | 1 (Δ2) | NO |
| `eval-070` | `TSTEL` | `TSTEL` ✓ | `REGULATORY` | `OTHER` ✗ | `negative` | `neutral` ✗ | 6 | 1 (Δ5) | NO |
| `eval-071` | `MFIN` | `Unknown Entity` ✗ | `REGULATORY` | `OTHER` ✗ | `positive` | `neutral` ✗ | 2 | 1 (Δ1) | NO |
| `eval-072` | `DCLD` | `DCLD` ✓ | `REGULATORY` | `OTHER` ✗ | `negative` | `neutral` ✗ | 5 | 1 (Δ4) | NO |
| `eval-073` | `SLEN` | `Unknown Entity` ✗ | `REGULATORY` | `OTHER` ✗ | `positive` | `neutral` ✗ | 3 | 1 (Δ2) | NO |
| `eval-074` | `AAPL` | `Unknown Entity` ✗ | `REGULATORY` | `OTHER` ✗ | `positive` | `neutral` ✗ | 2 | 1 (Δ1) | YES |
| `eval-075` | `MFIN` | `Unknown Entity` ✗ | `REGULATORY` | `OTHER` ✗ | `negative` | `neutral` ✗ | 6 | 1 (Δ5) | NO |
| `eval-076` | `CSEC` | `CSEC` ✓ | `CYBER` | `CYBER` ✓ | `negative` | `negative` ✓ | 8 | 7 (Δ1) | NO |
| `eval-077` | `FSBK` | `FSBK` ✓ | `CYBER` | `OTHER` ✗ | `negative` | `negative` ✓ | 9 | 3 (Δ6) | NO |
| `eval-078` | `DCLD` | `DCLD` ✓ | `CYBER` | `CYBER` ✓ | `positive` | `neutral` ✗ | 3 | 5 (Δ2) | NO |
| `eval-079` | `CSEC` | `Unknown Entity` ✗ | `CYBER` | `OTHER` ✗ | `negative` | `neutral` ✗ | 7 | 1 (Δ6) | NO |
| `eval-080` | `AAPL` | `Unknown Entity` ✗ | `CYBER` | `OTHER` ✗ | `neutral` | `positive` ✗ | 3 | 1 (Δ2) | YES |
| `eval-081` | `CSEC` | `Unknown Entity` ✗ | `CYBER` | `OTHER` ✗ | `negative` | `neutral` ✗ | 6 | 1 (Δ5) | NO |
| `eval-082` | `QSEM` | `QSEM` ✓ | `CYBER` | `OTHER` ✗ | `negative` | `neutral` ✗ | 8 | 1 (Δ7) | NO |
| `eval-083` | `PTEL` | `PTEL` ✓ | `CYBER` | `OTHER` ✗ | `positive` | `neutral` ✗ | 3 | 1 (Δ2) | NO |
| `eval-084` | `FSBK` | `Unknown Entity` ✗ | `CYBER` | `CYBER` ✓ | `negative` | `neutral` ✗ | 7 | 5 (Δ2) | NO |
| `eval-085` | `CSEC` | `CSEC` ✓ | `CYBER` | `OTHER` ✗ | `positive` | `neutral` ✗ | 2 | 1 (Δ1) | NO |
| `eval-086` | `BHPH` | `BHPH` ✓ | `PRODUCT` | `PRODUCT` ✓ | `positive` | `positive` ✓ | 4 | 3 (Δ1) | NO |
| `eval-087` | `VAUTO` | `VAUTO` ✓ | `PRODUCT` | `OTHER` ✗ | `negative` | `neutral` ✗ | 6 | 1 (Δ5) | NO |
| `eval-088` | `QSEM` | `QSEM` ✓ | `PRODUCT` | `OTHER` ✗ | `positive` | `positive` ✓ | 3 | 1 (Δ2) | NO |
| `eval-089` | `BHPH` | `Unknown Entity` ✗ | `PRODUCT` | `OTHER` ✗ | `negative` | `neutral` ✗ | 8 | 1 (Δ7) | NO |
| `eval-090` | `PTEL` | `PTEL` ✓ | `PRODUCT` | `OTHER` ✗ | `positive` | `neutral` ✗ | 3 | 1 (Δ2) | NO |
| `eval-091` | `BA` | `Unknown Entity` ✗ | `PRODUCT` | `OTHER` ✗ | `positive` | `neutral` ✗ | 4 | 1 (Δ3) | NO |
| `eval-092` | `BHPH` | `BHPH` ✓ | `PRODUCT` | `OTHER` ✗ | `positive` | `neutral` ✗ | 3 | 1 (Δ2) | NO |
| `eval-093` | `AAPL` | `Unknown Entity` ✗ | `PRODUCT` | `OTHER` ✗ | `negative` | `neutral` ✗ | 6 | 1 (Δ5) | NO |
| `eval-094` | `MSFT` | `Unknown Entity` ✗ | `PRODUCT` | `OTHER` ✗ | `neutral` | `neutral` ✓ | 1 | 1 (Δ0) | YES |
| `eval-095` | `SLEN` | `Unknown Entity` ✗ | `PRODUCT` | `OTHER` ✗ | `positive` | `neutral` ✗ | 3 | 1 (Δ2) | NO |
| `eval-096` | `AAPL` | `Unknown Entity` ✗ | `OTHER` | `OTHER` ✓ | `neutral` | `neutral` ✓ | 1 | 1 (Δ0) | NO |
| `eval-097` | `MSFT` | `MSFT` ✓ | `OTHER` | `OTHER` ✓ | `neutral` | `positive` ✗ | 1 | 1 (Δ0) | NO |
| `eval-098` | `CAT` | `Unknown Entity` ✗ | `OTHER` | `OTHER` ✓ | `neutral` | `neutral` ✓ | 1 | 1 (Δ0) | NO |
| `eval-099` | `MFIN` | `MFIN` ✓ | `OTHER` | `OTHER` ✓ | `neutral` | `neutral` ✓ | 1 | 1 (Δ0) | NO |
| `eval-100` | `SLEN` | `SLEN` ✓ | `OTHER` | `OTHER` ✓ | `neutral` | `neutral` ✓ | 1 | 1 (Δ0) | NO |
| `eval-101` | `TSTEL` | `TSTEL` ✓ | `OTHER` | `OTHER` ✓ | `neutral` | `neutral` ✓ | 1 | 1 (Δ0) | NO |
| `eval-102` | `XOM` | `Unknown Entity` ✗ | `OTHER` | `OTHER` ✓ | `neutral` | `positive` ✗ | 1 | 1 (Δ0) | NO |
| `eval-103` | `JPM` | `Unknown Entity` ✗ | `OTHER` | `OTHER` ✓ | `neutral` | `positive` ✗ | 1 | 1 (Δ0) | NO |
| `eval-104` | `MSFT` | `Unknown Entity` ✗ | `OTHER` | `OTHER` ✓ | `neutral` | `neutral` ✓ | 2 | 1 (Δ1) | YES |
| `eval-105` | `CAT` | `Unknown Entity` ✗ | `OTHER` | `OTHER` ✓ | `neutral` | `neutral` ✓ | 1 | 1 (Δ0) | NO |

---

## 6. Reproducibility Notice

To reproduce this evaluation report deterministically from source code:
```bash
uv run python scripts/run_evaluation.py
```
