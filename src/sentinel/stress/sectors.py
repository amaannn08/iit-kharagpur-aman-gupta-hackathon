"""GICS sector definitions, non-corporate categories, and normalization logic."""

from typing import Optional

GICS_SECTORS = (
    "Communication Services",
    "Consumer Discretionary",
    "Consumer Staples",
    "Energy",
    "Financials",
    "Health Care",
    "Industrials",
    "Information Technology",
    "Materials",
    "Real Estate",
    "Utilities",
)
NON_CORPORATE = ("Rates", "Government / Cash")
ALIASES = {
    "technology": "Information Technology",
    "tech": "Information Technology",
    "healthcare": "Health Care",
    "consumer cyclical": "Consumer Discretionary",
    "consumer defensive": "Consumer Staples",
    "transportation": "Industrials",
    "basic materials": "Materials",
    "telecommunications": "Communication Services",
    "telecom": "Communication Services",
    "banks": "Financials",
    "financial services": "Financials",
}


def normalize_sector(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    t = s.strip()
    for g in GICS_SECTORS + NON_CORPORATE:
        if t.lower() == g.lower():
            return g
    if t.lower() in ALIASES:
        return ALIASES[t.lower()]
    raise ValueError(f"Unknown sector '{s}'")
