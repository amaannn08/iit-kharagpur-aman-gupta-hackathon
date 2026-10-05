"""Input record contracts for multi-source financial text ingestion."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class SourceType(str, Enum):
    NEWS = "news"
    SOCIAL = "social"
    MANUAL = "manual"


class TimestampQuality(str, Enum):
    ORIGINAL = "original"
    DATE_ONLY = "date_only"
    SYNTHETIC = "synthetic"
    MISSING = "missing"


class InputRecord(BaseModel):
    """Normalized input text record conforming to PRD Section 6.1."""

    record_id: str = Field(..., description="Unique immutable record identifier")
    source_id: str = Field(..., description="Source dataset identifier e.g. news_demo")
    source_type: SourceType = Field(..., description="Source channel type")
    text: str = Field(..., min_length=5, max_length=25000, description="Raw text content")
    headline: Optional[str] = Field(None, description="Optional headline for news items")
    published_at: Optional[datetime] = Field(None, description="Original publication timestamp")
    timestamp_quality: TimestampQuality = Field(
        default=TimestampQuality.SYNTHETIC, description="Provenance quality of timestamp"
    )
    simulated_at: Optional[datetime] = Field(
        None, description="Logical timestamp in scenario replay"
    )
    is_synthetic: bool = Field(default=True, description="Flag indicating synthetic record")
    primary_entity_id: Optional[str] = Field(None, description="Explicit entity tag if known")
    scenario_id: Optional[str] = Field(None, description="Associated scenario ID")
    sequence_number: Optional[int] = Field(None, description="Replay sequence order")

    @field_validator("text")
    @classmethod
    def validate_non_empty_content(cls, v: str) -> str:
        stripped = v.strip()
        if len(stripped) < 5:
            raise ValueError("Input text must contain at least 5 non-whitespace characters")
        return stripped
