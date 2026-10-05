# S&P Sentinel — Final Jury Presentation Outline

**Candidate Name:** Aman Gupta  
**College Email ID:** amangupta08@kgpian.iitkgp.ac.in  
**College / Campus:** Indian Institute of Technology Kharagpur (IIT Kharagpur)  
**Track:** S&P Global & CRISIL Campus Hackathon 2026 — Risk Intelligence Track  
**Deliverable Note:** In accordance with PRD Section 16, this document specifies the structured 5–7 slide narrative designed for milestone M10. The compiled slide deck PDF (`docs/presentation.pdf`) and unlisted demo video will be finalized in M10 once final measured holdout metrics and portfolio stress runs are recorded.

---

## Slide 1: Title & Executive Overview
- **Title:** S&P Sentinel: Financial-Text Risk Intelligence & Wholesale Portfolio Stress Platform
- **Candidate Details:** Aman Gupta, Indian Institute of Technology Kharagpur
- **Problem Context:** Latency in traditional risk monitoring exposes institutional balance sheets to sudden credit defaults and cascading supply chain disruptions.
- **Value Proposition:** An auditable, CPU-efficient, 100% offline risk intelligence engine that transforms unstructured multi-source text into immediate quantitative portfolio stress shocks.

---

## Slide 2: Institutional Architecture & Local Execution Policy
- **Offline Architecture:** Strict localhost operation (FastAPI + SQLite + React) with zero external API calls or cloud dependencies.
- **End-to-End Pipeline:** Ingestion adapters -> Replay Clock & Deduplication -> NLP Risk Engine (FinBERT + Classifier + Rubric) -> Contagion Knowledge Graph -> Module B Wholesale Stress Engine.
- **Cryptographic Provenance:** Authoritative data manifest with SHA-256 integrity checks, guaranteeing zero proprietary client data leakage (Hackathon Section 8 & 9 compliance).

---

## Slide 3: Multi-Source NLP Risk Intelligence
- **Source Heterogeneity:** Handling structured news articles alongside noisy cashtag social posts (`$APEX`, `$QSEM`).
- **Domain Sentiment:** FinBERT $[-1.0, +1.0]$ distribution with probability validation.
- **Event Taxonomy & Severity:** 9-class categorization (`CREDIT`, `MACRO`, `SUPPLY_CHAIN`, etc.) coupled with an additive 1–10 impact severity score ($Base + Scope + Multiplier$).
- **Explainability:** Mandatory evidence span extraction ensuring every signal is grounded in source text.

---

## Slide 4: Contagion Propagation & Deduplication
- **Deduplication Window:** 24-hour entity-event suppression preventing duplicate shocks from multiple news echoes.
- **Knowledge Graph Topology:** Directed customer-supplier and credit linkages modeled in NetworkX.
- **Bounded Propagation:** 2-hop dampening ($0.50^{\text{hop}}$) ensuring second-order shocks decay realistic without runaway amplification.

---

## Slide 5: Module B — Wholesale Portfolio Stress Testing
- **$500M Wholesale Book:** Real-world institutional composition:
  - Corporate Loans ($220M funded): Expected Credit Loss (ECL) adjustments.
  - Corporate Bonds ($200M market value): Modified duration spread shock approximations.
  - SOFR Interest Rate Swaps ($150M gross notional): Signed DV01 curve sensitivity.
  - Cash Reserves ($80M): Sovereign liquidity baseline.
- **Crisis Scenarios:** Credit Crunch (+150 bps spread, +2.5% PD), Rate Shock (+100 bps parallel curve shift), and Supply Chain Force Majeure.
- **Stress Results & Loss Waterfall:** Transparent attribution of portfolio P&L across counterparties and asset classes.

---

## Slide 6: Quantitative Evaluation & Measured Benchmarks
- *(Measured values to be recorded in Milestone M7 / M10)*
- **NLP Quality Targets vs Actuals:**
  - Sentiment Macro-F1 Target: $\ge 0.75$ [Recorded in M7]
  - Event Classification Macro-F1 Target: $\ge 0.70$ [Recorded in M7]
  - Entity Linking Precision Target: $\ge 0.90$ [Recorded in M7]
  - Impact Severity MAE Target: $\le 1.50$ [Recorded in M7]
- **Operational Latency:** CPU inference throughput (< 150ms per record on standard hardware).

---

## Slide 7: Live Terminal Demo & Production Feasibility
- **Risk Terminal UI:** High-contrast institutional dark-mode terminal with live replay feed, signal audit drawer, and portfolio stress matrix.
- **Production Integration:** How S&P Sentinel integrates with S&P Global Ratings workflows and CRISIL credit intelligence systems.
- **Summary & Q&A Readiness:** Clear explanation of quantitative formulas, design trade-offs, and compliance guarantees.
