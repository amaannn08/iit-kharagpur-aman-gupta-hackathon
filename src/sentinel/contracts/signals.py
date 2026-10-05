"""Risk signal contracts conforming to PRD Section 6.2."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator


class EntityReference(BaseModel):
    name: str = Field(..., description="Canonical entity name")
    ticker: Optional[str] = Field(None, description="Mapped ticker symbol if applicable")
    scope: str = Field(default="company", description="Entity scope e.g. company, sector, macro")
    resolved: bool = Field(default=True, description="Whether entity resolution was confident")


class SentimentProbabilities(BaseModel):
    positive: float = Field(..., ge=0.0, le=1.0)
    negative: float = Field(..., ge=0.0, le=1.0)
    neutral: float = Field(..., ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_sum(self) -> "SentimentProbabilities":
        total = self.positive + self.negative + self.neutral
        if abs(total - 1.0) > 0.05:
            raise ValueError(f"Sentiment probabilities must sum to 1.0 (got {total:.3f})")
        return self


class SentimentOutput(BaseModel):
    score: float = Field(..., ge=-1.0, le=1.0, description="Numerical score P(pos) - P(neg)")
    label: str = Field(..., description="Dominant sentiment label: positive, negative, neutral")
    probabilities: SentimentProbabilities


class EventOutput(BaseModel):
    label: str = Field(..., description="Event category e.g. CREDIT, MACRO, SUPPLY_CHAIN")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Model prediction confidence")
    abstained: bool = Field(default=False, description="Whether classifier abstained to OTHER")


class ImpactComponents(BaseModel):
    event_base: int = Field(..., ge=1, le=6)
    scope: int = Field(..., ge=0, le=2)
    explicit_severity: int = Field(..., ge=0, le=2)


class ImpactOutput(BaseModel):
    score: int = Field(..., ge=1, le=10, description="Overall severity score on 1-10 scale")
    rubric_version: str = Field(default="1.0")
    components: ImpactComponents


class EvidenceSpan(BaseModel):
    start: int = Field(..., ge=0, description="Character offset start in raw text")
    end: int = Field(..., ge=0, description="Character offset end in raw text")
    text: str = Field(..., description="Extracted textual span")


class RiskSignal(BaseModel):
    """Auditable risk signal emitted by the NLP engine (PRD Section 6.2)."""

    schema_version: str = Field(default="1.0")
    signal_id: str = Field(..., description="Stable unique signal identifier")
    run_id: str = Field(..., description="Replay run ID scope")
    record_id: str = Field(..., description="Source record ID reference")
    source_id: str = Field(..., description="Source dataset e.g. news_demo")
    source_type: str = Field(..., description="news, social, or manual")
    is_synthetic: bool = Field(default=True)
    published_at: Optional[datetime] = None
    timestamp_quality: str = Field(default="synthetic")
    simulated_at: Optional[datetime] = None
    processed_at: datetime = Field(default_factory=datetime.utcnow)
    entity: EntityReference
    sentiment: SentimentOutput
    event: EventOutput
    impact: ImpactOutput
    evidence: List[EvidenceSpan] = Field(default_factory=list)
    duplicate_group_id: Optional[str] = None
    eligible_for_action: bool = Field(default=True)
    action_block_reasons: List[str] = Field(default_factory=list)
    model_versions: Dict[str, Any] = Field(default_factory=dict)
