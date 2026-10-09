"""Impact severity scoring conforming to PRD Section 7.4.

The additive rubric (base + scope + explicit severity) always runs and supplies the
explainable components and evidence spans. When the engine passes the classified event:
  - company-level signals with a classified event are scored by the market-calibrated model
    (impact_model.py); signals with no event (OTHER / abstained) keep the rubric:
    the decile of the predicted next-day abnormal return, validated out of fold on 2,617 real
    article-company events (Spearman 0.114, CI 0.076-0.152; the rubric alone scored 0.0005);
  - systemic / macro signals keep the rubric; an explicit magnitude ("75 basis points",
    "emergency", "plunge") adds a point, and without one the score is capped at 7;
  - explicit catastrophic language (default, Chapter 11, ransomware ...) on a stress event
    class sets a floor of 8, so unambiguous credit events always reach Module B.
"""

import re
from typing import Dict, List, Optional, Tuple

from sentinel.contracts.signals import (
    EntityReference,
    EventOutput,
    EvidenceSpan,
    ImpactComponents,
    ImpactOutput,
)
from sentinel.nlp.impact_model import CATASTROPHIC, LearnedImpactModel, impact_features

RUBRIC_VERSION = "2.0"
STRESS_CLASSES = {"CREDIT", "MACRO", "GEOPOLITICAL", "SUPPLY_CHAIN", "CYBER"}
SYSTEMIC_CAP = 7
CATASTROPHIC_FLOOR = 8
EXPLICIT_MAGNITUDE = re.compile(
    r"\b(\d+(\.\d+)?\s?(bps|basis points?|%|percent|points)|emergency|surprise[sd]?|unexpected(ly)?|"
    r"shock|crash(es|ed)?|plunge[sd]?|soar(s|ed)?|spik(e|es|ed|ing)|record (high|low)|"
    r"full-scale|invasion|war|default(s|ed)?|collapse[sd]?)\b",
    re.I,
)

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

    def __init__(
        self,
        rubric_version: str = RUBRIC_VERSION,
        impact_model: Optional[LearnedImpactModel] = None,
    ) -> None:
        self.rubric_version = rubric_version
        self.impact_model = impact_model or LearnedImpactModel()

    def evaluate(
        self,
        event_class: str,
        text: str,
        entity: EntityReference,
        event: Optional[EventOutput] = None,
        sentiment_score: Optional[float] = None,
        n_entities: int = 1,
        is_social: bool = False,
    ) -> Tuple[ImpactOutput, List[EvidenceSpan]]:
        """Impact score with rubric components and evidence spans.

        Without ``event`` this is the pure additive rubric (backwards compatible).
        """
        rubric, spans = self._rubric(event_class, text, entity)
        if event is None:
            return rubric, spans

        out = rubric.model_copy()
        # Impact describes an event: with no classified event (OTHER/abstained) keep the rubric
        is_event = event_class.upper() != "OTHER" and not event.abstained
        if entity.ticker and self.impact_model.available and is_event:
            feats = impact_features(event, sentiment_score or 0.0, n_entities, text, is_social)
            pred, decile = self.impact_model.score(feats)
            out.score = decile
            out.method = "market_calibrated"
            out.market_calibration = {
                "model": self.impact_model.version,
                "predicted_abs_abnormal_z": round(pred, 4),
                "decile": decile,
                "rubric_score": rubric.score,
            }
        else:
            # Systemic: an explicit magnitude ("75 basis points", "emergency") adds a point and
            # is required to exceed the action threshold.
            if m := EXPLICIT_MAGNITUDE.search(text):
                out.score = min(10, out.score + 1)
                spans.append(EvidenceSpan(start=m.start(), end=m.end(), text=m.group()))
            else:
                out.score = min(out.score, SYSTEMIC_CAP)

        if event_class.upper() in STRESS_CLASSES and (m := CATASTROPHIC.search(text)):
            if out.score < CATASTROPHIC_FLOOR:
                out.score = CATASTROPHIC_FLOOR
                out.method = "floor"
            if not any(s.start == m.start() for s in spans):
                spans.append(EvidenceSpan(start=m.start(), end=m.end(), text=m.group()))
        return out, spans

    def _rubric(
        self,
        event_class: str,
        text: str,
        entity: EntityReference,
    ) -> Tuple[ImpactOutput, List[EvidenceSpan]]:
        """Additive rubric: base + scope + explicit severity - mitigation, clamped to 1-10."""
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
