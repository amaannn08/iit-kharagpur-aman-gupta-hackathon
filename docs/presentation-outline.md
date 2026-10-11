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

## Video walkthrough (4:42, unlisted YouTube: https://youtu.be/2oVdwJt_VmY)

Recorded from the running app on the committed data, with narration.

| Time | Segment |
|---|---|
| 0:00-0:22 | Title: problem, engine and the two modules |
| 0:22-0:52 | Architecture and data flow |
| 0:52-1:24 | Live replay of real Polygon 2023 news; counters and the action gate |
| 1:24-1:50 | Signal inspector: entity, evidence span, sentiment, event class, impact |
| 1:50-2:15 | NLP sandbox: a credit-default headline triggers a stress run |
| 2:15-2:51 | Module B: PS benchmark (equities -10%, rates +200 bp), waterfall, attribution |
| 2:51-3:16 | Historical scenarios (COVID-19 window) |
| 3:16-3:48 | Module A: weights over time and the reason for each move |
| 3:48-4:18 | Evaluation on real held-out data, and its limits |
| 4:18-4:42 | Dark mode and summary |
