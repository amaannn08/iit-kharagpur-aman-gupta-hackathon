"""Entity recognition and resolution engine conforming to PRD Section 7.1."""

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from sentinel.contracts.signals import EntityReference, EvidenceSpan


@dataclass
class KnownEntity:
    ticker: str
    canonical_name: str
    sector: str
    cashtags: List[str]
    aliases: List[str]
    is_ambiguous: bool


# Disambiguation context keywords required when matching ambiguous terms (e.g., Apple, CAT)
FINANCIAL_CONTEXT_KEYWORDS = {
    "stock",
    "shares",
    "earnings",
    "quarterly",
    "revenue",
    "profit",
    "guidance",
    "ceo",
    "cfo",
    "nasdaq",
    "nyse",
    "investor",
    "dividend",
    "analyst",
    "downgrade",
    "upgrade",
    "valuation",
    "debt",
    "bond",
    "loan",
    "margin",
    "equity",
    "equities",
    "wall street",
    "sales",
}


class EntityLinker:
    """Extracts and resolves entity references from financial texts."""

    def __init__(self, alias_file: Optional[Union[str, Path]] = None) -> None:
        self.entities: Dict[str, KnownEntity] = {}
        # Mapping from lowercase token/alias to ticker
        self.alias_lookup: Dict[str, str] = {}
        self.cashtag_lookup: Dict[str, str] = {}

        if alias_file is None:
            alias_file = Path("data/entity_aliases.csv")
        self._load_aliases(Path(alias_file))

    def _load_aliases(self, path: Path) -> None:
        if not path.exists():
            return

        with open(path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                ticker = row["ticker"].strip().upper()
                canonical = row["canonical_name"].strip()
                sector = row.get("sector", "Unknown").strip()
                is_ambiguous = row.get("is_ambiguous", "false").strip().lower() == "true"

                raw_cashtags = row.get("cashtags", "").split(",")
                cashtags = [c.strip().upper() for c in raw_cashtags if c.strip()]
                raw_aliases = row.get("aliases", "").split(",")
                aliases = [a.strip() for a in raw_aliases if a.strip()]

                entity = KnownEntity(
                    ticker=ticker,
                    canonical_name=canonical,
                    sector=sector,
                    cashtags=cashtags,
                    aliases=aliases,
                    is_ambiguous=is_ambiguous,
                )
                self.entities[ticker] = entity

                # Register cashtags (e.g. $APEX -> APEX)
                for ct in cashtags:
                    self.cashtag_lookup[ct.upper()] = ticker

                # Register canonical name
                self.alias_lookup[canonical.lower()] = ticker

                # Register alias strings
                for alias in aliases:
                    self.alias_lookup[alias.lower()] = ticker

    def resolve(
        self,
        text: str,
        hint_entity_id: Optional[str] = None,
    ) -> Tuple[EntityReference, List[EvidenceSpan]]:
        """Resolve primary entity and extract character offset evidence spans from text.

        Guarantees:
        - Cashtags match with priority 1.
        - Exact alias matches checked next.
        - Ambiguous words require finance context keywords before resolving.
        - Unknown entities are marked resolved: False.
        """
        lower_text = text.lower()
        has_fin_context = any(
            re.search(rf"\b{re.escape(kw)}\b", lower_text) for kw in FINANCIAL_CONTEXT_KEYWORDS
        )

        # 1. Match Cashtags (Highest precision)
        cashtag_matches = list(re.finditer(r"\$([A-Za-z]{1,6})\b", text))
        for match in cashtag_matches:
            tag = f"${match.group(1).upper()}"
            if tag in self.cashtag_lookup:
                ticker = self.cashtag_lookup[tag]
                ke = self.entities[ticker]
                span = EvidenceSpan(
                    start=match.start(),
                    end=match.end(),
                    text=match.group(0),
                )
                return (
                    EntityReference(
                        name=ke.canonical_name,
                        ticker=ke.ticker,
                        scope="company",
                        resolved=True,
                    ),
                    [span],
                )

        # 2. Match aliases (Sorted by length descending to match longest phrases first)
        sorted_aliases = sorted(self.alias_lookup.keys(), key=len, reverse=True)
        for alias in sorted_aliases:
            pattern = rf"\b{re.escape(alias)}\b"
            match = re.search(pattern, lower_text)
            if match:
                ticker = self.alias_lookup[alias]
                ke = self.entities[ticker]

                # Check ambiguity constraint
                if ke.is_ambiguous and not has_fin_context:
                    # Ambiguous entity mention without financial context is not resolved
                    continue

                span = EvidenceSpan(
                    start=match.start(),
                    end=match.end(),
                    text=text[match.start() : match.end()],
                )
                return (
                    EntityReference(
                        name=ke.canonical_name,
                        ticker=ke.ticker,
                        scope="company",
                        resolved=True,
                    ),
                    [span],
                )

        # 3. Macro / Systemic resolution
        macro_terms = [
            "federal reserve",
            "central bank",
            "treasury yield",
            "treasury yields",
            "fomc",
            "european central bank",
            "ecb",
            "macro",
            "sovereign bond",
        ]
        for term in macro_terms:
            m = re.search(rf"\b{re.escape(term)}\b", lower_text)
            if m:
                span = EvidenceSpan(
                    start=m.start(),
                    end=m.end(),
                    text=text[m.start() : m.end()],
                )
                return (
                    EntityReference(
                        name="Macro / Central Bank",
                        ticker=None,
                        scope="macro",
                        resolved=True,
                    ),
                    [span],
                )

        # 4. Fallback: use hint only if provided and valid, but NEVER fabricate a fake span
        if hint_entity_id:
            hint_upper = hint_entity_id.upper()
            if hint_upper in ("MACRO", "SYSTEMIC"):
                return (
                    EntityReference(
                        name="Macro / Central Bank",
                        ticker=None,
                        scope="macro",
                        resolved=True,
                    ),
                    [],
                )
            if hint_upper in self.entities:
                ke = self.entities[hint_upper]
                # Try finding any alias in the text for evidence
                spans: List[EvidenceSpan] = []
                for alias in [ke.ticker] + ke.aliases + [ke.canonical_name]:
                    m = re.search(rf"\b{re.escape(alias)}\b", text, re.IGNORECASE)
                    if m:
                        spans.append(
                            EvidenceSpan(
                                start=m.start(),
                                end=m.end(),
                                text=text[m.start() : m.end()],
                            )
                        )
                        break

                return (
                    EntityReference(
                        name=ke.canonical_name,
                        ticker=ke.ticker,
                        scope="company",
                        resolved=True,
                    ),
                    spans,
                )

        # 5. Unknown entity
        return (
            EntityReference(
                name="Unknown Entity",
                ticker=None,
                scope="unknown",
                resolved=False,
            ),
            [],
        )
