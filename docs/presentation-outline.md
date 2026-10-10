# Presentation, demo and video outline

The deck itself is generated: `uv run python scripts/generate_presentation_pdf.py` -> `docs/presentation.pdf` (7 slides, numbers from `docs/metrics.json`).

| Slide | Topic (guidelines outline) | Content |
|---|---|---|
| 1 | Title | S&P Sentinel; Aman Gupta, IIT Kharagpur; scale of real data used |
| 2 | Problem & approach | Text -> structured signals; both modules; trust via real held-out evaluation; live capture |
| 3 | System design | `docs/architecture.png` |
| 4 | Implementation highlights | Linker, classifier, sentiment, market-calibrated impact, dedup/relevance, stress engine: what and why |
| 5 | Key results | Metrics vs baselines and targets; scenario P&L table; Module A back-test |
| 6 | Domain impact | Flight to quality measured; credit triangle; retail credit from real transactions; defensible impact score; auditability |
| 7 | Limitations & next steps | Tweets vs news domain, pending human labels, simplified valuation; next steps |

## Live demo (5 minutes)

1. **0:00-0:30** Slide 3: what flows where.
2. **0:30-1:30** Terminal, footer "Real news: Polygon 2023": play the replay; open a signal in the inspector (entity span, sentiment, event with gate evidence, impact method, block reasons).
3. **1:30-2:15** NLP Sandbox: paste a fresh headline (e.g. a bankruptcy or a rate cut) and show the signal and the automatic stress run.
4. **2:15-3:30** Wholesale Stress tab: "Silicon Valley Bank failure" and "PS example"; before/after by sleeve, the waterfall, reconciliation; point out that yields fall in credit stress.
5. **3:30-4:15** Index Rebalancer tab: weights over time and reasons; back-test result stated honestly.
6. **4:15-5:00** Evaluation tab: real held-out metrics and the impact-decile chart; close with limitations.

Fallback if the network is unavailable: everything above runs from committed data. If live capture is shown, start `scripts/live/record_live.py` before the demo and use "Live capture" + "Pull new live records".

## Video walkthrough (10 minutes, unlisted YouTube; link goes in README)

| Time | Segment |
|---|---|
| 0:00-0:30 | Problem and what the prototype does |
| 0:30-1:30 | Setup from the README Quickstart (clone, `uv sync`, build frontend, start API) |
| 1:30-4:30 | End-to-end: replay real news -> signals -> inspector; sandbox headline -> stress trigger; live capture append |
| 4:30-6:30 | Module B scenarios and dashboards; Module A weights over time |
| 6:30-8:00 | How the numbers are produced: `run_evaluation.py`, held-out data, baselines, leakage controls |
| 8:00-9:30 | Results and domain impact |
| 9:30-10:00 | Limitations and next steps |
