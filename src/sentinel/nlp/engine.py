"""NLP pipeline orchestrator producing auditable RiskSignals (PRD Section 6.2 & 7)."""

from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from sentinel.contracts.records import InputRecord
from sentinel.contracts.signals import EvidenceSpan, RiskSignal
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
        action_impact_threshold: int = 7,
        action_confidence_threshold: float = 0.40,
    ) -> None:

        self.entity_linker = entity_linker or EntityLinker()
        self.sentiment_analyzer = sentiment_analyzer or FinBERTSentimentAnalyzer()
        self.event_classifier = event_classifier or EventClassifier(
            confidence_threshold=action_confidence_threshold
        )
        self.severity_engine = severity_engine or SeverityRubricEngine()
        self.action_impact_threshold = action_impact_threshold
        self.action_confidence_threshold = action_confidence_threshold

    def process_record(
        self,
        record: InputRecord,
        run_id: str,
        dedup_decision: Optional[DedupDecision] = None,
    ) -> RiskSignal:
        """Process an input record and emit an auditable RiskSignal contract."""
        # 1. Entity Resolution
        entity_ref, entity_spans = self.entity_linker.resolve(
            record.text,
            hint_entity_id=record.primary_entity_id,
        )

        # 2. Sentiment Analysis
        sentiment = self.sentiment_analyzer.analyze(record.text)

        # 3. Event Classification
        event = self.event_classifier.predict(record.text)

        # 4. Severity Rubric Scoring
        impact, severity_spans = self.severity_engine.evaluate(
            event_class=event.label,
            text=record.text,
            entity=entity_ref,
        )

        # Combine unique evidence spans
        all_spans: List[EvidenceSpan] = []
        seen_spans = set()
        for span in entity_spans + severity_spans:
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
            sentiment=sentiment,
            event=event,
            impact=impact,
            evidence=all_spans,
            duplicate_group_id=duplicate_group_id,
            eligible_for_action=eligible,
            action_block_reasons=block_reasons,
            model_versions={
                "sentiment": self.sentiment_analyzer.model_version,
                "event": "tfidf_logreg_v1.0",
                "rubric": self.severity_engine.rubric_version,
            },
        )
