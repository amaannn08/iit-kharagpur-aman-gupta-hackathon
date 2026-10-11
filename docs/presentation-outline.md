# Presentation, demo and video outline

`docs/presentation.pdf` is the final 7-slide deck, designed in Canva with numbers taken from `docs/metrics.json`. `uv run python scripts/generate_presentation_pdf.py` writes a plain draft with the same numbers to `docs/presentation_draft.pdf` (not committed).

| Slide | Topic (guidelines outline) | Content |
|---|---|---|
| 1 | Title | S&P Sentinel; Aman Gupta, IIT Kharagpur; scale of real data used |
| 2 | Problem & approach | Text -> structured signals; both modules; trust via real held-out evaluation; live capture |
| 3 | System design | `docs/architecture.png` |
| 4 | Implementation highlights | Linker, classifier, sentiment, market-calibrated impact, dedup/relevance, stress engine: what and why |
| 5 | Key results | Metrics vs baselines and targets; scenario P&L table; Module A back-test |
| 6 | Domain impact | Flight to quality measured; credit triangle; FRED OAS validation; SVB-weekend replay; retail credit from real transactions; defensible impact score; auditability |
| 7 | Limitations & next steps | Tweets vs news domain; news holdout labeled by an AI agent (human labels to do); no automatic triggers on the Q4 holdout; valuation assumptions; next steps |

## Live demo (5 minutes)

1. **0:00-0:30** System Overview: architecture diagram, data contracts, and 100% offline localhost runtime compliance.
2. **0:30-1:30** Real News Replay (Polygon 2023): play the replay stream, inspect signals in the live feed, open the Signal Inspector panel to demonstrate entity linking, gate evidence highlights, sentiment probabilities, and impact score.
3. **1:30-2:15** Historical SVB-Weekend Replay (GDELT): select "Real replay: SVB weekend bank run 2023" from the Replay Control presets. Stream real March 2023 headlines and show entity resolution to SIVB/FRC/SBNY. Be upfront: most headlines are classified OTHER (the classifier was trained on tweets), and SIVB is not held and has no price-based contagion edges, so the replay shows NO_EXPOSURE rather than a loss. Then run the "Silicon Valley Bank failure" historical scenario for the market-wide effect.
4. **2:15-3:15** NLP Sandbox: test manual text analysis with custom corporate distress or rate cut headlines. Demonstrate real-time model inference, evidence gate checks, and one-click stress triggering.
5. **3:15-4:00** Wholesale Stress Testing: inspect calibrated historical scenarios (COVID-19, Fed Jun-2022, Fed Pivot 2023, Russia-Ukraine, SVB 2023) and the PS Benchmark card (-10% equities, +200 bp rates). Review sleeve P&L, waterfall charts, per-position loss attribution, and mathematical reconciliation.
6. **4:00-4:35** Index Rebalancer (Module A): review sentiment-driven weight tilts across 20 S&P names, turnover at 0/5/10 bps costs, break-even cost analysis, and block bootstrap confidence intervals.
7. **4:35-5:00** Evaluation & Governance: review binary release gates, eligible-signal lift on the Q4 holdout (and zero automatic triggers), AI-labeled news holdout (120 rows, MAE 1.52), and cryptographic manifest audit.

Fallback if the network is unavailable: everything above runs strictly from committed local datasets.

## Video walkthrough (10 minutes, unlisted YouTube; link in README)

| Time | Segment |
|---|---|
| 0:00-0:30 | Problem statement and system architecture overview |
| 0:30-1:30 | Setup verification: `make setup`, `make test`, `verify_hygiene.py`, and running `scripts/dev/demo.sh` |
| 1:30-3:30 | End-to-end signal pipeline: Polygon 2023 news replay and SVB-weekend GDELT replay -> signal inspection -> deduplication |
| 3:30-5:00 | NLP Sandbox and real-time stress shock triggering |
| 5:00-7:00 | Module B Wholesale Stress Testing: real issuer book (SEC XBRL), rating-tiered spreads, credit triangle, and loss attribution |
| 7:00-8:30 | Module A Index Rebalancer: backtest results, costs, and turnover analysis |
| 8:30-9:30 | Evaluation suite: temporal holdouts, the AI-labeled news holdout and its limits, FRED OAS validation, and performance benchmarks |
| 9:30-10:00 | Assumptions, limitations, and future work |
