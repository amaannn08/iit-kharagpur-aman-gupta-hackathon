#!/usr/bin/env python3
"""Build data/portfolio/wholesale_real.json: a synthetic book on real S&P 100 issuers.

Inputs (all real, build time):
- SEC XBRL companyfacts (debt, interest, EBIT, assets, equity) in data/raw/real/sec/xbrl/
- data/universe/entities.csv (GICS sectors and canonical names)
- FRED ICE BofA rating-bucket OAS (baseline spreads) in data/raw/real/fred/
- S&P Global Ratings Annual Corporate Default Study (baseline PD by rating)
- FRED DGS5 (5-year Treasury yield for bond yield and duration calibration)

Positions (sizes, tenors, coupons) are a constructed book and flagged is_synthetic: true.
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from sentinel.stress.ratings import rating_bucket  # noqa: E402
from sentinel.stress.sectors import normalize_sector  # noqa: E402

DATA_DIR = REPO_ROOT / "data"
RAW_DIR = DATA_DIR / "raw" / "real"
SEC_XBRL_DIR = RAW_DIR / "sec" / "xbrl"
FRED_DIR = RAW_DIR / "fred"
PORTFOLIO_DIR = DATA_DIR / "portfolio"
OUTPUT_REAL_PATH = PORTFOLIO_DIR / "wholesale_real.json"
OUTPUT_DEMO_PATH = PORTFOLIO_DIR / "demo_book.json"

COVERAGE_TO_RATING: List[Tuple[float, str]] = [
    (8.5, "AAA"),
    (6.5, "AA"),
    (5.5, "A+"),
    (4.25, "A"),
    (3.0, "A-"),
    (2.5, "BBB"),
    (2.25, "BB+"),
    (2.0, "BB"),
    (1.75, "B+"),
    (1.5, "B"),
    (1.25, "B-"),
    (0.8, "CCC"),
    (-1e9, "CC"),
]

# S&P Global Ratings, "Default, Transition, and Recovery: 2020 Annual Global Corporate Default And
# Rating Transition Study" (2021-04-07), Table 3, weighted long-term average annual default rate by
# rating category, 1981-2020 (%): AAA 0.00, AA 0.02, A 0.05, BBB 0.16, BB 0.63, B 3.34, CCC/C 28.30.
PD_SOURCE = (
    "S&P Global Ratings, 2020 Annual Global Corporate Default And Rating Transition Study, "
    "Table 3: weighted long-term average annual default rates by rating, 1981-2020"
)
PD_BY_BUCKET: Dict[str, float] = {
    "AAA": 0.0000,
    "AA": 0.0002,
    "A": 0.0005,
    "BBB": 0.0016,
    "BB": 0.0063,
    "B": 0.0334,
    "CCC": 0.2830,
}

OAS_SERIES: Dict[str, str] = {
    "AAA": "BAMLC0A1CAAA",
    "AA": "BAMLC0A2CAA",
    "A": "BAMLC0A3CA",
    "BBB": "BAMLC0A4CBBB",
    "BB": "BAMLH0A1HYBB",
    "B": "BAMLH0A2HYB",
    "CCC": "BAMLH0A3HYC",
}

LGD_SENIOR_UNSECURED = 0.45  # Basel F-IRB senior unsecured benchmark
TOTAL_BOOK_USD = 500_000_000.0
CASH_USD = 80_000_000.0
CREDIT_BOOK_USD = TOTAL_BOOK_USD - CASH_USD  # $420,000,000.0
NAME_CAP_RATIO = 0.08  # Max 8% of total book ($40,000,000) per issuer


# Facts must come from the issuer's latest annual report; an issuer whose latest 10-K balance
# sheet is older than this is excluded rather than sized on stale numbers.
MIN_FISCAL_YEAR_END = "2024-06-30"

# Consolidated interest of issuers with a captive finance arm includes that arm's funding costs,
# so EBIT / interest says nothing about the industrial credit (Damodaran separates the two).
# There is no standard XBRL flag for this (GM reports its finance receivables under
# company-specific tags), so the S&P 100 industrials with large captive lenders are listed.
CAPTIVE_FINANCE = {"GM": "GM Financial", "F": "Ford Credit", "DE": "John Deere Financial",
                   "CAT": "Cat Financial"}

TOTAL_DEBT_TAGS = (  # tags that already include current maturities
    "DebtLongtermAndShorttermCombinedAmount",
    "LongTermDebtAndCapitalLeaseObligationsIncludingCurrentMaturities",
    "DebtAndCapitalLeaseObligations",
    "LongTermDebt",
)
NONCURRENT_DEBT_TAGS = ("LongTermDebtNoncurrent", "LongTermDebtAndCapitalLeaseObligations")
CURRENT_DEBT_TAGS = ("LongTermDebtCurrent", "DebtCurrent", "LongTermDebtAndCapitalLeaseObligationsCurrent")
INTEREST_TAGS = ("InterestExpense", "InterestExpenseNonoperating", "InterestExpenseDebt",
                 "InterestAndDebtExpense", "InterestPaidNet")  # last resort: cash interest paid
PRETAX_TAGS = (
    "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
    "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments",
)
EQUITY_TAGS = ("StockholdersEquity",
               "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest")


def _annual(facts: Dict[str, Any], tag: str) -> List[Dict[str, Any]]:
    vals = facts.get("facts", {}).get("us-gaap", {}).get(tag, {}).get("units", {}).get("USD", [])
    return [v for v in vals if v.get("form") == "10-K" and v.get("fp") == "FY"]


def fiscal_year_end(facts: Dict[str, Any]) -> Optional[str]:
    """Balance-sheet date of the latest annual report (from Assets)."""
    vals = _annual(facts, "Assets")
    return max(v["end"] for v in vals) if vals else None


def fact_at(facts: Dict[str, Any], tags: Tuple[str, ...], fy_end: str,
            flow: bool = False) -> Tuple[Optional[float], Optional[str]]:
    """First tag with a value for exactly the fiscal year ending fy_end, and the tag used.

    Instant facts must be dated fy_end; flow facts (income statement) must cover ~one year ending
    fy_end. Values from other periods are never used.
    """
    for tag in tags:
        for v in sorted(_annual(facts, tag), key=lambda x: x.get("filed", ""), reverse=True):
            if v["end"] != fy_end:
                continue
            if flow:
                start = v.get("start")
                if not start or not 330 <= (pd.Timestamp(fy_end) - pd.Timestamp(start)).days <= 400:
                    continue
            return float(v["val"]), tag
    return None, None


def issuer_financials(facts: Dict[str, Any]) -> Dict[str, Any]:
    """Debt, EBIT, interest, assets and equity, all from the same (latest) fiscal year."""
    fy = fiscal_year_end(facts)
    if fy is None:
        return {"excluded": "no annual 10-K XBRL balance sheet"}
    if fy < MIN_FISCAL_YEAR_END:
        return {"excluded": f"latest annual balance sheet {fy} is older than {MIN_FISCAL_YEAR_END}"}
    debt, debt_tag = fact_at(facts, TOTAL_DEBT_TAGS, fy)
    if debt is None:
        lt, lt_tag = fact_at(facts, NONCURRENT_DEBT_TAGS, fy)
        cur, cur_tag = fact_at(facts, CURRENT_DEBT_TAGS, fy)
        if lt is not None:
            debt, debt_tag = lt + (cur or 0.0), "+".join(t for t in (lt_tag, cur_tag) if t)
    if not debt:
        return {"excluded": f"no total-debt fact for fiscal year {fy}"}
    ebit, _ = fact_at(facts, ("OperatingIncomeLoss",), fy, flow=True)
    interest, _ = fact_at(facts, INTEREST_TAGS, fy, flow=True)
    if ebit is None and interest:  # no operating-income line (e.g. integrated oil): pretax + interest
        pretax, _ = fact_at(facts, PRETAX_TAGS, fy, flow=True)
        ebit = pretax + interest if pretax is not None else None
    assets, _ = fact_at(facts, ("Assets",), fy)
    equity, _ = fact_at(facts, EQUITY_TAGS, fy)
    return {
        "fiscal_year_end": fy,
        "total_debt": debt,
        "debt_tag": debt_tag,
        "coverage": (ebit / interest) if ebit is not None and interest and interest > 0 else None,
        "equity_to_assets": (equity / assets) if equity is not None and assets and assets > 0 else None,
    }


def fred_last_date(series_name: str) -> str:
    df = pd.read_csv(FRED_DIR / f"{series_name}.csv")
    return str(df[df.iloc[:, 1] != "."].dropna().iloc[-1, 0])


def load_fred_series(series_name: str) -> float:
    path = FRED_DIR / f"{series_name}.csv"
    if not path.exists():
        raise FileNotFoundError(f"FRED series file not found: {path}")
    df = pd.read_csv(path)
    df = df[df.iloc[:, 1] != "."].dropna()
    return float(df.iloc[-1, 1])


def synthetic_rating(cov: Optional[float], equity_to_assets: Optional[float],
                     sector: str) -> Tuple[str, str]:
    """(rating, basis). Interest coverage is meaningless for lenders, whose interest expense is
    a funding cost of operations, so Financials are rated on equity/assets instead."""
    if sector == "Financials":
        e2a = equity_to_assets or 0.0
        return ("A" if e2a >= 0.08 else "BBB" if e2a >= 0.06 else "BB"), "equity_to_assets"
    if cov is None:
        return "BBB", "default: no positive interest-expense fact for the fiscal year"
    for lim, r in COVERAGE_TO_RATING:
        if cov >= lim:
            return r, "interest_coverage"
    return "BBB", "interest_coverage"


def build_wholesale_book() -> Dict[str, Any]:
    PORTFOLIO_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Load universe and S&P 100 constituent metadata
    universe_path = DATA_DIR / "universe" / "entities.csv"
    if universe_path.exists():
        uni_df = pd.read_csv(universe_path)
    else:
        uni_df = pd.read_csv(DATA_DIR / "entity_aliases.csv")
    uni_map = {r["ticker"].upper(): r for _, r in uni_df.iterrows()}

    sp100_path = RAW_DIR / "sec" / "sp100.csv"
    if not sp100_path.exists():
        raise FileNotFoundError(f"S&P 100 constituent table not found: {sp100_path}")
    sp100_df = pd.read_csv(sp100_path)

    # 2. Extract balance-sheet and coverage stats from SEC XBRL
    issuer_records = []
    excluded: Dict[str, str] = {}
    for ticker in sp100_df.ticker.unique():
        t = ticker.upper()
        xbrl_file = SEC_XBRL_DIR / f"{t}.json"
        if not xbrl_file.exists():
            continue
        try:
            facts = json.loads(xbrl_file.read_text(encoding="utf-8"))
        except Exception:
            continue

        if t in CAPTIVE_FINANCE:
            excluded[t] = f"captive finance arm ({CAPTIVE_FINANCE[t]}): interest coverage not meaningful"
            continue
        fin = issuer_financials(facts)
        if "excluded" in fin:
            excluded[t] = fin["excluded"]
            continue
        cov, e2a = fin["coverage"], fin["equity_to_assets"]
        if normalize_sector(uni_map[t]["sector"] if t in uni_map else "") == "Financials":
            cov = None  # lenders are rated on equity/assets; see synthetic_rating

        uni_meta = uni_map.get(t)
        raw_sector = (
            uni_meta["sector"] if uni_meta is not None
            else sp100_df.loc[sp100_df.ticker == ticker, "sector"].values[0]
        )
        canonical_name = (
            uni_meta["canonical_name"] if uni_meta is not None
            else sp100_df.loc[sp100_df.ticker == ticker, "name"].values[0]
        )

        sector = normalize_sector(raw_sector)
        synth_rat, rating_basis = synthetic_rating(cov, e2a, sector)

        issuer_records.append({
            "ticker": t,
            "name": canonical_name,
            "sector": sector,
            "total_debt": fin["total_debt"],
            "debt_tag": fin["debt_tag"],
            "fiscal_year_end": fin["fiscal_year_end"],
            "coverage": cov,
            "equity_to_assets": e2a,
            "rating": synth_rat,
            "rating_basis": rating_basis,
            "rating_bucket": rating_bucket(synth_rat),
        })

    df = pd.DataFrame(issuer_records)

    # 3. Rule-based selection: 2 largest debt issuers per GICS sector
    df_sorted = df.sort_values(["sector", "total_debt"], ascending=[True, False]).copy()
    df_sorted["sector_rank"] = df_sorted.groupby("sector").cumcount() + 1
    picks = df_sorted[df_sorted["sector_rank"] <= 2].copy().reset_index(drop=True)

    # 4. Exposure sizing: w_i proportional to sqrt(total_debt_i), strictly capped at 8% of total book ($40M)
    max_single_exposure = round(NAME_CAP_RATIO * TOTAL_BOOK_USD, 2)  # $40,000,000.00
    raw_w = np.sqrt(picks.total_debt.values)
    allocated = np.zeros(len(picks))
    remaining_budget = CREDIT_BOOK_USD
    active = np.ones(len(picks), dtype=bool)

    while active.any():
        w = raw_w * active
        if w.sum() == 0:
            break
        w = w / w.sum()
        proposal = w * remaining_budget
        capped = (proposal >= max_single_exposure) & active
        if not capped.any():
            allocated[active] = proposal[active]
            break
        allocated[capped] = max_single_exposure
        remaining_budget -= max_single_exposure * capped.sum()
        active[capped] = False

    picks["allocated_exposure"] = np.round(allocated, 2)
    # Adjust a non-capped pick for exact penny rounding to $420,000,000.0
    exposure_diff = round(CREDIT_BOOK_USD - picks["allocated_exposure"].sum(), 2)
    non_capped_indices = np.where(picks["allocated_exposure"].values < max_single_exposure)[0]
    if len(non_capped_indices) > 0:
        picks.loc[non_capped_indices[-1], "allocated_exposure"] += exposure_diff

    # 5. Baseline market parameters from FRED
    oas_bps_by_bucket = {b: round(load_fred_series(s) * 100, 1) for b, s in OAS_SERIES.items()}
    treasury_5y_pct = load_fred_series("DGS5")  # in percent, e.g. 4.99

    # 6. Build positions
    positions = []
    total_loans = 0.0
    total_bonds = 0.0

    pos_idx = 1
    for _, row in picks.iterrows():
        t = row["ticker"]
        name = row["name"]
        sec = row["sector"]
        rat = row["rating"]
        bucket = row["rating_bucket"]
        exp = float(row["allocated_exposure"])
        rank = int(row["sector_rank"])

        # Split: Rank 1 gets 60% loan / 40% bond; Rank 2 gets 40% loan / 60% bond
        loan_share = 0.60 if rank == 1 else 0.40

        loan_exp = round(exp * loan_share, 2)
        bond_exp = round(exp - loan_exp, 2)

        # Tenors: IG 5y, HY 3y
        is_ig = bucket in ("AAA", "AA", "A", "BBB")
        tenor_years = 5.0 if is_ig else 3.0
        mat_year = 2026 + int(tenor_years)
        maturity_date = f"{mat_year:04d}-03-01"

        # Loan Position
        positions.append({
            "position_id": f"L-{pos_idx:03d}",
            "asset_class": "loan",
            "entity_id": t,
            "counterparty_name": name,
            "sector": sec,
            "currency": "USD",
            "market_value": loan_exp,
            "ead": loan_exp,
            "baseline_pd": PD_BY_BUCKET.get(bucket, 0.006),
            "lgd": LGD_SENIOR_UNSECURED,
            "rating": rat,
            "sleeve": "wholesale",
            "maturity_date": maturity_date,
        })
        total_loans += loan_exp

        # Bond Position
        spread_bps = oas_bps_by_bucket.get(bucket, 150.0)
        yield_val = round((treasury_5y_pct + spread_bps / 100.0) / 100.0, 4)
        duration = round((1.0 - (1.0 + yield_val) ** (-tenor_years)) / yield_val, 2)

        positions.append({
            "position_id": f"B-{pos_idx:03d}",
            "asset_class": "bond",
            "entity_id": t,
            "counterparty_name": name,
            "sector": sec,
            "currency": "USD",
            "market_value": bond_exp,
            "notional": bond_exp,
            "coupon": yield_val,
            "yield": yield_val,
            "spread_bps": spread_bps,
            "modified_duration": duration,
            "rating": rat,
            "sleeve": "wholesale",
            "maturity_date": maturity_date,
        })
        total_bonds += bond_exp
        pos_idx += 1

    # Standard rates swaps and cash reserves
    positions.extend([
        {
            "position_id": "SWAP-001",
            "asset_class": "swap",
            "entity_id": "MACRO",
            "counterparty_name": "Global Clearing House",
            "sector": "Rates",
            "currency": "USD",
            "market_value": 0.0,
            "notional": 75000000.0,
            "pay_receive": "receive_fixed",
            "fixed_rate": 0.041,
            "floating_benchmark": "SOFR",
            "signed_dv01": 36000.0,
            "maturity_years": 5.0,
            "sleeve": "wholesale",
            "maturity_date": "2031-03-01",
        },
        {
            "position_id": "SWAP-002",
            "asset_class": "swap",
            "entity_id": "MACRO",
            "counterparty_name": "Global Clearing House",
            "sector": "Rates",
            "currency": "USD",
            "market_value": 0.0,
            "notional": 75000000.0,
            "pay_receive": "pay_fixed",
            "fixed_rate": 0.0425,
            "floating_benchmark": "SOFR",
            "signed_dv01": -34500.0,
            "maturity_years": 7.0,
            "sleeve": "wholesale",
            "maturity_date": "2033-03-01",
        },
        {
            "position_id": "CASH-001",
            "asset_class": "cash",
            "entity_id": "TREASURY",
            "counterparty_name": "Federal Reserve Overnight Facility",
            "sector": "Government / Cash",
            "currency": "USD",
            "market_value": CASH_USD,
            "notional": CASH_USD,
            "yield": 0.045,
            "modified_duration": 0.0,
            "rating": "AAA",
            "sleeve": "wholesale",
            "maturity_date": "2026-03-02",
        },
    ])

    summary = {
        "total_book_value_usd": round(total_loans + total_bonds + CASH_USD, 2),
        "corporate_loans_value_usd": round(total_loans, 2),
        "corporate_bonds_value_usd": round(total_bonds, 2),
        "cash_reserves_usd": round(CASH_USD, 2),
        "interest_rate_swaps_mtm_usd": 0.0,
        "interest_rate_swaps_gross_notional_usd": 150000000.0,
    }

    out = {
        "portfolio_name": "Wholesale book on real S&P 100 issuers (synthetic positions)",
        "profile": "real_issuers",
        "is_synthetic": True,
        "provenance": {
            "issuers": "S&P 100 constituents (Wikipedia, CC BY-SA 4.0)",
            "financials": "SEC EDGAR XBRL companyfacts (debt, interest, EBIT, assets, equity)",
            "pd": PD_SOURCE,
            "spreads": "FRED ICE BofA OAS rating-bucket series (latest derived)",
            "lgd": "Basel F-IRB senior unsecured benchmark (0.45)",
            "benchmark_rates": "FRED DGS5 (5-year Treasury yield)",
        },
        "selection_rule": "2 largest debt issuers per GICS sector among S&P 100 constituents",
        "base_currency": "USD",
        "valuation_date": fred_last_date("DGS5"),
        "issuers": [
            {k: (None if isinstance(v, float) and v != v  # NaN -> null (valid JSON)
                 else round(v, 3) if isinstance(v, float) and k != "total_debt" else v)
             for k, v in r.items() if k != "allocated_exposure"}
            for r in picks.drop(columns=["sector_rank"]).to_dict("records")
        ],
        "excluded_issuers": dict(sorted(excluded.items())),
        "summary": summary,
        "positions": positions,
    }

    OUTPUT_REAL_PATH.write_text(json.dumps(out, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT_REAL_PATH} with {len(picks)} issuers, {len(positions)} positions, total=${summary['total_book_value_usd']:,.2f}")

    # Also ensure demo_book.json exists (profile: synthetic_demo)
    source_demo_path = DATA_DIR / "wholesale_positions.json"
    if source_demo_path.exists():
        demo_data = json.loads(source_demo_path.read_text(encoding="utf-8"))
        demo_data["profile"] = "synthetic_demo"
        OUTPUT_DEMO_PATH.write_text(json.dumps(demo_data, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {OUTPUT_DEMO_PATH} (profile: synthetic_demo)")

    # Ensure fictional graph is copied to graph_edges_demo.csv
    demo_graph_src = DATA_DIR / "graph_edges.csv"
    demo_graph_dst = DATA_DIR / "graph_edges_demo.csv"
    if demo_graph_src.exists() and not demo_graph_dst.exists():
        demo_graph_dst.write_bytes(demo_graph_src.read_bytes())
        print(f"Wrote {demo_graph_dst}")

    # Register in manifest
    from scripts.data.build_manifest import register_dataset

    register_dataset(
        "data/portfolio/wholesale_real.json",
        description="Synthetic wholesale book constructed on real S&P 100 debt issuers",
        license_name="CC-BY-4.0",
        is_synthetic=True,
        derived_from=["data/raw/real/sec/xbrl", "data/raw/real/fred", "data/universe/entities.csv"],
    )
    register_dataset(
        "data/portfolio/demo_book.json",
        description="Fictional wholesale book for synthetic demo scenarios",
        license_name="MIT",
        is_synthetic=True,
        derived_from=[],
    )
    register_dataset(
        "data/graph_edges_demo.csv",
        description="Synthetic demo supply-chain and counterparty contagion graph",
        license_name="MIT",
        is_synthetic=True,
        derived_from=[],
    )

    return out


if __name__ == "__main__":
    build_wholesale_book()
