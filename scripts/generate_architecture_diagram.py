#!/usr/bin/env python3
"""Generate high-resolution system architecture diagram for S&P Sentinel.

Outputs docs/architecture.png. Metric values shown on the diagram are read from
docs/metrics.json (scripts/run_evaluation.py), never typed by hand.
"""

import json
from pathlib import Path

import matplotlib.patches as patches
import matplotlib.pyplot as plt

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PNG = REPO_ROOT / "docs" / "architecture.png"
METRICS = REPO_ROOT / "docs" / "metrics.json"


def create_architecture_diagram() -> None:
    # Set high DPI and dark theme canvas (1920x1080 proportion)
    fig, ax = plt.subplots(figsize=(18, 10), dpi=300)
    fig.patch.set_facecolor("#0b0f19")
    ax.set_facecolor("#0b0f19")

    # Coordinate boundaries [0, 100] on X and Y
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    # Header / Title Bar
    title_box = patches.FancyBboxPatch(
        (3, 91), 94, 7, boxstyle="round,pad=0.3", fc="#111827", ec="#38bdf8", lw=1.5
    )
    ax.add_patch(title_box)
    ax.text(
        5,
        95.5,
        "S&P SENTINEL — SYSTEM ARCHITECTURE & DATA FLOW",
        fontsize=16,
        fontweight="bold",
        color="#f8fafc",
        fontfamily="sans-serif",
    )
    ax.text(
        5,
        92.5,
        "Real-time financial-text risk signals driving index rebalancing and portfolio stress tests | IIT Kharagpur",
        fontsize=10,
        color="#94a3b8",
        fontfamily="sans-serif",
    )
    ax.text(
        80,
        94,
        "OFFLINE APP RUNTIME\nLIVE FEEDS VIA RECORDER",
        fontsize=9,
        fontweight="bold",
        color="#10b981",
        ha="center",
        va="center",
    )

    # Helper function for drawing module cards
    def draw_card(
        x,
        y,
        w,
        h,
        title,
        subtitle,
        items,
        border_color="#334155",
        bg_color="#131b2e",
        header_color="#38bdf8",
    ):
        # matplotlib renders text between two "$" as math: escape currency symbols
        title, subtitle = title.replace("$", r"\$"), (subtitle or "").replace("$", r"\$")
        items = [i.replace("$", r"\$") for i in items]
        box = patches.FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0.5", fc=bg_color, ec=border_color, lw=1.5
        )
        ax.add_patch(box)
        # Header banner
        header_strip = patches.Rectangle((x, y + h - 4.5), w, 4.5, fc="#1e293b", ec="none")
        ax.add_patch(header_strip)
        ax.text(
            x + 1.5,
            y + h - 2.8,
            title,
            fontsize=11,
            fontweight="bold",
            color=header_color,
            fontfamily="sans-serif",
        )
        if subtitle:
            ax.text(
                x + 1.5, y + h - 4.0, subtitle, fontsize=8, color="#94a3b8", fontfamily="sans-serif"
            )

        # Content list items
        curr_y = y + h - 7.5
        for item in items:
            ax.text(
                x + 2, curr_y, f"• {item}", fontsize=8.5, color="#e2e8f0", fontfamily="sans-serif"
            )
            curr_y -= 3.2

    m = json.loads(METRICS.read_text()) if METRICS.exists() else {}
    ev = m.get("public_real", {}).get("event", {})
    se = m.get("public_real", {}).get("sentiment", {})
    ent = m.get("entity_polygon", {})
    imp = m.get("market_impact", {})
    perf = m.get("perf", {})
    fmt = lambda v, d=3: f"{v:.{d}f}" if isinstance(v, (int, float)) else "n/a"  # noqa: E731

    # Column 1: real data sources
    draw_card(
        x=3,
        y=50,
        w=21,
        h=37,
        title="1. REAL DATA SOURCES",
        subtitle="Downloaded, checksummed, licensed",
        items=[
            "GDELT 2.0 GKG 15-min (live recorder)",
            "SEC EDGAR 8-K filings (live recorder)",
            "Polygon 2023 news: 5,548 articles",
            "Kaggle stock tweets: 862k (2017-18)",
            "HF labeled fin. tweets: 21k + 12k",
            "Kaggle card txns: 13.3M -> Module B",
            "yfinance closes; SHA-256 manifest",
        ],
        border_color="#0284c7",
        bg_color="#0f172a",
        header_color="#38bdf8",
    )

    # Column 1 bottom: replay, dedup, relevance
    draw_card(
        x=3,
        y=10,
        w=21,
        h=36,
        title="2. REPLAY, DEDUP & RELEVANCE",
        subtitle="Badged sources, offline runtime",
        items=[
            "Source registry: synthetic / historical / live",
            "Logical replay clock, live append",
            "Exact hash + MinHash-LSH near-dup",
            "Lead-sentence index (headline reposts)",
            "24 h window; 100k tweets in 26 s",
            "Social spam & relevance filter",
            "No network calls in the app runtime",
        ],
        border_color="#6366f1",
        bg_color="#0f172a",
        header_color="#818cf8",
    )

    # Column 2: NLP risk engine
    draw_card(
        x=27,
        y=10,
        w=22,
        h=77,
        title="3. NLP RISK ENGINE",
        subtitle="Trained and validated on real data",
        items=[
            f"Entity linker, S&P 500 universe: P {fmt(ent.get('precision'))}",
            "One signal per company (multi-entity)",
            f"Event classifier: macro-F1 {fmt(ev.get('macro_f1_model'))}",
            "  (4,117 held-out real tweets)",
            "Calibrated abstention + evidence gates",
            f"  precision {fmt(ev.get('precision_when_fired'))} when it fires",
            f"Sentiment: macro-F1 {fmt(se.get('macro_f1'))} (lexicon {fmt(se.get('baseline_lexicon_macro_f1'))})",
            "Rate cut / hike direction rules",
            "Impact 1-10: market-calibrated decile",
            f"  vs abnormal return: rho {fmt(imp.get('learned_oof_spearman'))}",
            "Rubric components + evidence spans",
            "8-K cyber / credit / routine filings",
            f"p95 {fmt(perf.get('latency_p95_s'))} s per record on CPU",
        ],
        border_color="#10b981",
        bg_color="#064e3b22",
        header_color="#34d399",
    )

    # Column 3: Module A
    draw_card(
        x=52,
        y=50,
        w=21,
        h=37,
        title="4. MODULE A: INDEX REBALANCER",
        subtitle="Sentiment-tilted mock S&P 100 index",
        items=[
            "20 names, equal base weights",
            "Time-decayed sentiment EMA per name",
            "w = base x (1 + k x EMA), long-only",
            "Caps: 20% per name, 40% per sector",
            "Weights over time + reasons + turnover",
            "Back-test on real tweets & prices",
            "Reported honestly: no proven alpha",
        ],
        border_color="#f59e0b",
        bg_color="#0f172a",
        header_color="#fbbf24",
    )

    # Column 3 bottom: Module B
    draw_card(
        x=52,
        y=10,
        w=21,
        h=36,
        title="5. MODULE B: STRESS ENGINE",
        subtitle="$610M funded + $150M swap notional",
        items=[
            "Wholesale $500M (synthetic book)",
            "Retail/SME $50M from real card txns",
            "Equity $60M, betas from real prices",
            "ECL, duration, signed DV01, beta",
            "Shocks from 5 real crisis windows",
            "Contagion graph; CYBER fraud op-loss",
            "Reconciled; NO_EXPOSURE flagged",
        ],
        border_color="#ec4899",
        bg_color="#0f172a",
        header_color="#f472b6",
    )

    # Column 4: API, audit, terminal
    draw_card(
        x=76,
        y=10,
        w=21,
        h=77,
        title="6. API, AUDIT & TERMINAL UI",
        subtitle="Localhost FastAPI + React",
        items=[
            "POST /api/analyze, /api/replay/*",
            "GET /api/signals, SSE event stream",
            "data/signals.jsonl file sink (PS)",
            "GET /api/index/* (Module A)",
            "POST /api/stress/scenario, /custom",
            "SQLite audit store, JSON/CSV export",
            "React terminal: live feed + inspector",
            "Module A weights-over-time chart",
            "Module B before/after + waterfall",
            "Real-data metrics panel",
            "docs/metrics.json: single source",
            "CI recomputes real-data suites",
        ],
        border_color="#8b5cf6",
        bg_color="#0f172a",
        header_color="#a78bfa",
    )

    # Connector Arrows
    arrow_props = dict(arrowstyle="-|>", lw=2, color="#38bdf8", mutation_scale=15)
    # 1 -> 2
    ax.annotate("", xy=(13.5, 46.5), xytext=(13.5, 49.5), arrowprops=arrow_props)
    # 2 -> 3
    ax.annotate("", xy=(26.5, 48.5), xytext=(24.2, 48.5), arrowprops=arrow_props)
    # 3 -> 4 (sentiment to Module A)
    ax.annotate("", xy=(51.5, 68.5), xytext=(49.2, 68.5), arrowprops=arrow_props)
    # 3 -> 5 (event + impact to Module B)
    ax.annotate("", xy=(51.5, 28.5), xytext=(49.2, 28.5), arrowprops=arrow_props)
    # 5 -> 6
    ax.annotate("", xy=(75.5, 28.5), xytext=(73.2, 28.5), arrowprops=arrow_props)
    # 4 -> 6
    ax.annotate("", xy=(75.5, 68.5), xytext=(73.2, 68.5), arrowprops=arrow_props)

    # Footer Notes
    ax.text(
        3,
        3,
        "S&P Global & CRISIL Campus Hackathon 2026 | Candidate: Aman Gupta (IIT Kharagpur) | Metrics: docs/metrics.json (scripts/run_evaluation.py)",
        fontsize=8.5,
        color="#64748b",
        fontfamily="sans-serif",
    )

    plt.tight_layout()
    OUTPUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(OUTPUT_PNG, facecolor=fig.get_facecolor(), edgecolor="none", bbox_inches="tight")
    plt.close()
    print(f"Architecture diagram generated successfully at {OUTPUT_PNG.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    create_architecture_diagram()
