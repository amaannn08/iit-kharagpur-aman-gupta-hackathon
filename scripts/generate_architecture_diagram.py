#!/usr/bin/env python3
"""Generate high-resolution system architecture diagram for S&P Sentinel.

Outputs docs/architecture.png with an institutional, dark-themed layout
illustrating all six pipeline stages conforming to the PRD specification.
"""

from pathlib import Path

import matplotlib.patches as patches
import matplotlib.pyplot as plt

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PNG = REPO_ROOT / "docs" / "architecture.png"


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
        (3, 91), 94, 7, boxstyle="round,pad=0.3",
        fc="#111827", ec="#38bdf8", lw=1.5
    )
    ax.add_patch(title_box)
    ax.text(
        5, 95.5, "S&P SENTINEL — SYSTEM ARCHITECTURE & DATA FLOW",
        fontsize=16, fontweight="bold", color="#f8fafc", fontfamily="sans-serif"
    )
    ax.text(
        5, 92.5, "Financial-Text Risk Intelligence & Wholesale Balance Sheet Stress Testing Platform | IIT Kharagpur",
        fontsize=10, color="#94a3b8", fontfamily="sans-serif"
    )
    ax.text(
        80, 94, "100% OFFLINE LOCALHOST\nSHA-256 AUDITED",
        fontsize=9, fontweight="bold", color="#10b981", ha="center", va="center"
    )

    # Helper function for drawing module cards
    def draw_card(x, y, w, h, title, subtitle, items, border_color="#334155", bg_color="#131b2e", header_color="#38bdf8"):
        box = patches.FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0.5",
            fc=bg_color, ec=border_color, lw=1.5
        )
        ax.add_patch(box)
        # Header banner
        header_strip = patches.Rectangle(
            (x, y + h - 4.5), w, 4.5,
            fc="#1e293b", ec="none"
        )
        ax.add_patch(header_strip)
        ax.text(
            x + 1.5, y + h - 2.8, title,
            fontsize=11, fontweight="bold", color=header_color, fontfamily="sans-serif"
        )
        if subtitle:
            ax.text(
                x + 1.5, y + h - 4.0, subtitle,
                fontsize=8, color="#94a3b8", fontfamily="sans-serif"
            )

        # Content list items
        curr_y = y + h - 7.5
        for item in items:
            ax.text(
                x + 2, curr_y, f"• {item}",
                fontsize=8.5, color="#e2e8f0", fontfamily="sans-serif"
            )
            curr_y -= 3.2

    # Column 1: Ingestion & Provenance (X: 3 to 22)
    draw_card(
        x=3, y=50, w=21, h=37,
        title="1. MULTI-SOURCE INGESTION",
        subtitle="Heterogeneous Offline Contracts",
        items=[
            "News CSV (Curated & Kaggle)",
            "Social Media (Cashtags & Rumors)",
            "Reference Universe (23 Tickers)",
            "Kaggle FinancialPhraseBank",
            "Pydantic v2 InputRecord",
            "Immutable Timestamp Quality",
            "SHA-256 Manifest (15 Datasets)"
        ],
        border_color="#0284c7", bg_color="#0f172a", header_color="#38bdf8"
    )

    # Column 1 bottom: Replay Controller
    draw_card(
        x=3, y=10, w=21, h=36,
        title="2. REPLAY & DEDUPLICATION",
        subtitle="Temporal Replay & Near-Dup Filter",
        items=[
            "Logical Replay Clock (1x-60x)",
            "Rolling Deduplication Window",
            "Token Jaccard Similarity (≥0.65)",
            "Sub-phrase Containment (≥0.80)",
            "Duplicate Echo Suppression",
            "Burst Chatter Aggregation",
            "Zero Cloud Key Requirement"
        ],
        border_color="#6366f1", bg_color="#0f172a", header_color="#818cf8"
    )

    # Column 2: Hybrid NLP Risk Engine (X: 27 to 48)
    draw_card(
        x=27, y=10, w=22, h=77,
        title="3. HYBRID NLP RISK ENGINE",
        subtitle="Multi-Task Feature Extraction Pipeline",
        items=[
            "Entity Linking & True Character Spans",
            "Alias & Ambiguity Resolution",
            "FinBERT & Financial Lexicon Sentiment",
            "Strict Probability Sum Validation",
            "Continuous Sentiment [-1.0, +1.0]",
            "10-Class Financial Event Taxonomy",
            "CREDIT, MACRO, SUPPLY_CHAIN, etc.",
            "Confidence Abstention (OTHER Fallback)",
            "Additive 1-10 Severity Rubric",
            "Base + Scope + Dynamic Multipliers",
            "De-Leaked Gold Holdout (105 Rows)",
            "Rule-Based Baseline Comparison",
            "Deterministic Grounding Spans"
        ],
        border_color="#10b981", bg_color="#064e3b22", header_color="#34d399"
    )

    # Column 3: Contagion & Shock Mapping (X: 52 to 73)
    draw_card(
        x=52, y=50, w=21, h=37,
        title="4. CONTAGION NETWORK",
        subtitle="NetworkX Multi-Hop Propagation",
        items=[
            "Directed Customer-Supplier Graph",
            "Debtor-Creditor Linkages",
            "Multi-Hop Transmission Engine",
            "Bounded Decay (0.50 per hop)",
            "Second-Order Counterparty Shock",
            "Cyclic Loop Prevention",
            "Isolated Node Protection"
        ],
        border_color="#f59e0b", bg_color="#0f172a", header_color="#fbbf24"
    )

    # Column 3 bottom: Module B Wholesale Stress Engine
    draw_card(
        x=52, y=10, w=21, h=36,
        title="5. WHOLESALE STRESS ENGINE",
        subtitle="Multi-Asset Revaluation & Loss P&L",
        items=[
            "$500M Wholesale Banking Book",
            "Corporate Loans: ECL (ΔPD × LGD)",
            "Corporate Bonds: Duration & Convexity",
            "SOFR Swaps: Signed DV01 Curve Delta",
            "$50M Retail Credit Sleeve (Kaggle)",
            "Systemic Macro Curve Shifts (±bps)",
            "Stress Waterfall & Portfolio P&L"
        ],
        border_color="#ec4899", bg_color="#0f172a", header_color="#f472b6"
    )

    # Column 4: Storage, Audit & UI (X: 76 to 97)
    draw_card(
        x=76, y=10, w=21, h=77,
        title="6. API, AUDIT & TERMINAL UI",
        subtitle="Localhost FastAPI & React UI",
        items=[
            "FastAPI Core Service (Port 8000)",
            "GET /api/signals?since= Filtering",
            "POST /api/analyze (Ad-hoc Text)",
            "POST /api/stress/run (Crisis Scenarios)",
            "signals.jsonl Append-Only File Sink",
            "SQLite Audit Store & Replay Logs",
            "React 18 + TypeScript + Vite UI",
            "Institutional High-Contrast Dark Mode",
            "Live Feed, Contagion Graph & Matrix",
            "Loss Attribution Waterfall",
            "Cryptographic Data Hygiene Gate",
            "Zero External Runtime Calls"
        ],
        border_color="#8b5cf6", bg_color="#0f172a", header_color="#a78bfa"
    )

    # Connector Arrows
    arrow_props = dict(
        arrowstyle="-|>", lw=2, color="#38bdf8", mutation_scale=15
    )
    # 1 -> 2
    ax.annotate("", xy=(13.5, 46.5), xytext=(13.5, 49.5), arrowprops=arrow_props)
    # 2 -> 3
    ax.annotate("", xy=(26.5, 48.5), xytext=(24.2, 48.5), arrowprops=arrow_props)
    # 3 -> 4
    ax.annotate("", xy=(51.5, 68.5), xytext=(49.2, 68.5), arrowprops=arrow_props)
    # 3 -> 5
    ax.annotate("", xy=(51.5, 28.5), xytext=(49.2, 28.5), arrowprops=arrow_props)
    # 4 -> 5
    ax.annotate("", xy=(62.5, 46.5), xytext=(62.5, 49.5), arrowprops=arrow_props)
    # 5 -> 6
    ax.annotate("", xy=(75.5, 28.5), xytext=(73.2, 28.5), arrowprops=arrow_props)
    # 4 -> 6
    ax.annotate("", xy=(75.5, 68.5), xytext=(73.2, 68.5), arrowprops=arrow_props)

    # Footer Notes
    ax.text(
        3, 3, "S&P Global & CRISIL Campus Hackathon 2026 | Candidate: Aman Gupta (IIT Kharagpur) | Codebase Status: Verified Green (71 Tests, Zero External Network Calls)",
        fontsize=8.5, color="#64748b", fontfamily="sans-serif"
    )

    plt.tight_layout()
    OUTPUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(OUTPUT_PNG, facecolor=fig.get_facecolor(), edgecolor="none", bbox_inches="tight")
    plt.close()
    print(f"Architecture diagram generated successfully at {OUTPUT_PNG.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    create_architecture_diagram()
