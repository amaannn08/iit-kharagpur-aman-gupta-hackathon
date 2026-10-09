#!/usr/bin/env python3
"""Build the entity universe: real S&P 500 constituents + the synthetic demo issuers.

Inputs : data/raw/real/sec/sp500.csv, data/raw/real/sec/company_tickers.json (fetch_real.py),
         data/entity_aliases.csv (curated aliases for the demo universe)
Output : data/universe/entities.csv
         ticker, canonical_name, sector, aliases (|-separated), ambiguous_aliases, is_synthetic, cik

The S&P 500 is used instead of all ~10k SEC registrants: on real Polygon news the full SEC
name list dropped linking precision from 0.97 to 0.78 because of common-word company names.
"""

import csv
import importlib.util
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RAW_SEC = REPO_ROOT / "data" / "raw" / "real" / "sec"
OUT = REPO_ROOT / "data" / "universe" / "entities.csv"
LEGACY = REPO_ROOT / "data" / "entity_aliases.csv"

# Fictional issuers used by the synthetic demo scenarios and the synthetic portfolio.
SYNTHETIC_TICKERS = {
    "APEX", "GLOG", "QSEM", "MFIN", "SLEN", "CSEC", "BHPH", "TSTEL",
    "MEDX", "VAUTO", "FSBK", "OMNI", "LITH", "DCLD", "PTEL", "AERO",
}  # fmt: skip

# Widely used short names / brands that differ from the legal constituent name.
BRANDS = {
    "META": ["Facebook", "Meta Platforms", "Instagram", "WhatsApp"],
    "GOOGL": ["Google", "Alphabet", "YouTube"],
    "AMZN": ["Amazon", "AWS"],
    "BRK-B": ["Berkshire Hathaway", "Berkshire"],
    "JPM": ["JPMorgan", "JP Morgan", "JPMorgan Chase", "Chase"],
    "KO": ["Coca-Cola", "Coke"],
    "WMT": ["Walmart"],
    "DIS": ["Disney", "Walt Disney"],
    "NFLX": ["Netflix"],
    "TSLA": ["Tesla"],
    "F": ["Ford", "Ford Motor"],
    "GM": ["General Motors"],
    "NKE": ["Nike"],
    "SBUX": ["Starbucks"],
    "INTC": ["Intel"],
    "GS": ["Goldman Sachs", "Goldman"],
    "MS": ["Morgan Stanley"],
    "BAC": ["Bank of America", "BofA"],
    "C": ["Citigroup", "Citi"],
    "WFC": ["Wells Fargo"],
    "XOM": ["Exxon", "ExxonMobil", "Exxon Mobil"],
    "CVX": ["Chevron"],
    "MSFT": ["Microsoft"],
    "AAPL": ["Apple", "iPhone"],
    "NVDA": ["Nvidia", "NVIDIA"],
    "PFE": ["Pfizer"],
    "BA": ["Boeing"],
    "MCD": ["McDonald's", "McDonalds"],
    "CRM": ["Salesforce"],
    "AMD": ["Advanced Micro Devices"],
    "IBM": ["International Business Machines"],
    "CMCSA": ["Comcast", "NBCUniversal"],
    "PG": ["Procter & Gamble", "P&G"],
    "JNJ": ["Johnson & Johnson", "J&J"],
    "UNH": ["UnitedHealth", "UnitedHealth Group"],
    "V": ["Visa"],
    "MA": ["Mastercard"],
    "PYPL": ["PayPal"],
    "TGT": ["Target"],
    "ORCL": ["Oracle"],
    "CSCO": ["Cisco"],
    "FDX": ["FedEx"],
    "UPS": ["UPS"],
    "LMT": ["Lockheed Martin", "Lockheed"],
    "CAT": ["Caterpillar"],
    "COST": ["Costco"],
    "HD": ["Home Depot"],
    "LOW": ["Lowe's", "Lowes"],
    "T": ["AT&T"],
    "VZ": ["Verizon"],
    "BLK": ["BlackRock"],
    "ADBE": ["Adobe"],
}

# Single words that are ordinary English, places, or institutions that headlines mention in
# passing ("downgraded by Moody's", "Nasdaq-listed"): require financial context to link.
AMBIGUOUS_ALIASES = {
    "Apple", "Target", "Ford", "Chase", "Visa", "Oracle", "Meta", "Gap", "Block", "Shell",
    "Coke", "Ball", "Citi", "Amazon", "Intel", "Cisco", "Delta", "Southern", "Everest",
    "Flex", "Dover", "Hartford", "Waters", "Lilly", "Mosaic", "Booking", "Coherent",
    "Moody's", "Nasdaq", "Chubb", "Loews", "Masco", "Corning",
}  # fmt: skip

# Cleaned names too generic to use at all ("News Corp" -> "News", "Dow Inc." -> "Dow", which
# headlines use for the Dow Jones index): keep the fuller legal form instead.
# "Nasdaq" in headlines is almost always the index or the exchange venue, not Nasdaq, Inc.
GENERIC_REPLACEMENTS = {
    "News": "News Corp",
    "Fox": "Fox Corporation",
    "Dow": "Dow Inc",
    "Nasdaq": "Nasdaq Inc",
}

SUFFIX = re.compile(
    r"[,.]?\s+(inc|incorporated|corp|corporation|co|company|holdings?|group|plc|ltd|limited|"
    r"n\.?v|s\.?a|the|class [a-c]|common stock|& co)\.?$",
    re.I,
)


def clean_name(name: str) -> str:
    """'Alphabet Inc. (Class A)' -> 'Alphabet'; 'APPLE INC /CA/' -> 'APPLE'."""
    n = re.sub(r"\s*\([^)]*\)", "", name)
    n = re.sub(r"\s*/[A-Z]{2}/?$", "", n).strip()
    prev = None
    while prev != n:
        prev, n = n, SUFFIX.sub("", n).strip(" ,.")
    return n


def is_ambiguous(alias: str) -> bool:
    return alias in AMBIGUOUS_ALIASES or (" " not in alias and len(alias) <= 3)


def build() -> list:
    if not (RAW_SEC / "sp500.csv").exists():
        sys.exit("data/raw/real/sec/sp500.csv missing: run scripts/data/fetch_real.py --only sec")
    sec = json.loads((RAW_SEC / "company_tickers.json").read_text())
    cik = {v["ticker"].replace(".", "-"): v["cik_str"] for v in sec.values()}

    rows = {}
    with open(RAW_SEC / "sp500.csv", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            t = r["ticker"].strip()
            cleaned = clean_name(r["name"])
            aliases = {GENERIC_REPLACEMENTS.get(cleaned, cleaned), *BRANDS.get(t, [])}
            rows[t] = {
                "ticker": t,
                "canonical_name": r["name"].strip(),
                "sector": r["sector"].strip(),
                "aliases": aliases,
                "is_synthetic": False,
                "cik": cik.get(t, ""),
            }

    with open(LEGACY, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            t = r["ticker"].strip().upper()
            legacy_aliases = {a.strip() for a in r.get("aliases", "").split(",") if a.strip()}
            legacy_aliases.add(r["canonical_name"].strip())
            if t in rows:  # real constituent: keep real name, merge curated aliases
                rows[t]["aliases"] |= {a for a in legacy_aliases if a.upper() != t}
                continue
            if t not in SYNTHETIC_TICKERS:
                continue
            rows[t] = {
                "ticker": t,
                "canonical_name": r["canonical_name"].strip(),
                "sector": r.get("sector", "").strip(),
                "aliases": legacy_aliases,
                "is_synthetic": True,
                "cik": "",
            }

    # Each alias gets exactly one owner (share classes such as GOOG/GOOGL both clean to
    # "Alphabet"): prefer the ticker whose curated BRANDS list contains it, else the first.
    owner = {}
    for t in sorted(rows):
        for a in rows[t]["aliases"]:
            key = a.lower()
            if key not in owner or a in BRANDS.get(t, []):
                owner[key] = t
    for t in rows:
        rows[t]["aliases"] = {a for a in rows[t]["aliases"] if owner[a.lower()] == t}

    out = []
    for t in sorted(rows):
        r = rows[t]
        aliases = sorted(a for a in r["aliases"] if len(a) >= 2)
        out.append(
            {
                "ticker": t,
                "canonical_name": r["canonical_name"],
                "sector": r["sector"],
                "aliases": "|".join(aliases),
                "ambiguous_aliases": "|".join(a for a in aliases if is_ambiguous(a)),
                "is_synthetic": str(r["is_synthetic"]).lower(),
                "cik": r["cik"],
            }
        )
    return out


if __name__ == "__main__":
    rows = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    spec = importlib.util.spec_from_file_location(
        "build_manifest", Path(__file__).with_name("build_manifest.py")
    )
    build_manifest = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(build_manifest)
    build_manifest.register_dataset(
        str(OUT.relative_to(REPO_ROOT)),
        "Entity universe: real S&P 500 constituents (SEC CIKs) plus the 16 fictional demo "
        "issuers, flagged per row in is_synthetic",
        "CC BY-SA 4.0 (Wikipedia S&P 500 constituent list) + US public domain (SEC tickers)",
        is_synthetic=False,
        source="https://en.wikipedia.org/wiki/List_of_S%26P_500_companies; "
        "https://www.sec.gov/files/company_tickers.json",
        derived_from=["data/entity_aliases.csv"],
        columns=list(rows[0]),
    )
    n_syn = sum(r["is_synthetic"] == "true" for r in rows)
    print(f"wrote {OUT.relative_to(REPO_ROOT)}: {len(rows)} entities ({n_syn} synthetic)")
