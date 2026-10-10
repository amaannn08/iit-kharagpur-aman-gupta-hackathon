# S&P Sentinel - S&P Global & Crisil Campus Hackathon

**Candidate Name:** Aman Gupta
**College Email ID:** amangupta08@kgpian.iitkgp.ac.in
**College / Campus:** Indian Institute of Technology Kharagpur
**Demo Video Link:** TODO: unlisted YouTube link (to be recorded)
**Slide Deck Link (if hosted externally):** in repository: [docs/presentation.pdf](docs/presentation.pdf)

## 1. Project Overview / Problem Statement & Approach

Market-moving events (defaults, rate decisions, sanctions, cyber incidents, earnings shocks) appear first as unstructured text in news and social media. The problem statement asks for an AI/NLP risk engine that ingests such text from at least two sources in real time and turns it into structured signals (sentiment score, event class, impact score) that downstream applications can consume, plus at least one downstream module.

S&P Sentinel is that engine, with **both** downstream modules. For every company a text mentions, the engine emits a signal with sentiment (-1..1), an event class from the PS taxonomy (credit, macro, geopolitical, M&A, product, plus regulatory, earnings, supply chain and cyber), a 1-10 impact score calibrated against real market reactions, character-level evidence spans, and an action decision with reasons. Signals are served by a REST API, a server-sent event stream and an append-only `data/signals.jsonl` file. **Module A** re-weights a 20-name mock S&P 100 index by sentiment and charts the weights over time. **Module B** runs event-triggered stress tests on a $610M funded book (synthetic wholesale loans/bonds/swaps, a retail/SME credit sleeve built from real card-transaction data, and an equity sleeve with real betas) using shocks measured from five real crisis windows.

The approach is evidence-first: every model is trained and evaluated on real public data with held-out splits, and every number in this README, the deck and the dashboard is produced by `scripts/run_evaluation.py` into `docs/metrics.json`. Real-time ingestion uses a separate recorder for GDELT and SEC EDGAR; the application itself never calls external services.

## 2. Architecture & Tech Stack

![Architecture](docs/architecture.png)

**Data flow:** real sources (GDELT 15-minute GKG files and SEC 8-K filings via the live recorder; Polygon news, stock tweets and the other datasets for replay) -> typed `InputRecord`s -> replay controller (logical clock, exact + MinHash-LSH near-duplicate suppression, social spam/relevance filter) -> NLP engine (entity linking, sentiment, event classification with abstention and evidence gates, market-calibrated impact) -> one `RiskSignal` per company -> SQLite audit store, SSE stream, `signals.jsonl` -> Module A rebalancer and Module B stress engine -> React terminal.

| Layer | Technology | Why |
|---|---|---|
| API / runtime | Python 3.11, FastAPI, Pydantic v2, SQLite (SQLAlchemy), SSE | Typed contracts, local audit trail, no external runtime dependencies |
| Entity linking | Rule-based linker over the S&P 500 universe (SEC CIKs) | Exact, auditable spans; role guards for rating agencies, brokers and fund sponsors |
| Event classification | scikit-learn TF-IDF + isotonic-calibrated logistic regression (`models/event_v2.joblib`, 5.2 MB) | CPU-fast and explainable; calibrated abstention threshold chosen on a dev split |
| Sentiment | TF-IDF word + char n-grams + logistic regression (`models/sentiment_v2.joblib`); optional local FinBERT | Outperformed off-the-shelf FinBERT on independent financial tweets in our comparison |
| Impact | Gradient-boosted regression of next-day abnormal return (`models/impact_v2.joblib`) + additive rubric for explanation | Validated against what markets actually did |
| Dedup | `datasketch` MinHash-LSH with a lead-sentence index and a 24 h window | Near-linear; catches headline re-posts of long articles |
| Module B | Loan ECL, bond duration, signed swap DV01, equity beta; directed exposure graph (`data/graph_edges.csv`) with hop decay | Shocks from measured windows; funded value and derivative MTM reported separately |
| Frontend | React 18, TypeScript, Vite, Recharts, Tailwind | Live feed, signal inspector, Module A/B dashboards, metrics panel |
| Data tooling | kagglehub, huggingface_hub, yfinance (build-time only, `data` dependency group) | Anonymous downloads; no keys |

## 3. Dataset Used

All real datasets are public; synthetic data is labeled `is_synthetic: true` in `data/manifest.json` and every file is SHA-256 checksummed there (`python scripts/verify_hygiene.py`). Large raw downloads stay in the gitignored `data/raw/real/` cache and are reproduced with `scripts/data/fetch_real.py`; the repository commits samples and derived aggregates, each folder with a LICENSE file.

| Dataset | Use | Committed | License |
|---|---|---|---|
| [zeroshot/twitter-financial-news-topic](https://huggingface.co/datasets/zeroshot/twitter-financial-news-topic) (21,107 labeled tweets) | Train / evaluate event classifier | `data/train/hf_fin_topic/` (full) | MIT |
| [zeroshot/twitter-financial-news-sentiment](https://huggingface.co/datasets/zeroshot/twitter-financial-news-sentiment) (11,931) | Train / evaluate sentiment | `data/train/hf_fin_sentiment/` (full) | MIT |
| [Polygon news with ticker-level sentiment](https://www.kaggle.com/datasets/rdolphin/financial-news-with-ticker-level-sentiment) (5,548 articles, 2023) | Historical news replay, entity evaluation, impact labels | `data/real/polygon_news/` (full) | MIT |
| [Tweet sentiment's impact on stock returns](https://www.kaggle.com/datasets/thedevastator/tweet-sentiment-s-impact-on-stock-returns) (862,231 tweets, 2017-18) | Social replay, Module A back-test | `data/real/stock_tweets/` (5,000 sample) | CC0 (tweet text subject to X terms) |
| [FinancialPhraseBank](https://www.kaggle.com/datasets/ankurzing/sentiment-analysis-for-financial-news) (4,846) | Sentiment training augmentation only | `data/train/phrasebank/` (600 sample) | CC BY-NC-SA 3.0 (not relicensed) |
| [Financial transactions dataset](https://www.kaggle.com/datasets/computingvictor/transactions-fraud-datasets) (13.3M transactions, 2,000 users) | Module B retail/SME credit sleeve, CYBER fraud rates | `data/portfolio/credit_sleeve.json` (aggregates only) | Apache-2.0 |
| SEC EDGAR 8-K filings (EDGAR full-text search) | Labeled CYBER/CREDIT text and routine negatives; live feed | `data/train/sec_8k/items.csv` (704 statements) | US public record |
| GDELT 2.0 GKG | Live news feed; 2-hour snapshot for offline replay | `data/real/gdelt/snapshot.csv` (2,690 headlines) | GDELT open data |
| yfinance closes (S&P 500, SPY, IEF, LQD, HYG, ^TNX, ^VIX) | Impact labels, shock calibration, equity betas | Derived statistics only (`data/market/`) | Yahoo terms (raw prices not redistributed) |
| Synthetic demo feeds, wholesale book, contagion graph, scenarios | Deterministic demo scenario | `data/*.csv`, `data/wholesale_positions.json` | MIT, `is_synthetic: true` |

**Not used:** Salad Money open-banking data (GeoDS "Secure": UK trusted research environment only); GDELT DOC API (rate-limited; the raw 15-minute files are used instead).

**Assumptions** (details in [docs/assumptions.md](docs/assumptions.md)): retail EAD = total debt + 30% CCF on card limits, PD by credit-score band, LGD 80%, sleeve scaled to $50M; HY spread change from HYG vs IEF with duration 3.7; PD shock via the credit triangle (spread ~ PD x LGD, LGD 60%); impact label = |abnormal next-day return| / 30-day volatility; wholesale positions and equity sizes are synthetic.

## 4. Quickstart & Installation

Runtime: Python 3.11 (uv) and Node 20+ on Linux (tested on Linux 7.2, Node 26).

```bash
git clone https://github.com/amaannn08/iit-kharagpur-aman-gupta-hackathon.git
cd iit-kharagpur-aman-gupta-hackathon
uv sync                                   # or: pip install -r requirements.txt
(cd frontend && npm ci && npm run build)  # builds the terminal served by the API
uv run uvicorn sentinel.api.app:app --host 127.0.0.1 --port 8000
# open http://127.0.0.1:8000 and pick a replay source in the footer
```

The app runs from the committed data and models alone. Optional steps:

```bash
uv run pytest && (cd frontend && npm test)                 # backend and frontend tests
python scripts/verify_hygiene.py                            # manifest hashes, secrets, offline runtime
uv run python scripts/run_evaluation.py --write-readme      # recompute docs/metrics.json and the table below
uv run --group data python scripts/data/fetch_real.py       # re-download every real dataset (~1.7 GB, no keys)
uv run python scripts/data/convert_real.py                  # rebuild committed samples from the raw cache
uv run python scripts/models/train_event.py                 # retrain (also train_sentiment.py, train_impact.py)
uv run python scripts/live/record_live.py --interval-min 15 # live GDELT + SEC 8-K capture (separate process)
```

To demo real time: run the recorder, choose "Live capture" in the terminal footer, and press "Pull new live records" as new files arrive.

## 5. Key Results & Domain Impact

Measured on real held-out data (generated by `scripts/run_evaluation.py`; raw values in [docs/metrics.json](docs/metrics.json), full report in [docs/evaluation_report.md](docs/evaluation_report.md)):

<!-- METRICS:START -->
| Metric | Measured | Target | Comparison |
|---|---|---|---|
| Event macro-F1, 4,117 held-out real financial tweets | 0.846 | >= 0.7 | keyword 0.286 / old seed model 0.060 |
| Event, runtime path (abstention + evidence gates), same rows | F1 0.585, precision 0.932 when it fires | precision first | fires on 25% of rows (precision/recall trade-off) |
| Sentiment macro-F1, 2,388 held-out real financial tweets | 0.778 | >= 0.75 | lexicon 0.469 |
| Entity linking, 2,518 real news articles | P 0.971 / R 0.588 | P >= 0.9 | old alias table: entity found in 5% |
| Impact vs next-day abnormal return, 2,617 real events | Spearman 0.151 [0.113, 0.190] | > 0 | rubric 0.098 |
| Latency per record (p95), CPU | 0.015 s | <= 2.0 s | 96 records/s |
<!-- METRICS:END -->

**Module B (stress testing).** Historical scenarios replay measured market moves on the $610M funded book; every run reconciles position P&L to the total. Example results: COVID-19 window and SVB failure (see `stress` in `docs/metrics.json`), and the PS example shock (equities -10%, rates +200 bp). Event-triggered runs scale the calibrated shocks by impact/8; a trigger that touches no position is reported as `NO_EXPOSURE`.

**Module A (index rebalancing).** Positive sentiment raises a name's weight and negative lowers it, within 20% name and 40% sector caps; the terminal charts weights over time with a reason for every move. A back-test on real 2017-18 tweets and prices shows a small, statistically insignificant active return (`docs/module_a_backtest.json`): the module demonstrates sentiment-driven reweighting, not alpha.

**Why it matters.** The engine turns unstructured text into auditable signals whose impact score is validated against real market reactions; the stress engine encodes measured crisis behaviour (in the SVB, COVID and Russia windows Treasury yields fell while spreads widened) instead of assuming every shock lifts rates, and builds retail credit exposure from real transaction data. Evidence spans, model versions, block reasons and reconciliation checks make every decision reviewable.

**Limitations.** Headline NLP metrics are on financial tweets; news-domain agreement with LLM silver labels is lower. Severity MAE against human labels is pending: a 300-row real-news set is sampled in `data/eval/holdout_v2_news.todo.csv` for hand labeling. Valuation is simplified (single-period ECL, duration without convexity, linear DV01). The wholesale book and equity position sizes are synthetic.

## Repository layout

```
src/sentinel/     contracts, ingestion, nlp (entities, events, sentiment, severity, impact model,
                  relevance), replay (clock, controller, dedup), stress, rebalance, api, storage
frontend/         React terminal (feed, inspector, Module A/B dashboards, metrics)
models/           committed model artifacts + cards (training data hashes, metrics, thresholds)
scripts/          data (fetch, convert, universe, sleeves, shock calibration), models (train_*),
                  live recorder, evaluation, back-test, diagram and deck generators
data/             real samples (real/, train/), universe, portfolio, market-derived labels,
                  scenarios, synthetic demo feeds, manifest.json
docs/             presentation.pdf, architecture.png, metrics.json, evaluation_report.md, assumptions
tests/            backend tests (pytest); frontend tests live in frontend/src
```

License: MIT ([LICENSE](LICENSE)). Third-party data keeps its own license (see each data folder's LICENSE and [data/DATA_LICENSE.md](data/DATA_LICENSE.md)).
