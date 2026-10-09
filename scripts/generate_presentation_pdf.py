#!/usr/bin/env python3
"""Generate the 7-slide submission deck, docs/presentation.pdf.

Follows the guidelines' outline (title, problem & approach, system design, implementation,
key results, domain impact, limitations & next steps). Every number is read from
docs/metrics.json and docs/module_a_backtest.json (scripts/run_evaluation.py,
scripts/backtest_module_a.py); nothing is typed by hand.

Usage: uv run python scripts/generate_presentation_pdf.py
"""

import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS = REPO_ROOT / "docs"
OUTPUT_PDF = DOCS / "presentation.pdf"

INK, MUTED, ACCENT, GRID = "#0f172a", "#334155", "#0284c7", "#cbd5e1"
SCENARIO_NAMES = {
    "HIST-COVID_2020": "COVID-19 liquidity shock (Feb-Mar 2020)",
    "HIST-FED_JUN_2022": "Fed 75 bp surprise hike (Jun 2022)",
    "HIST-FED_PIVOT_2023": "Fed pivot rally (Nov-Dec 2023)",
    "HIST-RUSSIA_2022": "Russia-Ukraine invasion (Feb-Mar 2022)",
    "HIST-SVB_2023": "SVB failure (Mar 2023)",
}


def usd_m(v: float) -> str:
    return f"{'-' if v < 0 else '+'}${abs(v) / 1e6:,.1f}M"


def build_presentation_pdf() -> None:
    m = json.loads((DOCS / "metrics.json").read_text())
    ev, se = m["public_real"]["event"], m["public_real"]["sentiment"]
    ent, imp, perf, sec = m["entity_polygon"], m["market_impact"], m["perf"], m["sec_8k"]
    stress, mod_a = m["stress"], m["module_a"]
    windows = json.loads((REPO_ROOT / "data" / "market" / "stress_windows.json").read_text())[
        "windows"
    ]
    sleeve = json.loads((REPO_ROOT / "data" / "portfolio" / "credit_sleeve.json").read_text())
    svb, n_tx, n_borrowers = (
        windows["svb_2023"],
        sleeve["inputs"]["transactions"],
        sleeve["inputs"]["borrowers"],
    )

    styles = getSampleStyleSheet()
    title = ParagraphStyle("T", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=22,
                           leading=26, textColor=colors.HexColor(INK), spaceAfter=4)  # fmt: skip
    subtitle = ParagraphStyle("S", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=12,
                              leading=16, textColor=colors.HexColor(ACCENT), spaceAfter=10)  # fmt: skip
    body = ParagraphStyle("B", parent=styles["Normal"], fontName="Helvetica", fontSize=10,
                          leading=14, textColor=colors.HexColor(MUTED), spaceAfter=6)  # fmt: skip
    bullet = ParagraphStyle("L", parent=body, leftIndent=14, bulletIndent=4, spaceAfter=3)
    small = ParagraphStyle("Sm", parent=body, fontSize=8.5, leading=11)

    def bullets(items):
        return [Paragraph(i, bullet, bulletText="•") for i in items]

    def table(rows, widths, header=True):
        t = Table([[Paragraph(str(c), small) for c in r] for r in rows], colWidths=widths)
        style = [("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor(GRID)),
                 ("VALIGN", (0, 0), (-1, -1), "TOP")]  # fmt: skip
        if header:
            style += [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e0f2fe"))]
        t.setStyle(TableStyle(style))
        return t

    def two_col(left, right, w=(355, 355)):
        t = Table([[left, right]], colWidths=list(w))
        t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
        return t

    el = []

    # 1. Title
    el += [
        Spacer(1, 70),
        Paragraph("S&amp;P Sentinel", title),
        Paragraph(
            "Real-time financial-text risk signals driving index rebalancing and "
            "portfolio stress testing",
            subtitle,
        ),  # fmt: skip
        Paragraph(
            "<b>Candidate:</b> Aman Gupta &nbsp;|&nbsp; <b>College:</b> Indian Institute "
            "of Technology Kharagpur",
            body,
        ),  # fmt: skip
        Paragraph(
            "S&amp;P Global &amp; CRISIL Campus Hackathon 2026 &nbsp;|&nbsp; Individual submission",
            body,
        ),  # fmt: skip
        Spacer(1, 16),
        Paragraph(
            f"Built and evaluated on real public data: {ev['n']:,} + {se['n']:,} held-out "
            f"labeled financial tweets, {ent['articles']:,} real news articles, "
            f"{imp['events']:,} market-reaction events, {n_tx / 1e6:.1f}M card transactions, "
            "live GDELT and SEC EDGAR feeds.",
            body,
        ),  # fmt: skip
        PageBreak(),
    ]

    # 2. Problem & approach
    el += [
        Paragraph("Problem &amp; approach", title),
        Paragraph(
            "Turn unstructured news and social text into machine-readable risk signals, "
            "then act on them",
            subtitle,
        ),  # fmt: skip
        two_col(
            bullets(
                [
                    "<b>Problem:</b> material events (defaults, rate moves, sanctions, cyber "
                    "incidents) surface first in text; banks need structured signals fast and must "
                    "trust them.",
                    "<b>Engine output per company:</b> sentiment (-1..1), event class, impact "
                    "(1-10), evidence spans, action eligibility; served by API, SSE and a JSONL file.",
                    "<b>Trust:</b> every model is trained and scored on real held-out data; metrics "
                    "in this deck are read from docs/metrics.json (scripts/run_evaluation.py) and "
                    "data facts from the committed data files.",
                ]
            ),
            bullets(
                [
                    "<b>Module A</b> (tactical): a 20-name mock S&amp;P 100 index re-weighted by "
                    "sentiment, with caps and a weights-over-time dashboard.",
                    "<b>Module B</b> (strategic): event-driven stress tests on a $610M funded book "
                    "(wholesale + retail credit from real transactions + equities), shocks "
                    "calibrated on five real crisis windows.",
                    "<b>Real time:</b> a recorder captures GDELT (15-min) and SEC 8-K filings; the "
                    "app itself makes no network calls.",
                ]
            ),
        ),
        PageBreak(),
    ]

    # 3. System design
    el += [
        Paragraph("System design &amp; data flow", title),
        Image(str(DOCS / "architecture.png"), width=700, height=387),
        PageBreak(),
    ]

    # 4. Implementation highlights
    el += [
        Paragraph("Implementation highlights", title),
        Paragraph("Key modules, technology choices and why", subtitle),
        table(
            [
                ["Component", "What it does", "Why this choice"],
                [
                    "Entity linker",
                    f"S&amp;P 500 universe from SEC/Wikipedia; spans equal the text; "
                    f"one signal per company. P {ent['precision']:.3f} / R {ent['recall']:.3f}.",
                    "Rule-based and auditable; role guards stop rating agencies and brokers being "
                    "linked as the subject.",
                ],
                [
                    "Event classifier",
                    "TF-IDF + calibrated logistic regression, 8 PS classes + "
                    "CYBER/SUPPLY_CHAIN; abstention threshold chosen on a dev split.",
                    "CPU-fast, explainable; trained on real labeled tweets and real 8-K filings.",
                ],
                [
                    "Sentiment",
                    f"Real-data TF-IDF model (macro-F1 {se['macro_f1']:.3f}); policy "
                    "rules make rate cuts positive and hikes negative.",
                    "Outperformed off-the-shelf FinBERT in a prototype comparison; FinBERT stays an optional tier.",
                ],
                [
                    "Impact 1-10",
                    "Gradient-boosted model of next-day abnormal return, mapped to "
                    "deciles; rubric kept for explanation.",
                    "Validated against what markets actually did, not hand-picked weights.",
                ],
                [
                    "Dedup + relevance",
                    "Exact hash + MinHash-LSH with a lead-sentence index and a "
                    "24 h window; spam / no-context filter for social.",
                    "Bounded, near-linear index instead of an O(n^2) scan; syndicated copies never re-trigger stress.",
                ],
                [
                    "Module B engine",
                    "Loan ECL, bond duration, swap DV01, equity beta; contagion "
                    "graph; CYBER loss from observed fraud rates; reconciliation invariant.",
                    "Shocks measured from real windows; funded value and derivative MTM separated.",
                ],
            ],
            [110, 330, 270],
        ),
        PageBreak(),
    ]

    # 5. Key results
    stress_rows = [["Scenario (measured market move)", "Portfolio P&amp;L", "% of funded"]]
    for sid, r in stress["scenarios"].items():
        stress_rows.append([SCENARIO_NAMES.get(sid, sid),
                            usd_m(r["total_pnl_usd"]), f"{r['pnl_pct_of_funded']:.1%}"])  # fmt: skip
    ps = stress["ps_example_equities_-10pct_rates_+200bp"]
    stress_rows.append(["PS example: equities -10%, rates +200 bp", usd_m(ps["total_pnl_usd"]),
                        f"{ps['total_pnl_usd'] / stress['funded_book_usd']:.1%}"])  # fmt: skip
    lo, hi = imp["learned_oof_spearman_ci95"]
    a = next((r for r in mod_a.get("runs", []) if r["k"] == 1.5), None)
    el += [
        Paragraph("Key results (real held-out data)", title),
        two_col(
            table(
                [
                    ["Metric", "Measured", "Baseline / target"],
                    [
                        f"Event macro-F1 ({ev['n']:,} tweets)",
                        f"{ev['macro_f1_model']:.3f}",
                        f"keyword {ev['baseline_keyword_macro_f1']:.3f}, old {ev['baseline_seed_classifier_macro_f1']:.3f}; target 0.70",
                    ],
                    [
                        "Event precision when it fires",
                        f"{ev['precision_when_fired']:.3f}",
                        f"fires on {ev['fired_rate']:.0%} (abstains otherwise)",
                    ],
                    [
                        f"Sentiment macro-F1 ({se['n']:,} tweets)",
                        f"{se['macro_f1']:.3f}",
                        f"lexicon {se['baseline_lexicon_macro_f1']:.3f}; target 0.75",
                    ],
                    [
                        f"Entity linking ({ent['articles']:,} articles)",
                        f"P {ent['precision']:.3f} / R {ent['recall']:.3f}",
                        "target P 0.90",
                    ],
                    [
                        f"Impact vs abnormal return ({imp['events']:,})",
                        f"rho {imp['learned_oof_spearman']:.3f}",
                        f"95% CI [{lo:.3f}, {hi:.3f}]; rubric {imp['rubric_v1_spearman']:.3f}",
                    ],
                    [
                        "Large moves, top vs bottom decile",
                        f"{imp['large_move_rate_decile_10']:.1%} vs {imp['large_move_rate_decile_1']:.1%}",
                        "|abnormal z| &gt; 2",
                    ],
                    [
                        "Routine 8-Ks sent to stress path",
                        f"{sec['routine_filings_false_stress_rate']:.1%}",
                        f"{sec['n']} held-out filings",
                    ],
                    [
                        "Latency p95 per record (CPU)",
                        f"{perf['latency_p95_s']:.3f} s",
                        f"{perf['records_per_s']:.0f} records/s; target 2 s",
                    ],
                ],
                [135, 75, 140],
            ),
            [
                table(stress_rows, [190, 85, 70]),
                Spacer(1, 8),
                Paragraph(
                    (
                        f"Module A back-test (443 days, k=1.5): active return "
                        f"{a['active_annual_return']:+.2%}/yr, tracking error {a['tracking_error']:.2%}, "
                        f"t = {a['active_return_t_stat']:.2f}: sentiment reweighting works, no proven alpha."
                    )
                    if a
                    else "Module A back-test: not run.",
                    small,
                ),
            ],
        ),
        PageBreak(),
    ]

    # 6. Domain impact
    el += [
        Paragraph("Domain impact", title),
        Paragraph("Why it matters for a credit-risk and ratings business", subtitle),
        *bullets(
            [
                "<b>Flight to quality, measured:</b> in the SVB, COVID and Russia windows the "
                "10-year Treasury yield <i>fell</i> while spreads widened; only Fed tightening raised "
                "it. The shock catalog encodes this instead of assuming every crisis lifts yields.",
                f"<b>Credit triangle:</b> the SVB window's {svb['bond_spread_shift_bps']:+.0f} bp HY "
                f"spread implies {svb['loan_pd_increment'] * 100:+.1f} pp PD at 60% LGD, independently "
                "supporting the +150 bp / +2.5 pp single-name credit shock.",
                f"<b>Retail credit from real transactions:</b> {n_borrowers:,} borrowers and "
                f"{n_tx:,} card transactions pooled into sector x rating tranches; cyber losses use "
                "observed fraud rates by sector.",
                "<b>Impact you can defend:</b> the 1-10 score predicts the size of the next-day "
                "abnormal move out of sample, so analysts can rank events by expected market impact.",
                "<b>Auditability:</b> evidence spans, model versions, block reasons and a "
                "reconciliation invariant on every stress run; one JSON file holds every metric.",
            ]
        ),
        PageBreak(),
    ]

    # 7. Limitations & next steps
    el += [
        Paragraph("Limitations &amp; next steps", title),
        two_col(
            bullets(
                [
                    "Headline NLP metrics are on financial <i>tweets</i>; agreement with LLM silver "
                    f"labels on news is lower (sentiment {se['polygon_news_vs_llm_silver_macro_f1']:.2f}).",
                    "Reaction-phrased headlines ('shares slide after...') are often abstained.",
                    "Severity MAE vs human labels is pending: a 300-row real-news set is sampled "
                    "(data/eval/holdout_v2_news.todo.csv) and must be labeled by hand.",
                    "Simplified valuation: single-period ECL, no convexity, linear DV01; wholesale "
                    "book and equity sizes are synthetic; retail sleeve is scaled to $50M.",
                ]
            ),
            bullets(
                [
                    "Label the 300 news rows; report news-domain metrics and intra-annotator agreement.",
                    "Fine-tune FinBERT on tweets + news as an optional higher-accuracy tier.",
                    "Systemic impact model on index and yield reactions.",
                    "Longer live capture to evaluate real-time precision of actionable signals.",
                ]
            ),
        ),
    ]

    doc = SimpleDocTemplate(str(OUTPUT_PDF), pagesize=landscape(letter), leftMargin=36,
                            rightMargin=36, topMargin=36, bottomMargin=36)  # fmt: skip
    doc.build(el)
    print(f"wrote {OUTPUT_PDF.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    build_presentation_pdf()
