# Data Licensing, Authorship, and Provenance Notice

**Repository:** S&P Sentinel — Financial Text Risk Intelligence & Wholesale Portfolio Stress Platform  
**Author:** Aman Gupta (Indian Institute of Technology Kharagpur)  
**Governing Root License:** MIT License (see `LICENSE`)

---

## 1. Project-Authored Synthetic Datasets

The following datasets bundled in `data/` were authored directly by Aman Gupta specifically for the evaluation and benchmarking of S&P Sentinel:

- `data/news_demo.csv` (Curated synthetic financial news headlines and narrative paragraphs)
- `data/social_demo.csv` (Curated synthetic financial social media posts and trader commentary)
- `data/wholesale_positions.json` (Synthetic $500M institutional wholesale banking portfolio)
- `data/scenarios/credit_crunch.json` (Authored credit deterioration scenario)
- `data/scenarios/rate_shock.json` (Authored yield curve parallel shock scenario)
- `data/scenarios/supply_disruption.json` (Authored industrial force majeure scenario)
- `data/eval/holdout_seed.csv` (Curated gold-standard evaluation holdout seed)

### License Grant
These authored synthetic datasets are released under the terms of the project's **MIT License** (consistent with the root repository `LICENSE`). You are free to use, modify, distribute, and reproduce these datasets provided that the copyright and permission notice are preserved.

---

## 2. Project-Authored Evaluation Rubric

- `data/eval/annotation_rubric.md` (Standardized 9-class financial event taxonomy and 1–10 additive impact severity rubric)

### License Grant
The annotation rubric is authored by Aman Gupta and released under the **MIT License**.

---

## 3. Public Factual Reference Identifiers

- `data/entity_aliases.csv` (Reference entity universe mapping stock tickers to canonical corporate names, primary GICS sectors, aliases, and cashtags)

### Provenance & Factual Scope
This file contains factual public market reference identifiers (such as ticker symbols, official corporate registrations, and high-level industrial classifications). Factual data points and public company names are non-copyrightable facts of public record. The compilation, curation, and alias mappings are made available under the project's **MIT License**.

---

## 4. Synthetic Contagion Relationships & Banking Exposures

- `data/graph_edges.csv` (Directed customer-supplier and creditor transmission linkages)
- `data/wholesale_positions.json` (Counterparty facility allocations and notional amounts)

### Factual Distinction
The relationships and positions contained in these files are **entirely hypothetical and synthetic**. They do NOT reflect actual confidential lending facilities, non-public supplier contracts, or private counterparty exposures of S&P Global, CRISIL, or their commercial clients. They are engineered strictly as an offline computational testbed for second-order risk propagation and wholesale balance sheet stress testing.

---

## 5. Hackathon Integrity & Compliance Declaration

In strict compliance with **Hackathon Guidelines Section 8 (Confidentiality & Data Protection)** and **Section 9 (Intellectual Property & Licensing)**:
1. **Zero Client Data:** No confidential, proprietary, internal, or non-public data from S&P Global, CRISIL, or any corporate client was accessed, ingested, or included.
2. **Zero Proprietary Model Inversion:** No proprietary credit rating formulas, confidential risk algorithms, or private benchmark datasets were replicated.
3. **Explicit Synthetic Disclosure:** Every synthetic record is marked with `is_synthetic: true` and documented in `data/manifest.json`.
