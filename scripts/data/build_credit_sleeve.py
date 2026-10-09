#!/usr/bin/env python3
"""Build retail credit portfolio sleeve from Kaggle transactions & user debt data.

Implements Problem Statement Module B ("provided sample transaction data")
per Review Plan Section 6.4:
1. Ingests user credit scores, debts, and MCC merchant profiles.
2. Applies standard Basel/A-IRB credit risk rating buckets (Score -> PD).
3. Maps consumer/SME merchant category codes to industrial sectors.
4. Aggregates into pooled LoanPosition tranches for wholesale stress valuation.
"""

import csv
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RAW_DIR = REPO_ROOT / "data" / "raw" / "kaggle" / "transactions"
OUT_DIR = REPO_ROOT / "data" / "portfolio"

MCC_TO_SECTOR = {
    "5411": "Consumer Staples",
    "4814": "Telecommunications",
    "5541": "Energy",
    "4511": "Industrials",
    "5732": "Technology",
    "5044": "Commercial Services",
    "8011": "Healthcare",
    "1520": "Real Estate",
}


def score_to_rating_and_pd(score: int) -> tuple[str, float]:
    """Map FICO/credit score to supervisory rating bucket and baseline PD."""
    if score >= 760:
        return "AA", 0.005
    elif score >= 700:
        return "BBB", 0.015
    elif score >= 640:
        return "BB", 0.040
    else:
        return "B-", 0.100


def build_credit_sleeve() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    users_file = RAW_DIR / "users.csv"

    if not users_file.exists():
        print(f"Error: {users_file} does not exist.")
        return

    print(f"[CREDIT SLEEVE] Aggregating retail credit data from {users_file.relative_to(REPO_ROOT)}...")

    tranches: dict[tuple[str, str], dict] = {}

    with open(users_file, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            score = int(row.get("credit_score", 680))
            debt = float(row.get("total_debt", 25000))
            mcc = row.get("mcc_dominant", "5411")

            sector = MCC_TO_SECTOR.get(mcc, "Financials")
            rating, pd_val = score_to_rating_and_pd(score)

            key = (sector, rating)
            if key not in tranches:
                tranches[key] = {
                    "sector": sector,
                    "rating": rating,
                    "pd": pd_val,
                    "total_ead": 0.0,
                    "count": 0,
                }

            tranches[key]["total_ead"] += debt
            tranches[key]["count"] += 1

    # Scale tranches to representative institutional sleeve (~$50M total EAD)
    raw_total_ead = sum(t["total_ead"] for t in tranches.values()) or 1.0
    target_sleeve_ead = 50_000_000.0  # $50M retail credit sleeve
    scale_factor = target_sleeve_ead / raw_total_ead

    positions = []
    idx = 1
    for (sector, rating), data in sorted(tranches.items()):
        scaled_ead = round(data["total_ead"] * scale_factor, 2)
        pos_id = f"RTL-LOAN-{idx:03d}"
        pos = {
            "position_id": pos_id,
            "asset_class": "loan",
            "entity_id": f"RTL_{sector[:4].upper()}_{rating}",
            "counterparty_name": f"Pooled Retail & SME {sector} ({rating} Tranche)",
            "sector": sector,
            "currency": "USD",
            "market_value": scaled_ead,
            "ead": scaled_ead,
            "baseline_pd": data["pd"],
            "lgd": 0.80,  # Unsecured consumer/SME credit
            "rating": rating,
            "maturity_date": "2027-12-31",
        }
        positions.append(pos)
        idx += 1

    # Write CSV
    csv_file = OUT_DIR / "credit_sleeve.csv"
    fieldnames = [
        "position_id",
        "asset_class",
        "entity_id",
        "counterparty_name",
        "sector",
        "currency",
        "market_value",
        "ead",
        "baseline_pd",
        "lgd",
        "rating",
        "maturity_date",
    ]
    with open(csv_file, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(positions)
    print(f"  OK: Wrote {len(positions)} pooled loan tranches to {csv_file.relative_to(REPO_ROOT)}")

    # Write JSON portfolio wrapper
    json_file = OUT_DIR / "credit_sleeve.json"
    sleeve_doc = {
        "portfolio_name": "Consumer & SME Retail Credit Portfolio Sleeve (Kaggle Transaction Ingestion)",
        "base_currency": "USD",
        "target_book_value_usd": target_sleeve_ead,
        "summary": {
            "total_book_value_usd": target_sleeve_ead,
            "corporate_loans_value_usd": target_sleeve_ead,
            "corporate_bonds_value_usd": 0.0,
            "cash_reserves_usd": 0.0,
        },
        "positions": positions,
    }
    with open(json_file, mode="w", encoding="utf-8") as f:
        json.dump(sleeve_doc, f, indent=2)
        f.write("\n")
    print(f"  OK: Wrote JSON credit sleeve to {json_file.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    build_credit_sleeve()
