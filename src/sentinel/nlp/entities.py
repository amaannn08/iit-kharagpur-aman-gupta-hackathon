"""Entity recognition and resolution engine conforming to PRD Section 7.1.

Universe: data/universe/entities.csv (real S&P 500 constituents + flagged synthetic demo
issuers, built by scripts/data/build_universe.py). Falls back to data/entity_aliases.csv.

Resolution rules, each producing a character span that equals text[start:end]:
1. Cashtags ($AAPL) and exchange notation ("(NYSE: F)", "(TSLA)").
2. Bare upper-case tickers of 3+ letters (IBM, AMD) outside a stop-list of common acronyms.
3. Alias n-grams, longest first. Single-word aliases must be capitalized; aliases flagged
   ambiguous ("Apple", "Target", "Moody's") also require financial context in the text.
4. Macro / central-bank fallback when no company is found.
"""

import csv
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union

from sentinel.config import settings
from sentinel.contracts.signals import EntityReference, EvidenceSpan


@dataclass
class KnownEntity:
    ticker: str
    canonical_name: str
    sector: str
    aliases: List[str]
    ambiguous_aliases: Set[str] = field(default_factory=set)
    is_synthetic: bool = False


FINANCIAL_CONTEXT = re.compile(
    r"\b(stocks?|shares?|earnings|revenues?|quarter(ly)?|profits?|ceo|cfo|nasdaq|nyse|"
    r"investors?|analysts?|guidance|dividends?|sales|deal|markets?|price|debt|bonds?|loans?|"
    r"downgrade[ds]?|upgrade[ds]?|valuation|margins?|equit(y|ies)|wall street|ratings?|"
    r"results|eps|buybacks?|acquisitions?|merger|ipo|outlook|forecast)\b",
    re.I,
)
CASHTAG = re.compile(r"\$([A-Za-z]{1,5}(?:[.\-][A-Za-z])?)\b")
EXCHANGE_TICKER = re.compile(
    r"\((?:(?:NYSE|NASDAQ|Nasdaq|NYSEARCA|AMEX|NYSE American)\s*:\s*)?([A-Z]{1,5}(?:[.\-][A-Z])?)\)"
)
BARE_TICKER = re.compile(r"\b[A-Z]{3,5}\b")
# Upper-case tokens that are common acronyms, not tickers, in financial text.
STOP_TICKERS = {
    "ALL", "ARE", "BIG", "CEO", "CFO", "COO", "USA", "EPS", "FDA", "SEC", "GDP", "IPO", "ETF",
    "YOY", "NOW", "KEY", "LOW", "CAT", "FED", "ECB", "IMF", "CPI", "PPI", "AI", "EV", "ESG",
    "NYSE", "AMEX", "OPEC", "NATO", "FTC", "DOJ", "LLC", "INC", "LTD", "PLC", "USD",
    "EUR", "GBP", "JPY", "CNY", "API", "IT", "ON", "ONE", "HAS", "FOR", "NEW", "TOP", "BUY",
    "SELL", "HOLD", "Q1", "Q2", "Q3", "Q4", "UK", "EU", "US", "UN", "WHO", "ATM", "CDC",
    "FOMC", "SPAC", "NFT", "GPU", "CPU", "SUV", "TV", "PC", "VIX", "SPY", "DJIA", "CNBC",
    "MORE", "CASH", "PEAK", "WELL", "BALL", "FAST", "LIFE", "GOOD", "TECH", "REAL", "PLAY",
    "PEG", "ROE", "ROI", "ROA", "EBIT", "YTD", "CAGR", "NAV", "MSCI", "NASDAQ", "FTSE", "RAFI",
}  # fmt: skip
# Rating agencies and exchanges are usually the *agent* or *venue* in a headline
# ("downgraded by Moody's", "S&P Global Ratings lowers ...", "Nasdaq-listed"), not its subject.
AGENT_TICKERS = {"MCO", "SPGI", "NDAQ", "ICE", "CME", "MSCI"}
AGENT_AFTER = re.compile(
    r"^(?:'s)?[\s-]*(ratings?\b|investors service|global ratings|-?listed|composite|100\b|"
    r"downgrade|upgrade|cut|lower|raise|affirm|revis|assign|place|rate[sd]?\b|index|exchange)",
    re.I,
)
AGENT_BEFORE = re.compile(r"\b(by|from|on|at|per|according to)\s+(the\s+)?$", re.I)
# Banks/brokers appear as the analyst rather than the subject ("Wells Fargo maintains
# Overweight on APA", "after a Morgan Stanley analyst cut ...").
BROKER_TICKERS = {"MS", "GS", "WFC", "JPM", "C", "BAC", "RJF", "SCHW"}
BROKER_AFTER = re.compile(
    r"^\s+(analysts?\b|strategists?\b|economists?\b|maintains\b|reiterates\b|initiates\b|"
    r"upgrades\b|downgrades\b|raises .{0,30}price target|lowers .{0,30}price target|"
    r"(has|keeps) an? \w+ rating|rating\b)",
    re.I,
)
# Fund sponsors are not the subject of articles about their ETFs.
SPONSOR_TICKERS = {"IVZ", "BLK", "STT", "SCHW", "BEN", "TROW"}
SPONSOR_AFTER = re.compile(r"^[\w\s&.\-]{0,40}\b(ETF|Fund|Trust)\b")
PHRASE_EXCLUSIONS = {
    "TGT": (re.compile(r"\bprice\s*$", re.I), None),  # "price target"
    "DD": (None, re.compile(r"^\s+analysis\b", re.I)),  # "DuPont analysis"
}
TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9&'’\-.]*")
PUNCT = re.compile(r"[.,:;!?'’]*$")
TRAILING = re.compile(r"(?:'s|’s|\.com)?[.,:;!?'’]*$")
MACRO_TERMS = [
    "federal reserve", "central bank", "treasury yield", "treasury yields", "fomc",
    "european central bank", "ecb", "macro", "sovereign bond",
]  # fmt: skip


def _universe_path() -> Path:
    path = settings.data_dir / "universe" / "entities.csv"
    return path if path.exists() else settings.data_dir / "entity_aliases.csv"


class EntityLinker:
    """Extracts and resolves entity references from financial texts."""

    def __init__(self, alias_file: Optional[Union[str, Path]] = None) -> None:
        self.entities: Dict[str, KnownEntity] = {}
        self.alias_lookup: Dict[str, Tuple[str, str]] = {}  # lower alias -> (ticker, alias)
        self.max_alias_tokens = 1
        self._load(Path(alias_file) if alias_file else _universe_path())

    def _load(self, path: Path) -> None:
        if not path.exists():
            return
        with open(path, mode="r", encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                ticker = row["ticker"].strip().upper()
                canonical = row["canonical_name"].strip()
                if "ambiguous_aliases" in row:  # universe format
                    aliases = [a for a in row["aliases"].split("|") if a]
                    ambiguous = {a for a in row["ambiguous_aliases"].split("|") if a}
                    synthetic = row.get("is_synthetic", "false").lower() == "true"
                else:  # legacy data/entity_aliases.csv format
                    aliases = [a.strip() for a in row.get("aliases", "").split(",") if a.strip()]
                    aliases.append(canonical)
                    flag = row.get("is_ambiguous", "false").strip().lower() == "true"
                    ambiguous = set(aliases) if flag else set()
                    synthetic = False
                entity = KnownEntity(
                    ticker=ticker,
                    canonical_name=canonical,
                    sector=row.get("sector", "").strip(),
                    aliases=aliases,
                    ambiguous_aliases=ambiguous,
                    is_synthetic=synthetic,
                )
                self.entities[ticker] = entity
                for alias in aliases:
                    if alias.upper() == ticker and len(alias) <= 5:
                        continue  # bare tickers are handled by the ticker rules
                    self.alias_lookup.setdefault(alias.lower(), (ticker, alias))
                    self.max_alias_tokens = max(self.max_alias_tokens, len(alias.split()))

    def _ref(self, ticker: str) -> EntityReference:
        ke = self.entities[ticker]
        return EntityReference(
            name=ke.canonical_name, ticker=ke.ticker, scope="company", resolved=True,
            sector=ke.sector or None,
        )  # fmt: skip

    def _ticker_in_universe(self, raw: str) -> Optional[str]:
        t = raw.upper().replace(".", "-")
        return t if t in self.entities else None

    def find_companies(self, text: str) -> Dict[str, List[EvidenceSpan]]:
        """Return {ticker: [spans]} for every company mention, in order of first appearance."""
        found: Dict[str, List[EvidenceSpan]] = {}

        def add(ticker: str, start: int, end: int) -> None:
            spans = found.setdefault(ticker, [])
            overlaps = any(start < s.end and s.start < end for s in spans)  # "$APEX" vs "APEX"
            if len(spans) < 3 and not overlaps:
                spans.append(EvidenceSpan(start=start, end=end, text=text[start:end]))

        for m in CASHTAG.finditer(text):
            if t := self._ticker_in_universe(m.group(1)):
                add(t, m.start(), m.end())
        for m in EXCHANGE_TICKER.finditer(text):
            if t := self._ticker_in_universe(m.group(1)):
                add(t, m.start(1), m.end(1))

        letters = [c for c in text if c.isalpha()]
        mostly_upper = letters and sum(c.isupper() for c in letters) / len(letters) > 0.6
        if not mostly_upper:  # all-caps headlines ("FED HIKES RATES") are not ticker lists
            for m in BARE_TICKER.finditer(text):
                if m.group() not in STOP_TICKERS and m.group() in self.entities:
                    add(m.group(), m.start(), m.end())

        has_context = bool(FINANCIAL_CONTEXT.search(text))
        tokens = [(m.start(), m.end()) for m in TOKEN.finditer(text)]
        i = 0
        while i < len(tokens):
            matched = 0
            for n in range(min(self.max_alias_tokens, len(tokens) - i), 0, -1):
                start, end = tokens[i][0], tokens[i + n - 1][1]
                span = text[start:end]
                # Official names can contain the possessive ("Moody's", "McDonald's"), so try
                # the span with only punctuation removed before dropping 's / .com.
                hit, stripped = None, span
                for candidate in (PUNCT.sub("", span), TRAILING.sub("", span)):
                    if hit := self.alias_lookup.get(candidate.lower()):
                        stripped = candidate
                        break
                if not hit:
                    continue
                ticker, alias = hit
                ke = self.entities[ticker]
                if " " not in alias and not stripped[:1].isupper():
                    continue  # single-word aliases must be capitalized ("apple" is fruit)
                if alias in ke.ambiguous_aliases and not has_context:
                    continue
                after = text[start + len(stripped) :]
                before = text[max(0, start - 20) : start]
                exclude_before, exclude_after = PHRASE_EXCLUSIONS.get(ticker, (None, None))
                if (
                    (
                        ticker in AGENT_TICKERS
                        and (AGENT_AFTER.match(after) or AGENT_BEFORE.search(before))
                    )
                    or (ticker in BROKER_TICKERS and BROKER_AFTER.match(after))
                    or (ticker in SPONSOR_TICKERS and SPONSOR_AFTER.match(after))
                    or (exclude_before and exclude_before.search(before))
                    or (exclude_after and exclude_after.match(after))
                ):
                    matched = n  # consume the tokens so a shorter alias cannot re-match them
                    break
                add(ticker, start, start + len(stripped))
                matched = n
                break
            i += matched or 1

        return dict(sorted(found.items(), key=lambda kv: kv[1][0].start))

    def _macro(self, text: str) -> Optional[Tuple[EntityReference, List[EvidenceSpan]]]:
        lower = text.lower()
        for term in MACRO_TERMS:
            m = re.search(rf"\b{re.escape(term)}\b", lower)
            if m:
                ref = EntityReference(
                    name="Macro / Central Bank", ticker=None, scope="macro", resolved=True
                )
                return ref, [
                    EvidenceSpan(start=m.start(), end=m.end(), text=text[m.start() : m.end()])
                ]
        return None

    def resolve_all(
        self, text: str, hint_entity_id: Optional[str] = None
    ) -> List[Tuple[EntityReference, List[EvidenceSpan]]]:
        """Every resolved company (PRD 6.2: one signal per entity/event association).

        Falls back to the macro entity, then a valid hint (without fabricated spans), then a
        single unresolved reference.
        """
        companies = self.find_companies(text)
        if companies:
            return [(self._ref(t), spans) for t, spans in companies.items()]
        if macro := self._macro(text):
            return [macro]
        if hint_entity_id:
            hint = hint_entity_id.upper()
            if hint in ("MACRO", "SYSTEMIC"):
                return [
                    (EntityReference(name="Macro / Central Bank", ticker=None, scope="macro"), [])
                ]
            if hint in self.entities:
                return [(self._ref(hint), [])]
        unknown = EntityReference(
            name="Unknown Entity", ticker=None, scope="unknown", resolved=False
        )
        return [(unknown, [])]

    def resolve(
        self, text: str, hint_entity_id: Optional[str] = None
    ) -> Tuple[EntityReference, List[EvidenceSpan]]:
        """Primary (first-mentioned) entity, kept for single-entity callers."""
        return self.resolve_all(text, hint_entity_id)[0]
