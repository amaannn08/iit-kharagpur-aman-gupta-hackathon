"""Additive impact severity rubric engine conforming to PRD Section 7.4."""

import re
from typing import Dict, List, Tuple

from sentinel.contracts.signals import (
    EntityReference,
    EvidenceSpan,
    ImpactComponents,
    ImpactOutput,
)

RUBRIC_VERSION = "1.0"

# Versioned Event Base Scores (1 to 6 scale)
EVENT_BASE_SCORES: Dict[str, int] = {
    "CREDIT": 5,
    "MACRO": 5,
    "GEOPOLITICAL": 5,
    "CYBER": 5,
    "SUPPLY_CHAIN": 5,
    "REGULATORY": 4,
    "M_AND_A": 4,
    "PRODUCT": 3,
    "EARNINGS": 3,
    "OTHER": 1,
}

SYSTEMIC_KEYWORDS = {
    "systemic",
    "contagion",
    "nationwide",
    "global",
    "industry-wide",
    "across the sector",
    "all banks",
    "worldwide",
    "market-wide",
}

SECTOR_KEYWORDS = {
    "sector",
    "peers",
    "regional banks",
    "automakers",
    "tech firms",
    "energy producers",
    "broad industry",
    "supply chain network",
    "syndicated",
    "syndicate",
    "banking sector",
}

REASSURANCE_KEYWORDS = {
    "denies",
    "denied",
    "unchanged",
    "reassures",
    "routine",
    "in line with expectations",
    "fully operational",
    "no default",
    "stabilizes",
}

CATASTROPHIC_SEVERITY_KEYWORDS = {
    "default",
    "bankruptcy",
    "insolvent",
    "insolvency",
    "chapter 11",
    "force majeure",
    "closed by regulators",
    "bank run",
    "liquidation",
    "catastrophic",
    "run on the bank",
    "ransomware",
    "unpatched",
    "zero-day",
    "covenant breach",
    "covenants",
    "blast furnace",
    "halted indefinitely",
}

MATERIAL_SEVERITY_KEYWORDS = {
    "downgrade",
    "downgraded",
    "probe",
    "investigation",
    "lawsuit",
    "shortfall",
    "breach",
    "curb",
    "halted",
    "suspended",
    "warning",
    "distress",
    "subpoena",
    "antitrust",
    "monopolization",
    "hiking",
    "hike",
    "declined",
    "decline",
    "missed",
    "restructuring",
    "exploit",
    "exploited",
}


class SeverityRubricEngine:
    """Calculates auditable impact score (1-10) using additive components."""

    def __init__(self, rubric_version: str = RUBRIC_VERSION) -> None:
        self.rubric_version = rubric_version

    def evaluate(
        self,
        event_class: str,
        text: str,
        entity: EntityReference,
    ) -> Tuple[ImpactOutput, List[EvidenceSpan]]:
        """Calculate impact score with component breakdown and triggering evidence spans."""
        lower_text = text.lower()
        evidence_spans: List[EvidenceSpan] = []

        # 1. Base Score
        event_base = EVENT_BASE_SCORES.get(event_class.upper(), 1)

        # 2. Scope Increment (0, 1, or 2) with Evidence Spans
        scope = 0
        if entity.scope == "macro" or any(kw in lower_text for kw in SYSTEMIC_KEYWORDS):
            scope = 2
            for kw in sorted(SYSTEMIC_KEYWORDS, key=len, reverse=True):
                match = re.search(rf"\b{re.escape(kw)}\b", lower_text)
                if match:
                    evidence_spans.append(
                        EvidenceSpan(
                            start=match.start(),
                            end=match.end(),
                            text=text[match.start() : match.end()],
                        )
                    )
                    break
        elif any(kw in lower_text for kw in SECTOR_KEYWORDS):
            scope = 1
            for kw in sorted(SECTOR_KEYWORDS, key=len, reverse=True):
                match = re.search(rf"\b{re.escape(kw)}\b", lower_text)
                if match:
                    evidence_spans.append(
                        EvidenceSpan(
                            start=match.start(),
                            end=match.end(),
                            text=text[match.start() : match.end()],
                        )
                    )
                    break

        # 3. Explicit Severity Increment (0, 1, or 2)
        explicit_sev = 0
        matched_words = set()

        # Check catastrophic triggers first
        for kw in sorted(CATASTROPHIC_SEVERITY_KEYWORDS, key=len, reverse=True):
            match = re.search(rf"\b{re.escape(kw)}\b", lower_text)
            if match and kw not in matched_words:
                matched_words.add(kw)
                explicit_sev = 2
                evidence_spans.append(
                    EvidenceSpan(
                        start=match.start(),
                        end=match.end(),
                        text=text[match.start() : match.end()],
                    )
                )
                break

        # Check material triggers if not catastrophic
        if explicit_sev == 0:
            for kw in sorted(MATERIAL_SEVERITY_KEYWORDS, key=len, reverse=True):
                match = re.search(rf"\b{re.escape(kw)}\b", lower_text)
                if match and kw not in matched_words:
                    matched_words.add(kw)
                    explicit_sev = 1
                    evidence_spans.append(
                        EvidenceSpan(
                            start=match.start(),
                            end=match.end(),
                            text=text[match.start() : match.end()],
                        )
                    )
                    break

        # 4. Mitigating / Reassurance adjustment (e.g. routine stability, denial of rumors)
        mitigation = 0
        for kw in sorted(REASSURANCE_KEYWORDS, key=len, reverse=True):
            match = re.search(rf"\b{re.escape(kw)}\b", lower_text)
            if match:
                mitigation = -2 if kw in ("denies", "denied", "routine", "unchanged") else -1
                evidence_spans.append(
                    EvidenceSpan(
                        start=match.start(),
                        end=match.end(),
                        text=text[match.start() : match.end()],
                    )
                )
                break

        total_score = max(1, min(10, event_base + scope + explicit_sev + mitigation))

        output = ImpactOutput(
            score=total_score,
            rubric_version=self.rubric_version,
            components=ImpactComponents(
                event_base=event_base,
                scope=scope,
                explicit_severity=max(0, explicit_sev + mitigation),
            ),
        )
        return output, evidence_spans
