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
- `data/eval/synthetic_regression.csv` (105 author-written regression rows; not a benchmark)
- `data/eval/synthetic_regression.csv` (105-row author-written regression suite)
- `data/eval/holdout_v2_news.csv` (120 real news rows; labels written by an AI agent, not human-reviewed; see `holdout_v2_news.provenance.json`)

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
- `data/universe/entities.csv` (S&P 500 constituents and historical changes)

### Provenance & Factual Scope
These files contain factual public market reference identifiers (such as ticker symbols, official corporate registrations, and high-level industrial classifications). Factual data points and public company names are non-copyrightable facts of public record. The compilation, curation, and alias mappings are made available under the project's **MIT License**.

---

## 4. Synthetic Contagion Relationships & Banking Exposures

- `data/graph_edges_demo.csv` (fictional supplier and creditor linkages for the synthetic demo). `data/graph_edges.csv` is derived from real prices (same-sector residual return correlations), see section 6
- `data/wholesale_positions.json`, `data/portfolio/wholesale_real.json` (Counterparty facility allocations and notional amounts)

### Factual Distinction
The relationships and positions contained in these files are **computational testbeds**. They do NOT reflect actual confidential lending facilities, non-public supplier contracts, or private counterparty exposures of S&P Global, CRISIL, or their commercial clients. Real issuer positions (`wholesale_real.json`) use public SEC XBRL debt statistics to construct representative balance-sheet facilities for stress simulation.

---

## 5. Hackathon Integrity & Compliance Declaration

In strict compliance with **Hackathon Guidelines Section 8 (Confidentiality & Data Protection)** and **Section 9 (Intellectual Property & Licensing)**:
1. **Zero Client Data:** No confidential, proprietary, internal, or non-public data from S&P Global, CRISIL, or any corporate client was accessed, ingested, or included.
2. **Zero Proprietary Model Inversion:** No proprietary credit rating formulas, confidential risk algorithms, or private benchmark datasets were replicated.
3. **Explicit Synthetic Disclosure:** Every synthetic record is marked with `is_synthetic: true` and documented in `data/manifest.json`.

---

## 6. Real Public Datasets & Reference Sources

Real public datasets are downloaded by `scripts/data/fetch_real.py` into the gitignored `data/raw/real/` cache. The repository commits samples, derived aggregates, or verified offline snapshots; `data/manifest.json` records the license, source URL, SHA-256 and row count for every tracked dataset. Third-party data preserves its originating license terms:

| Committed path | Source | License / Terms | Usage |
|---|---|---|---|
| `data/train/hf_fin_topic/`, `data/train/hf_fin_sentiment/` | zeroshot/twitter-financial-news-topic, -sentiment (Hugging Face) | MIT | NLP training and validation splits |
| `data/real/polygon_news/` | Kaggle rdolphin/financial-news-with-ticker-level-sentiment (Polygon.io news) | MIT | Entity linking and temporal pipeline holdout |
| `data/real/stock_tweets/` (5,000-row sample) | Kaggle thedevastator/tweet-sentiment-s-impact-on-stock-returns | CC0; tweet text subject to platform terms | Social sentiment and relevance verification |
| `data/train/phrasebank/` (600-row sample) | FinancialPhraseBank, Malo et al. (2014) | CC BY-NC-SA 3.0 | Sentiment calibration reference |
| `data/portfolio/credit_sleeve.json` (aggregates) | Kaggle computingvictor/transactions-fraud-datasets | Apache-2.0 | Retail credit card and fraud operational risk |
| `data/train/sec_8k/items.csv` | SEC EDGAR Form 8-K filings | U.S. public record | Event classification silver dataset |
| `data/real/gdelt/snapshot.csv`, `data/real/gdelt/svb_weekend.csv` | GDELT Project 2.0 Global Knowledge Graph (GKG) | GDELT open data | Replay feed and March 2023 SVB-weekend stress scenario |
| `data/universe/entities.csv` | Wikipedia list of S&P 500 companies; SEC `company_tickers.json` | CC BY-SA 4.0 / U.S. public domain | Constituent reference universe |
| `data/market/*.json\|csv` | Statistics derived from Yahoo Finance closes via yfinance | Derived statistics only | Beta, volatility, and stress calibration windows |
| **FRED / ICE BofA OAS Rating Series** | Federal Reserve Bank of St. Louis (FRED): BAMLC0A1CAAA, BAMLC0A2CAA, BAMLC0A3CA, BAMLC0A4CBBB, BAMLH0A1HYBB, BAMLH0A2HYB, BAMLH0A3HYC | Public domain / Open macro series (derived statistics only) | Rating-tiered spread calibration and validation anchors |
| **SEC EDGAR XBRL companyfacts** | U.S. Securities and Exchange Commission (SEC EDGAR API: `data.sec.gov/api/xbrl/companyfacts`) | U.S. public record (non-copyrightable public financial statements) | Extracting total debt, operating income, and interest expense for 22 real debt issuers across 11 GICS sectors |
| **S&P Global Ratings Default Study** | S&P Global Ratings, *Default, Transition, and Recovery: 2020 Annual Global Corporate Default And Rating Transition Study*, Table 3 (weighted long-term average, 1981-2020) | Seven cited statistics | Baseline one-year PD by rating (AAA 0.00% ... CCC/C 28.30%) |
| **yfinance closes (S&P 500)** | Yahoo Finance via yfinance | Derived statistics only | `data/graph_edges.csv`: residual return correlations, 2023-03-01 to 2024-02-29 |
