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

---

## 6. Real Public Datasets

Real public datasets are downloaded by `scripts/data/fetch_real.py` into the gitignored
`data/raw/real/` cache. The repository commits samples or derived aggregates only; each folder
carries a LICENSE file with attribution, and `data/manifest.json` records license, source URL,
SHA-256 and row count for every file. Third-party data keeps its own license and is not covered
by the project's MIT license.

| Committed path | Source | License |
|---|---|---|
| `data/train/hf_fin_topic/`, `data/train/hf_fin_sentiment/` | zeroshot/twitter-financial-news-topic, -sentiment (Hugging Face) | MIT |
| `data/real/polygon_news/` | Kaggle rdolphin/financial-news-with-ticker-level-sentiment (Polygon.io news) | MIT |
| `data/real/stock_tweets/` (5,000-row sample) | Kaggle thedevastator/tweet-sentiment-s-impact-on-stock-returns | CC0; tweet text subject to X terms |
| `data/train/phrasebank/` (600-row sample) | FinancialPhraseBank, Malo et al. (2014) | CC BY-NC-SA 3.0 (bundled License.txt; Kaggle lists 4.0) |
| `data/portfolio/credit_sleeve.json` (aggregates) | Kaggle computingvictor/transactions-fraud-datasets | Apache-2.0 |
| `data/train/sec_8k/items.csv` | SEC EDGAR Form 8-K filings | US public record |
| `data/real/gdelt/snapshot.csv` | GDELT Project 2.0 GKG (cite "The GDELT Project") | GDELT open data |
| `data/universe/entities.csv` | Wikipedia list of S&P 500 companies; SEC company_tickers.json | CC BY-SA 4.0 (constituent list); US public domain (SEC) |
| `data/market/*.json|csv` | Statistics derived from Yahoo Finance closes via yfinance | Derived values only; raw prices not redistributed |

Earlier revisions contained hand-written fixture rows under `data/external/` and an 8-user
`data/portfolio/credit_sleeve.*` that were labeled as Kaggle data; they were not real records and
were removed.
