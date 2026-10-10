# Evaluation

All reported metrics come from one script and one file:

```bash
uv run python scripts/run_evaluation.py               # all suites -> docs/metrics.json, docs/evaluation_report.md
uv run python scripts/run_evaluation.py --write-readme  # also refresh the README results table
```

| Suite | Data | What is measured |
|---|---|---|
| `public_real` | 4,117 + 2,388 held-out real labeled financial tweets (HF, MIT) | Event macro-F1 (model and runtime path with abstention + gates), precision when the classifier fires, sentiment macro-F1, keyword / lexicon / old-seed baselines on identical rows, confusion matrix |
| `entity_polygon` | 5,548 real Polygon articles; gold = article `tickers[]` within the S&P 500 universe | Precision and recall |
| `market_impact` | 2,617 real article-company events with next-day abnormal returns | Out-of-fold Spearman (5-fold, grouped by month) with bootstrap 95% CI, decile table, large-move rates; rubric comparison |
| `sec_8k` | Held-out 20% of real 8-K filings | Recall by class; share of routine filings sent to the credit/cyber stress path |
| `stress` | Module B scenarios | P&L by sleeve for five historical windows and the PS example; reconciliation |
| `module_a` | Back-test on real tweets and prices | Active return, tracking error, t-statistic, turnover |
| `perf` | 2,000 real articles | Records/s, p50/p95 latency, peak memory |
| `synthetic_regression` | 105 author-written rows | Regression check only (not a quality claim) |

Model cards (`models/*.card.json`) record training-data hashes, thresholds and the held-out metrics computed at training time. CI recomputes the suites that need only committed data, and tests gate the results on the problem-statement targets.

## Leakage controls

- Training, threshold selection and evaluation use disjoint data: the abstention threshold is chosen on a dev split of the training data; HF valid splits are never used for fitting.
- 8-K filings are split by accession number (identical split in every training script).
- Impact labels exclude reaction headlines and use only information available before the reaction day.
- The human-labeling sample excludes every row used for training, including weak-label headlines.

## Real-news holdout (AI-agent labels)

`data/eval/holdout_v2_news.csv` holds 120 stratified real rows (60 Polygon, 40 GDELT, 20 held-out 8-K). Its `gold_*` and `should_trigger` columns were written in one pass by an AI agent following `data/eval/annotation_rubric.md`; no person has reviewed them, and no annotator agreement is reported (`holdout_v2_news.provenance.json`). The `news_holdout` suite therefore measures agreement with an independent labeler, not with human ground truth.

To replace them: label the rows by hand with `uv run python scripts/eval/label_cli.py --annotator "<name>"`, set `label_source` to `human` in the provenance file, run `--freeze`, label a random subset again a day later into `holdout_v2_news.relabel.csv`, and the suite reports Cohen's kappa from that second pass. Never train on this file.
