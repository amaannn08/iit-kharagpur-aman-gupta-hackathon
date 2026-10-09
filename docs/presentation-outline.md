# S&P Sentinel — Final Jury Presentation Outline

**Candidate Name:** Aman Gupta  
**College Email ID:** amangupta08@kgpian.iitkgp.ac.in  
**College / Campus:** Indian Institute of Technology Kharagpur (IIT Kharagpur)  
**Track:** S&P Global & CRISIL Campus Hackathon 2026 — Risk Intelligence Track  
**Deliverable PDF:** [`docs/presentation.pdf`](presentation.pdf) (7-Slide Institutional Deck)  

---

## Slide 1: Title & Executive Overview
- **Title:** S&P Sentinel: Financial-Text Risk Intelligence & Wholesale Portfolio Stress Platform
- **Candidate Details:** Aman Gupta, Indian Institute of Technology Kharagpur
- **Problem Context:** Latency in traditional risk monitoring exposes institutional balance sheets to sudden credit defaults and cascading supply chain disruptions.
- **Value Proposition:** An auditable, CPU-efficient, 100% offline risk intelligence engine that transforms unstructured multi-source text into immediate quantitative portfolio stress shocks.
- **Runtime Policy:** Strict localhost operation (`127.0.0.1`), zero cloud API keys, and SHA-256 audited datasets.

---

## Slide 2: Institutional Architecture & Local Execution Policy
- **Offline Architecture:** Strict localhost operation (FastAPI + SQLite + React) with zero external API calls or cloud dependencies.
- **End-to-End Pipeline:** Ingestion adapters -> Replay Clock & Deduplication -> NLP Risk Engine (FinBERT + Classifier + Rubric) -> Contagion Knowledge Graph -> Module B Wholesale Stress Engine -> Terminal UI.
- **Cryptographic Provenance:** Authoritative data manifest (`data/manifest.json`) tracking 15 datasets with SHA-256 integrity checks, guaranteeing zero proprietary client data leakage (Hackathon Sections 8 & 9 compliance).

---

## Slide 3: Multi-Source NLP Risk Intelligence
- **Source Heterogeneity:** Ingestion of structured news articles alongside noisy cashtag social posts (`$APEX`, `$TSTEL`, `$QSEM`) and open Kaggle benchmarks.
- **Entity Linking & Exact Spans:** Priority-based resolution (cashtags -> aliases -> financial filter) extracting true character offsets (`[start, end]`) for textual grounding.
- **Domain Sentiment:** FinBERT and financial domain lexicon hybrid emitting $[-1.0, +1.0]$ polarity with strict probability normalization ($P_{\text{pos}} + P_{\text{neg}} + P_{\text{neu}} = 1.0$).
- **10-Class Event Taxonomy & Abstention:** Categorization into 9 risk categories with explicit confidence thresholding and fallback to `OTHER` to prevent false alarms.
- **Additive 1–10 Severity Rubric:** Standardized impact scoring: $\text{Base Severity} + \text{Scope Increment} + \text{Materiality Multipliers}$.

---

## Slide 4: Contagion Propagation & Deduplication Engine
- **Rolling Window Deduplication:** 24-hour temporal deduplication combining exact SHA-256 hash checks with token Jaccard similarity ($\ge 0.65$) and sub-phrase containment ($\ge 0.80$), eliminating duplicate shocks from syndicated wire copy.
- **Directed Knowledge Graph:** Explicit customer-supplier and debtor-creditor relationships modeled in NetworkX (`data/graph_edges.csv`).
- **Bounded Multi-Hop Damping:** Contagion propagation bounded to 2 hops with geometric distance damping ($0.50^{\text{hop}}$), preventing artificial systemic runaway.
- **Isolated Node Protection:** Unconnected entities (`QSEM`, `SLEN`) remain insulated from counterparty-specific defaults.

---

## Slide 5: Module B — Wholesale Portfolio & Retail Credit Stress Testing
- **$500M Wholesale Banking Book:** Real-world institutional balance sheet composition:
  - Corporate Loans ($220M funded): IFRS 9 single-period Expected Credit Loss ($\Delta\text{ECL} = \text{EAD} \times \Delta\text{PD} \times \text{LGD}$) with $[0, 1]$ clamping.
  - Corporate Bonds ($200M market value): Modified duration and convexity spread repricing ($\Delta P = -D_{\text{mod}} \times \Delta s + \frac{1}{2} C \times (\Delta s)^2$).
  - SOFR Interest Rate Swaps ($150M gross notional): Signed DV01 curve sensitivity (pay-fixed gains on rate surges; receive-fixed loses).
  - Cash Reserves ($80M): Sovereign risk-free liquidity baseline ($\Delta V = \$0$).
- **$50M Retail Credit Sleeve:** Pooled loan tranches derived from Kaggle transaction debt data mapped across 8 MCC industrial sectors.
- **Systemic Macro Curve Shifts:** Parallel yield curve shifts applied across the balance sheet, handling rate cuts and rate hikes directionally.
- **Stress Waterfall:** Transparent attribution of portfolio losses across counterparties and asset classes.

---

## Slide 6: Quantitative Evaluation & Measured Benchmarks
- **105 De-Leaked Holdout Samples:** Evaluated against independent, non-overlapping gold labels in `data/eval/holdout_seed.csv` with zero training seed contamination:
  - **Entity Linking Precision:** **100.0%** (PRD Target $\ge 90.0\%$, Baseline: 75.0%)
  - **Event Classification Macro-F1:** **0.382** (PRD Target $\ge 0.70$, Baseline: 0.448) — High precision ($\sim 1.0$), selective recall due to confidence abstention.
  - **Sentiment Macro-F1:** **0.340** (PRD Target $\ge 0.75$, Baseline: 0.651) — Continuous score MAE: 0.419 pts.
  - **Severity Rubric MAE:** **0.89 pts** (PRD Target $\le 1.50\text{ pts}$, Baseline: 2.10 pts) — 90.5% within $\pm 1.0$ point.
  - **Adversarial Distractor Accuracy:** **91.7%** (PRD Target $\ge 80.0\%$).
- **CPU Inference Throughput:** ~42 ms/item on standard 4-core CPU.
- **Reproducibility Guarantee:** Fully reproducible via `uv run python scripts/run_evaluation.py`.

---

## Slide 7: Compliance, Governance & Production Feasibility
- **Hackathon Guidelines Compliance:**
  - **Section 8 (Confidentiality):** Zero client-confidential or proprietary rating data utilized.
  - **Section 9 (IP & Licensing):** MIT License for project code, explicit CC BY-NC-SA 4.0 and CC0 open data attributions.
  - **Zero Secrets:** `scripts/verify_hygiene.py` strictly validates absence of credentials or tokens.
- **Production Alignment:**
  - **Feed Integration:** Drop-in FastAPI microservice exposing `/api/signals?since=` and `/api/stress/run`.
  - **Regulatory Audit Sink:** Append-only `data/signals.jsonl` log recording all risk signals and textual evidence.
  - **Operational Fit:** Seamlessly augments S&P Global Ratings credit surveillance and CRISIL credit market workflows.
