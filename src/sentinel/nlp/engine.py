"""NLP pipeline orchestrator producing auditable RiskSignals (PRD Section 6.2 & 7)."""

from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from sentinel.config import settings
from sentinel.contracts.records import InputRecord
from sentinel.contracts.signals import (
    EntityReference,
    EventOutput,
    EvidenceSpan,
    RiskSignal,
    SentimentOutput,
)
from sentinel.nlp.entities import EntityLinker
from sentinel.nlp.events import EventClassifier
from sentinel.nlp.sentiment import FinBERTSentimentAnalyzer
from sentinel.nlp.severity import SeverityRubricEngine
from sentinel.replay.dedup import DedupDecision


class NLPEngine:
    """Orchestrates entity linking, sentiment, event classification, and severity scoring."""

    def __init__(
        self,
        entity_linker: Optional[EntityLinker] = None,
        sentiment_analyzer: Optional[FinBERTSentimentAnalyzer] = None,
        event_classifier: Optional[EventClassifier] = None,
        severity_engine: Optional[SeverityRubricEngine] = None,
        action_impact_threshold: Optional[int] = None,
        action_confidence_threshold: Optional[float] = None,
    ) -> None:

        self.action_impact_threshold = (
            action_impact_threshold
            if action_impact_threshold is not None
            else settings.action_impact_threshold
        )
        self.action_confidence_threshold = (
            action_confidence_threshold
            if action_confidence_threshold is not None
            else settings.action_confidence_threshold
        )

        self.entity_linker = entity_linker or EntityLinker()
        self.sentiment_analyzer = sentiment_analyzer or FinBERTSentimentAnalyzer()
        # Abstention threshold comes from the trained model's card (chosen on a dev split)
        self.event_classifier = event_classifier or EventClassifier()
        self.severity_engine = severity_engine or SeverityRubricEngine()

    def process_record(
        self,
        record: InputRecord,
        run_id: str,
        dedup_decision: Optional[DedupDecision] = None,
    ) -> RiskSignal:
        """Process a record and return the signal for its primary (first-mentioned) entity."""
        return self.process_record_multi(record, run_id, dedup_decision)[0]

    def process_record_multi(
        self,
        record: InputRecord,
        run_id: str,
        dedup_decision: Optional[DedupDecision] = None,
    ) -> List[RiskSignal]:
        """Emit one auditable RiskSignal per resolved entity (PRD Section 6.2).

        Sentiment and event classification are computed once per record; impact and action
        eligibility are computed per entity because scope (company vs macro) changes them.
        """
        lower_text = record.text.lower()

        # 1. Entity Resolution (every company mentioned, or macro / unresolved fallback)
        entities = self.entity_linker.resolve_all(
            record.text,
            hint_entity_id=record.primary_entity_id,
        )

        # 2. Sentiment Analysis
        sentiment = self.sentiment_analyzer.analyze(record.text)

        # 3. Event Classification
        event = self.event_classifier.predict(record.text)

        # Directional macro policy tagging (Bug B2 fix)
        if event.label.upper() == "MACRO":
            if any(
                w in lower_text
                for w in (
                    "rate cut",
                    "cuts rate",
                    "cutting rate",
                    "easing",
                    "lower rate",
                    "lowers rate",
                    "rate reduction",
                    "monetary stimulus",
                )
            ):
                event.macro_direction = "easing"
            elif any(
                w in lower_text
                for w in (
                    "rate hike",
                    "hikes rate",
                    "hiking rate",
                    "tightening",
                    "raise rate",
                    "raises rate",
                    "rate increase",
                    "inflation surge",
                )
            ):
                event.macro_direction = "tightening"
            else:
                event.macro_direction = "none"

        return [
            self._build_signal(
                record, run_id, dedup_decision, entity_ref, entity_spans, sentiment, event
            )
            for entity_ref, entity_spans in entities
        ]

    def _build_signal(
        self,
        record: InputRecord,
        run_id: str,
        dedup_decision: Optional[DedupDecision],
        entity_ref: EntityReference,
        entity_spans: List[EvidenceSpan],
        sentiment: SentimentOutput,
        event: EventOutput,
    ) -> RiskSignal:
        # 4. Severity Rubric Scoring
        impact, severity_spans = self.severity_engine.evaluate(
            event_class=event.label,
            text=record.text,
            entity=entity_ref,
        )

        # Combine unique evidence spans
        all_spans: List[EvidenceSpan] = []
        seen_spans = set()
        for span in entity_spans + event.evidence + severity_spans:
            key = (span.start, span.end, span.text)
            if key not in seen_spans:
                seen_spans.add(key)
                all_spans.append(span)

        # 5. Action Eligibility Gating (PRD Section 7.3 & 9.3)
        eligible = True
        block_reasons: List[str] = []

        if dedup_decision and dedup_decision.is_duplicate:
            eligible = False
            block_reasons.append("DUPLICATE_TEXT_SUPPRESSED")

        if event.abstained or event.label == "OTHER":
            eligible = False
            block_reasons.append("EVENT_CLASSIFICATION_OTHER")

        if event.confidence < self.action_confidence_threshold:
            eligible = False
            block_reasons.append("CONFIDENCE_BELOW_THRESHOLD")

        if impact.score <= self.action_impact_threshold:
            eligible = False
            block_reasons.append("IMPACT_BELOW_ACTION_THRESHOLD")

        if not entity_ref.resolved:
            eligible = False
            block_reasons.append("UNRESOLVED_ENTITY")

        duplicate_group_id = (
            dedup_decision.duplicate_group_id
            if dedup_decision and dedup_decision.is_duplicate
            else None
        )

        return RiskSignal(
            schema_version="1.0",
            signal_id=f"sig-{uuid4().hex[:12]}",
            run_id=run_id,
            record_id=record.record_id,
            source_id=record.source_id,
            source_type=record.source_type.value,
            is_synthetic=record.is_synthetic,
            published_at=record.published_at,
            timestamp_quality=record.timestamp_quality.value,
            simulated_at=record.simulated_at,
            processed_at=datetime.utcnow(),
            entity=entity_ref,
            sentiment=sentiment.model_copy(deep=True),
            event=event.model_copy(deep=True),
            impact=impact,
            evidence=all_spans,
            duplicate_group_id=duplicate_group_id,
            eligible_for_action=eligible,
            action_block_reasons=block_reasons,
            model_versions={
                "sentiment": self.sentiment_analyzer.model_version,
                "event": self.event_classifier.model_version,
                "rubric": self.severity_engine.rubric_version,
            },
        )
