"""Relevance screening for social posts (PRD Section 8.1).

Social records are stored and audited like any other, but a post only becomes actionable if it
is not commercial spam and carries financial context. On a 5,000-tweet real sample, ~10% were
listing / giveaway spam ("Samsung Galaxy S7 32GB Factory Unlocked", "#win a PS4 #giveaway"),
and many brand mentions were unrelated chatter ("Octavia Spencer is coming to Netflix").
"""

import re
from typing import Optional

from sentinel.nlp.entities import FINANCIAL_CONTEXT

SOCIAL_SPAM = re.compile(
    r"\b\d+\s?(?:gb|tb)\b|wi-?fi|unlocked|brand new|free shipping|\bebay\b|giveaway|"
    r"follow (?:me|back)|\b(?:size|colou?r)\s*[:=]|(?:#\w+\s*){5,}|\bsale\b.{0,20}\$\d|"
    r"buy now|shop now|coupon code|promo code|back in stock|do not miss it",
    re.I,
)
CASHTAG = re.compile(r"\$[A-Za-z]{1,5}\b")
# Macro / credit vocabulary that company-news context words miss ("sovereign yields spiking").
MARKET_CONTEXT = re.compile(
    r"\b(yields?|rates?|bps|basis points|spreads?|cds|default(s|ed)?|coupon|bonds?|treasur(y|ies)|"
    r"inflation|central bank|fed|fomc|ecb|boe|boj|currency|forex|fx|[a-z]{3}usd|usd[a-z]{3}|"
    r"recession|gdp|credit|liquidity|sanctions?|tariffs?|oil|crude)\b",
    re.I,
)


def social_block_reason(text: str) -> Optional[str]:
    """Return a block reason for a social post that must not drive actions, else None."""
    if SOCIAL_SPAM.search(text):
        return "SOCIAL_SPAM"
    if not (CASHTAG.search(text) or FINANCIAL_CONTEXT.search(text) or MARKET_CONTEXT.search(text)):
        return "NO_FINANCIAL_CONTEXT"
    return None
