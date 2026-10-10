#!/usr/bin/env python3
"""Build the Module B retail/SME credit sleeve from the REAL Kaggle transactions dataset.

PS Module B: "Define a synthetic portfolio using the provided sample transaction data."
Source: computingvictor/transactions-fraud-datasets (Apache-2.0) in data/raw/real/transactions:
  users_data.csv (2,000 borrowers: credit score, income, total debt), cards_data.csv (6,146
  cards: credit limits), transactions_data.csv (13.3M card transactions with MCC codes),
  mcc_codes.json, train_fraud_labels.json (per-transaction fraud flags).

Method (assumptions are documented in docs/assumptions.md):
  - EAD = total debt + 30% credit-conversion factor on credit-card limits
  - 1-year PD from credit-score band; LGD 80% (unsecured consumer/SME credit)
  - sector = the GICS sector of each borrower's largest card-spend category (MCC)
  - borrowers pooled into sector x rating-band tranches (>= 10 borrowers each), scaled so the
    sleeve totals a stated $50M; scale_factor is recorded
  - observed fraud rate per sector (labelled transactions) feeds the CYBER operational-loss shock
Card numbers, CVVs and addresses are never read or written.

Output: data/portfolio/credit_sleeve.json (aggregates only)
Usage:  uv run python scripts/data/build_credit_sleeve.py
"""

import importlib.util
import json
import sys
import time
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RAW = REPO_ROOT / "data" / "raw" / "real" / "transactions"
OUT = REPO_ROOT / "data" / "portfolio" / "credit_sleeve.json"
SLEEVE_SIZE_USD = 50_000_000.0
CCF = 0.30
LGD = 0.80
MIN_BORROWERS = 10
# (lower, upper) credit score -> (rating band, 1-year PD)
SCORE_BANDS = [
    (0, 580, "CCC", 0.20),
    (580, 640, "B", 0.10),
    (640, 700, "BB", 0.04),
    (700, 760, "BBB", 0.015),
    (760, 900, "A", 0.005),
]
# MCC description keywords -> GICS sector (first match wins)
MCC_SECTOR_RULES = [
    (
        ("grocery", "supermarket", "drug", "pharmac", "wholesale club", "beverage", "candy"),
        "Consumer Staples",
    ),
    (("service station", "fuel", "petroleum", "oil"), "Energy"),
    (("utilities", "electric", "gas, water"), "Utilities"),
    (
        ("telecommunication", "cable", "satellite", "computer network", "telegraph"),
        "Communication Services",
    ),
    (
        (
            "airline",
            "air carrier",
            "railroad",
            "toll",
            "bus line",
            "taxicab",
            "freight",
            "trucking",
            "transportation",
            "travel agenc",
            "cruise",
            "postal",
            "courier",
        ),
        "Industrials",
    ),  # fmt: skip
    (
        (
            "medical",
            "doctor",
            "physician",
            "hospital",
            "dentist",
            "optometr",
            "chiropract",
            "health",
            "nursing",
            "laborator",
        ),
        "Health Care",
    ),  # fmt: skip
    (("money transfer", "insurance", "securities", "financial", "bank"), "Financials"),
    (("computer", "software", "electronic", "digital goods"), "Information Technology"),
    (
        (
            "lumber",
            "building material",
            "hardware",
            "contractor",
            "construction",
            "heating",
            "plumbing",
            "roofing",
            "industrial",
            "machinery",
            "steel",
            "metal",
            "chemical",
            "tool",
            "equipment",
        ),
        "Industrials",
    ),  # fmt: skip
]


def mcc_sector(description: str) -> str:
    d = description.lower()
    for keywords, sector in MCC_SECTOR_RULES:
        if any(k in d for k in keywords):
            return sector
    return "Consumer Discretionary"  # restaurants, retail, hotels, entertainment, auto, ...


def money(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.astype(str).str.replace(r"[$,]", "", regex=True), errors="coerce")


def band(score: float):
    for lo, hi, rating, pd_ in SCORE_BANDS:
        if lo <= score < hi:
            return rating, pd_
    return None, None


def main() -> None:
    if not RAW.exists():
        sys.exit("data/raw/real/transactions missing: run scripts/data/fetch_real.py --only kaggle")
    t0 = time.time()
    mcc_desc = json.loads((RAW / "mcc_codes.json").read_text())
    sector_of_mcc = {int(k): mcc_sector(v) for k, v in mcc_desc.items()}

    users = pd.read_csv(
        RAW / "users_data.csv", usecols=["id", "credit_score", "yearly_income", "total_debt"]
    )
    for c in ("yearly_income", "total_debt"):
        users[c] = money(users[c])
    cards = pd.read_csv(RAW / "cards_data.csv", usecols=["client_id", "card_type", "credit_limit"])
    cards["credit_limit"] = money(cards.credit_limit)
    credit_limits = (
        cards[cards.card_type.str.contains("Credit", na=False)]
        .groupby("client_id")
        .credit_limit.sum()
    )

    labels = pd.Series(json.loads((RAW / "train_fraud_labels.json").read_text())["target"])
    labels.index = labels.index.astype("int64")
    is_fraud = labels.eq("Yes")

    spend_parts, fraud_parts, n_tx = [], [], 0
    cols = ["id", "client_id", "amount", "mcc"]
    for chunk in pd.read_csv(RAW / "transactions_data.csv", usecols=cols, chunksize=2_000_000):
        n_tx += len(chunk)
        chunk["amount"] = money(chunk.amount).clip(lower=0)
        chunk["sector"] = chunk.mcc.map(sector_of_mcc).fillna("Consumer Discretionary")
        spend_parts.append(chunk.groupby(["client_id", "sector"]).amount.sum())
        flags = chunk.id.map(is_fraud)  # NaN where the transaction has no label
        labelled = chunk.assign(fraud=flags).dropna(subset=["fraud"])
        fraud_parts.append(labelled.groupby("sector").fraud.agg(["sum", "count"]))

    spend = pd.concat(spend_parts).groupby(level=[0, 1]).sum().reset_index()
    dominant = (
        spend.sort_values("amount").groupby("client_id").tail(1).set_index("client_id").sector
    )
    fraud = pd.concat(fraud_parts).groupby(level=0).sum()
    fraud_rate = (fraud["sum"] / fraud["count"]).round(6)

    u = (
        users.set_index("id")
        .join(credit_limits.rename("credit_limit"))
        .join(dominant.rename("sector"))
    )
    u["ead"] = u.total_debt.fillna(0) + CCF * u.credit_limit.fillna(0)
    u[["rating", "pd"]] = u.credit_score.apply(lambda s: pd.Series(band(s)))
    u = u.dropna(subset=["sector", "rating"])
    tr = (
        u.groupby(["sector", "rating"])
        .agg(
            ead=("ead", "sum"),
            pd=("pd", "mean"),
            borrowers=("ead", "size"),
            avg_score=("credit_score", "mean"),
        )
        .reset_index()
    )
    tr = tr[tr.borrowers >= MIN_BORROWERS].reset_index(drop=True)
    scale = SLEEVE_SIZE_USD / tr.ead.sum()

    positions = []
    for i, r in tr.sort_values(["sector", "pd"]).reset_index(drop=True).iterrows():
        value = round(float(r.ead * scale), 2)
        positions.append(
            {
                "position_id": f"RTL-{i + 1:03d}",
                "asset_class": "loan",
                "entity_id": f"RTL_{r.sector.upper().replace(' ', '_')}_{r.rating}",
                "counterparty_name": f"Retail/SME pool: {r.sector} ({r.rating})",
                "sector": r.sector,
                "currency": "USD",
                "market_value": value,
                "ead": value,
                "baseline_pd": round(float(r.pd), 4),
                "lgd": LGD,
                "rating": r.rating,
                "maturity_date": "2027-12-31",
                "sleeve": "retail_sme",
                "borrowers": int(r.borrowers),
                "avg_credit_score": round(float(r.avg_score), 1),
            }
        )
    # Fold per-tranche rounding into the largest tranche so the sleeve totals exactly the target
    residual = round(SLEEVE_SIZE_USD - sum(p["market_value"] for p in positions), 2)
    largest = max(positions, key=lambda p: p["market_value"])
    largest["market_value"] = largest["ead"] = round(largest["market_value"] + residual, 2)

    sleeve = {
        "portfolio_name": "Retail/SME credit sleeve (derived from real card transaction data)",
        "base_currency": "USD",
        "valuation_date": "2026-03-01",
        "is_synthetic": False,
        "source": "kaggle:computingvictor/transactions-fraud-datasets (Apache-2.0)",
        "method": {
            "ead": f"total_debt + {CCF:.0%} CCF x credit-card limits",
            "pd_by_score_band": {b[2]: b[3] for b in SCORE_BANDS},
            "lgd": LGD,
            "sector": "GICS sector of the borrower's largest card-spend MCC category",
            "min_borrowers_per_tranche": MIN_BORROWERS,
            "scale_factor": round(float(scale), 8),
            "raw_ead_usd": round(float(tr.ead.sum()), 2),
        },
        "inputs": {
            "borrowers": int(len(users)),
            "cards": int(len(cards)),
            "transactions": int(n_tx),
            "labelled_transactions": int(fraud["count"].sum()),
        },  # fmt: skip
        "sector_fraud_rates": fraud_rate.to_dict(),
        "positions": positions,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(sleeve, indent=1) + "\n")

    spec = importlib.util.spec_from_file_location(
        "bm", Path(__file__).with_name("build_manifest.py")
    )
    bm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bm)
    bm.register_dataset(
        "data/portfolio/credit_sleeve.json",
        f"Module B retail/SME credit sleeve: {len(positions)} sector x rating tranches aggregated from "
        f"{len(users)} real borrowers and {n_tx:,} real card transactions",
        "Apache-2.0 (derived aggregates of computingvictor/transactions-fraud-datasets)",
        is_synthetic=False,
        source="https://www.kaggle.com/datasets/computingvictor/transactions-fraud-datasets",
    )
    print(f"{n_tx:,} transactions in {time.time() - t0:.0f}s -> {len(positions)} tranches")
    print(tr.assign(value=(tr.ead * scale).round(0)).to_string(index=False))
    print("fraud rate by sector:", fraud_rate.to_dict())


if __name__ == "__main__":
    main()
