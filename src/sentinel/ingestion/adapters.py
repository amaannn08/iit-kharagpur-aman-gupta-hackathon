"""Adapters for parsing distinct local text sources into unified InputRecord contracts."""

import csv
from datetime import datetime
from pathlib import Path
from typing import List, Union

from sentinel.contracts.records import InputRecord, SourceType, TimestampQuality


class NewsAdapter:
    """Parses local financial news records into InputRecord contracts."""

    @staticmethod
    def load_from_csv(file_path: Union[str, Path]) -> List[InputRecord]:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"News dataset file not found: {path}")

        records: List[InputRecord] = []
        with open(path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for idx, row in enumerate(reader):
                text_content = f"{row.get('headline', '')}. {row.get('body', '')}".strip()
                if not text_content:
                    text_content = row.get("headline") or row.get("body") or "No content"

                published_at_str = row.get("published_at")
                published_at = (
                    datetime.fromisoformat(published_at_str.replace("Z", "+00:00"))
                    if published_at_str
                    else None
                )

                simulated_at_str = row.get("simulated_at")
                simulated_at = (
                    datetime.fromisoformat(simulated_at_str.replace("Z", "+00:00"))
                    if simulated_at_str
                    else published_at
                )

                record = InputRecord(
                    record_id=row.get("record_id", f"news-{idx:04d}"),
                    source_id=row.get("source_id", "news_demo"),
                    source_type=SourceType.NEWS,
                    text=text_content,
                    headline=row.get("headline"),
                    published_at=published_at,
                    timestamp_quality=TimestampQuality(row.get("timestamp_quality", "synthetic")),
                    simulated_at=simulated_at,
                    is_synthetic=row.get("is_synthetic", "true").lower() == "true",
                    primary_entity_id=row.get("primary_entity_id"),
                    sequence_number=idx + 1,
                )
                records.append(record)

        return records


class SocialAdapter:
    """Parses local financial social media records into InputRecord contracts."""

    @staticmethod
    def load_from_csv(file_path: Union[str, Path]) -> List[InputRecord]:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Social dataset file not found: {path}")

        records: List[InputRecord] = []
        with open(path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for idx, row in enumerate(reader):
                text_content = row.get("text", "").strip()
                if not text_content:
                    continue

                published_at_str = row.get("published_at")
                published_at = (
                    datetime.fromisoformat(published_at_str.replace("Z", "+00:00"))
                    if published_at_str
                    else None
                )

                simulated_at_str = row.get("simulated_at")
                simulated_at = (
                    datetime.fromisoformat(simulated_at_str.replace("Z", "+00:00"))
                    if simulated_at_str
                    else published_at
                )

                record = InputRecord(
                    record_id=row.get("record_id", f"soc-{idx:04d}"),
                    source_id=row.get("source_id", "social_demo"),
                    source_type=SourceType.SOCIAL,
                    text=text_content,
                    published_at=published_at,
                    timestamp_quality=TimestampQuality(row.get("timestamp_quality", "synthetic")),
                    simulated_at=simulated_at,
                    is_synthetic=row.get("is_synthetic", "true").lower() == "true",
                    primary_entity_id=row.get("primary_entity_id"),
                    sequence_number=idx + 1,
                )
                records.append(record)

        return records
