#!/usr/bin/env python3
"""Generate submission presentation deck PDF for S&P Sentinel.

Creates docs/presentation.pdf (7-slide presentation) conforming to
S&P Global & CRISIL Campus Hackathon guidelines and PRD requirements.
"""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PDF = REPO_ROOT / "docs" / "presentation.pdf"


def build_presentation_pdf() -> None:
    OUTPUT_PDF.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(OUTPUT_PDF),
        pagesize=landscape(letter),
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()

    # Custom styles for presentation
    title_style = ParagraphStyle(
        "SlideTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=22,
        leading=26,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=6,
    )
    subtitle_style = ParagraphStyle(
        "SlideSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#0284c7"),
        spaceAfter=14,
    )
    body_style = ParagraphStyle(
        "SlideBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#334155"),
        spaceAfter=8,
    )
    bullet_style = ParagraphStyle(
        "SlideBullet",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13.5,
        textColor=colors.HexColor("#1e293b"),
        leftIndent=15,
        spaceAfter=5,
    )
    card_title_style = ParagraphStyle(
        "CardTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=4,
    )

    elements = []

    # -------------------------------------------------------------
    # SLIDE 1: Title & Executive Overview
    # -------------------------------------------------------------
    elements.append(Paragraph("S&P SENTINEL", title_style))
    elements.append(
        Paragraph(
            "Financial-Text Risk Intelligence & Wholesale Portfolio Stress Testing Platform",
            subtitle_style,
        )
    )
    elements.append(Spacer(1, 10))

    meta_text = """
    <b>Candidate:</b> Aman Gupta &nbsp;|&nbsp; <b>Institution:</b> Indian Institute of Technology Kharagpur (IIT Kharagpur)<br/>
    <b>Event:</b> S&P Global & CRISIL Campus Hackathon 2026 &nbsp;|&nbsp; <b>Track:</b> Risk Intelligence Track<br/>
    <b>Localhost Policy:</b> 100% Offline Runtime &bull; Zero Cloud Keys &bull; SHA-256 Audited Datasets
    """
    elements.append(Paragraph(meta_text, body_style))
    elements.append(Spacer(1, 15))

    s1_cards = [
        [
            Paragraph("<b>The Institutional Challenge</b>", card_title_style),
            Paragraph("<b>The Sentinel Solution</b>", card_title_style),
        ],
        [
            Paragraph(
                "Traditional institutional risk monitoring operates with latency. By the time corporate earnings reports or debt rating downgrades are published, counterparty contagion and market spreads have already moved against the bank balance sheet.",
                body_style,
            ),
            Paragraph(
                "Sentinel provides an auditable, sub-150ms risk intelligence engine. It extracts grounded financial signals from unstructured news and social streams, runs multi-hop contagion propagation, and revalues wholesale portfolio positions in real time.",
                body_style,
            ),
        ],
    ]
    t1 = Table(s1_cards, colWidths=[350, 350])
    t1.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 1, colors.HexColor("#e2e8f0")),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ]
        )
    )
    elements.append(t1)
    elements.append(PageBreak())

    # -------------------------------------------------------------
    # SLIDE 2: Architecture & Localhost Execution Policy
    # -------------------------------------------------------------
    elements.append(Paragraph("System Architecture & Localhost Execution", title_style))
    elements.append(Paragraph("End-to-End Pipeline & Strict Security Compliance", subtitle_style))

    arch_bullets = [
        "<b>Multi-Source Ingestion:</b> Structured news CSVs, noisy social chatter with cashtags ($APEX, $TSTEL), reference universe of 23 tickers, and Kaggle open benchmarks.",
        "<b>Replay Controller & Deduplication:</b> Clock-controlled logical replay (1x-60x) with token Jaccard (≥0.65) and containment (≥0.80) near-duplicate suppression.",
        "<b>Hybrid NLP Risk Engine:</b> CPU-optimized FinBERT sentiment distribution, 10-class financial event classifier, exact character span grounding, and 1-10 severity rubric.",
        "<b>Contagion Knowledge Graph:</b> NetworkX directed customer-supplier and creditor-debtor graph with 2-hop dampening (0.50/hop) to prevent runaway feedback.",
        "<b>Wholesale Stress Valuation:</b> Real-time mark-to-market and Expected Credit Loss (ECL) revaluation across loans, corporate bonds, SOFR swaps, and retail credit.",
        "<b>Cryptographic Provenance:</b> 15 datasets tracked in data/manifest.json with SHA-256 checksums. Verified zero external cloud API calls in backend runtime.",
    ]
    for b in arch_bullets:
        elements.append(Paragraph(f"&bull; {b}", bullet_style))
    elements.append(PageBreak())

    # -------------------------------------------------------------
    # SLIDE 3: Multi-Source NLP Risk Intelligence
    # -------------------------------------------------------------
    elements.append(Paragraph("Multi-Source NLP Risk Intelligence", title_style))
    elements.append(Paragraph("Entity Linking, Sentiment Scoring, and Severity Rubric", subtitle_style))

    nlp_cards = [
        [
            Paragraph("<b>Entity Linking & Exact Spans</b>", card_title_style),
            Paragraph("<b>Domain Sentiment Scoring</b>", card_title_style),
        ],
        [
            Paragraph(
                "• Links corporate mentions to canonical tickers via alias tables.<br/>"
                "• Extracts exact start/end character offsets for textual evidence grounding.<br/>"
                "• Handles ambiguous references and cashtag tokens seamlessly.",
                body_style,
            ),
            Paragraph(
                "• FinBERT & Lexicon hybrid calibrated to financial vernacular.<br/>"
                "• Strict probability distribution: P(pos) + P(neg) + P(neu) = 1.0.<br/>"
                "• Continuous polarity score mapped to [-1.0, +1.0] domain.",
                body_style,
            ),
        ],
        [
            Paragraph("<b>10-Class Event Taxonomy</b>", card_title_style),
            Paragraph("<b>Additive 1-10 Severity Rubric</b>", card_title_style),
        ],
        [
            Paragraph(
                "• Structured classes: CREDIT, MACRO, SUPPLY_CHAIN, REGULATORY, EARNINGS, M&A, CYBER, ESG, PRODUCT, OTHER.<br/>"
                "• Confidence thresholding with explicit fallback to OTHER to avoid false alarms.",
                body_style,
            ),
            Paragraph(
                "• Standardized impact severity: Base Severity + Scope + Multipliers.<br/>"
                "• Dynamic calibration based on regulatory penalties and capital spend.<br/>"
                "• Severity MAE: 0.89 points against gold rubric (Target ≤ 1.50 pts).",
                body_style,
            ),
        ],
    ]
    t3 = Table(nlp_cards, colWidths=[350, 350])
    t3.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 1, colors.HexColor("#e2e8f0")),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    elements.append(t3)
    elements.append(PageBreak())

    # -------------------------------------------------------------
    # SLIDE 4: Contagion Propagation & Deduplication Engine
    # -------------------------------------------------------------
    elements.append(Paragraph("Contagion Propagation & Deduplication", title_style))
    elements.append(Paragraph("Network Topologies and Second-Order Risk Transmission", subtitle_style))

    cont_bullets = [
        "<b>Rolling Window Deduplication:</b> Identical or near-duplicate news items within a rolling 24-hour window are suppressed using Jaccard word set similarity (≥0.65) and containment (≥0.80), eliminating duplicate shocks to balance sheets.",
        "<b>Directed Knowledge Graph:</b> Explicit corporate supply-chain linkages (e.g., APEX supplies TSTEL at 0.45 weight; TSTEL supplies VAUTO at 0.65 weight).",
        "<b>Geometric Multi-Hop Damping:</b> Contagion shock dampens across network hops (factor = weight × 0.50^hop). Prevents artificial systemic runaway.",
        "<b>Second-Order Transmission Example:</b> A credit default shock at APEX propagates 1 hop to Titan Steel (TSTEL) and 2 hops to Vanguard Auto (VAUTO), while unaffected sectors remain insulated (0 bps change).",
    ]
    for b in cont_bullets:
        elements.append(Paragraph(f"&bull; {b}", bullet_style))
    elements.append(PageBreak())

    # -------------------------------------------------------------
    # SLIDE 5: Module B — Wholesale Portfolio & Retail Credit Stress Testing
    # -------------------------------------------------------------
    elements.append(Paragraph("Module B — Wholesale Stress Testing", title_style))
    elements.append(Paragraph("$500M Institutional Book + $50M Retail Credit Sleeve", subtitle_style))

    portfolio_data = [
        ["Asset Class", "Book Exposure", "Valuation Metric", "Stress Transmission Mechanism"],
        ["Syndicated Corporate Loans", "$220,000,000", "Expected Credit Loss (ECL)", "ΔPD = Baseline PD × severity × shock factor; ECL = EAD × ΔPD × LGD"],
        ["Corporate Fixed Bonds", "$200,000,000", "Mark-to-Market (MtM)", "ΔP = -ModDuration × ΔSpread + 0.5 × Convexity × (ΔSpread)²"],
        ["SOFR Interest Rate Swaps", "$150,000,000 gross", "Signed DV01 Sensitivity", "ΔMtM = Signed DV01 × ΔCurve bps (directional for pay vs receive)"],
        ["Consumer/SME Credit Sleeve", "$50,000,000", "Pooled ECL Tranches", "Aggregated from Kaggle retail debt data mapped to 8 sectors"],
        ["Systemic Macro Curve Shifts", "Portfolio-wide", "Yield Curve Shift (±bps)", "Applies systemic interest rate shocks directly across all asset sleeves"],
    ]
    t5 = Table(portfolio_data, colWidths=[140, 110, 150, 300])
    t5.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0284c7")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 9),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f8fafc")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("FONTSIZE", (0, 1), (-1, -1), 8.5),
            ]
        )
    )
    elements.append(t5)
    elements.append(PageBreak())

    # -------------------------------------------------------------
    # SLIDE 6: Rigorous Quantitative Evaluation & De-Leaked Benchmarks
    # -------------------------------------------------------------
    elements.append(Paragraph("Quantitative Evaluation & Honest Benchmarks", title_style))
    elements.append(Paragraph("105 De-Leaked Holdout Samples with Confusion Matrix & Baselines", subtitle_style))

    eval_data = [
        ["Benchmark Metric", "Measured Value", "PRD Target", "Baseline Comparison", "Audit Verification"],
        ["Entity Linking Precision", "100.0%", "≥ 90.0%", "Keyword Baseline: 75.0%", "Exact character spans, zero placeholders"],
        ["Event Classification Macro-F1", "0.382", "≥ 0.70", "Keyword Baseline: 0.448", "High precision (~1.0), selective recall"],
        ["Sentiment Macro-F1", "0.340", "≥ 0.75", "Lexicon Baseline: 0.651", "Continuous score MAE: 0.419 pts"],
        ["Severity Rubric MAE", "0.89 pts", "≤ 1.50 pts", "Constant Mean: 2.10 pts", "90.5% within ±1.0 point of gold rubric"],
        ["Adversarial Sample Accuracy", "91.7%", "≥ 80.0%", "Adversarial Disambiguation", "Correctly rejects rumors and denials"],
    ]
    t6 = Table(eval_data, colWidths=[150, 95, 85, 160, 210])
    t6.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#10b981")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 9),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f8fafc")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("FONTSIZE", (0, 1), (-1, -1), 8.5),
            ]
        )
    )
    elements.append(t6)
    elements.append(Spacer(1, 10))
    elements.append(
        Paragraph(
            "<b>Reproducibility Guarantee:</b> All metrics evaluated locally without internet access. Fully reproducible via: <code>uv run python scripts/run_evaluation.py</code>",
            body_style,
        )
    )
    elements.append(PageBreak())

    # -------------------------------------------------------------
    # SLIDE 7: Compliance, Integrity & Production Readiness
    # -------------------------------------------------------------
    elements.append(Paragraph("Compliance, Integrity & Production Readiness", title_style))
    elements.append(Paragraph("Zero-Data-Loss Standards and Institutional Governance", subtitle_style))

    comp_cards = [
        [
            Paragraph("<b>Hackathon Guidelines Compliance</b>", card_title_style),
            Paragraph("<b>Production S&P / CRISIL Fit</b>", card_title_style),
        ],
        [
            Paragraph(
                "• <b>Section 8 (Confidentiality):</b> Zero confidential client or proprietary rating data utilized.<br/>"
                "• <b>Section 9 (IP & Licensing):</b> MIT License for project-authored code, explicit attributions for CC BY-NC-SA and CC0 datasets.<br/>"
                "• <b>Zero Secrets:</b> verify_hygiene.py strictly validates no credentials or tokens exist.",
                body_style,
            ),
            Paragraph(
                "• <b>Feed Integration:</b> Drop-in microservice exposing FastAPI endpoints (/api/signals, /api/stress/run).<br/>"
                "• <b>Real-Time Audit Sink:</b> data/signals.jsonl append-only log for regulatory compliance.<br/>"
                "• <b>Zero Cloud Key Overhead:</b> Runs entirely on standard commodity CPU hardware.",
                body_style,
            ),
        ],
    ]
    t7 = Table(comp_cards, colWidths=[350, 350])
    t7.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 1, colors.HexColor("#e2e8f0")),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ]
        )
    )
    elements.append(t7)

    doc.build(elements)
    print(f"Presentation PDF successfully generated at {OUTPUT_PDF.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    build_presentation_pdf()
