"""Rating-tier shock multipliers and baseline PDs.

Multipliers scale index spread moves (and the PD derived from them) by rating. Anchors:
the HY index (HYG: ~50% BB, ~38% B, ~12% CCC) = 1.0; the IG index (LQD: ~5% AA, ~45% A,
~50% BBB) = the measured LQD/HYG spread-move ratio (median 0.41 over the stress windows in
data/market/stress_windows.json). tests/test_stress_ratings.py checks both anchors.
"""

import re
from typing import Mapping, Optional

RATING_SPREAD_MULTIPLIER = {
    "AAA": 0.20,
    "AA": 0.28,
    "A": 0.36,
    "BBB": 0.55,
    "BB": 0.75,
    "B": 1.10,
    "CCC": 1.90,
}
UNRATED_BUCKET = "BB"  # conservative default for NR / unknown
IG_INDEX_MIX = {"AA": 0.05, "A": 0.45, "BBB": 0.50}
HY_INDEX_MIX = {"BB": 0.50, "B": 0.38, "CCC": 0.12}


def rating_bucket(rating: Optional[str]) -> str:
    """'BB-' -> 'BB', 'A+' -> 'A', 'CC'/'C'/'D' -> 'CCC', AAA-cash -> 'AAA', else unrated."""
    if not rating:
        return UNRATED_BUCKET
    r = re.sub(r"[+-]", "", rating.strip().upper())
    if r in ("CC", "C", "D", "SD"):
        return "CCC"
    return r if r in RATING_SPREAD_MULTIPLIER else UNRATED_BUCKET


def spread_multiplier(rating: Optional[str]) -> float:
    return RATING_SPREAD_MULTIPLIER[rating_bucket(rating)]


def index_multiplier(mix: Mapping[str, float]) -> float:
    return sum(w * RATING_SPREAD_MULTIPLIER[b] for b, w in mix.items())
