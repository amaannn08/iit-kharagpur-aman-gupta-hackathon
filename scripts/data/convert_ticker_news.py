#!/usr/bin/env python3
"""Convert Kaggle Ticker-Level Financial News into S&P Sentinel external dataset contract.

Converts raw ticker news (rdolphin/financial-news-with-ticker-level-sentiment) into:
1. data/external/ticker_news/replay_sample.csv: Contract-compliant InputRecord schema (unlabeled)
2. data/external/ticker_news/silver_labels.csv: Detached silver labels keyed by record_id
3. data/external/ticker_news/LICENSE: Attribution and CC0 license notice
"""

import csv
import hashlib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RAW_DIR = REPO_ROOT / "data" / "raw" / "kaggle" / "ticker_news"
OUT_DIR = REPO_ROOT / "data" / "external" / "ticker_news"

LICENSE_TEXT = """Creative Commons CC0: Public Domain Dedication

Source: Financial News with Ticker-Level Sentiment
Curator: rdolphin (Kaggle)
Description: Public financial news summaries with ticker tags and sentiment indicators.
License: CC0 1.0 Universal (CC0 1.0) Public Domain Dedication.
"""


def convert_ticker_news(max_samples: int = 500) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    raw_files = list(RAW_DIR.glob("*.csv"))
    if not raw_files:
        print(f"Error: No raw ticker news files found in {RAW_DIR}")
        return

    raw_file = raw_files[0]
    print(f"[CONVERT] Reading Ticker News from {raw_file.relative_to(REPO_ROOT)}...")

    input_records = []
    silver_labels = []

    with open(raw_file, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        count = 0
        for row in reader:
            headline = (row.get("headline") or row.get("title") or "").strip()
            body = (row.get("summary") or row.get("body") or headline).strip()
            published_at = (row.get("published_at") or row.get("date") or "2026-03-15T12:00:00Z").strip()
            ticker = (row.get("ticker") or row.get("stock") or "").strip()
            sentiment_label = (row.get("sentiment_label") or row.get("sentiment") or "neutral").strip()
            sentiment_score = float(row.get("sentiment_score") or 0.0)

            if not headline:
                continue

            rec_id = f"kn-{hashlib.sha256(headline.encode('utf-8')).hexdigest()[:10]}"

            input_record = {
                "record_id": rec_id,
                "source_id": "kaggle_rdolphin_ticker_news",
                "source_type": "NEWS",
                "headline": headline,
                "body": body,
                "published_at": published_at,
                "timestamp_quality": "ORIGINAL",
                "simulated_at": "",
                "is_synthetic": "false",
                "primary_entity_id": "",  # Unlabeled, entity linking extracts entity
            }
            input_records.append(input_record)

            silver_labels.append({
                "record_id": rec_id,
                "ticker": ticker,
                "sentiment_label": sentiment_label,
                "sentiment_score": sentiment_score,
            })

            count += 1
            if count >= max_samples:
                break

    # Write unlabeled input records
    sample_csv = OUT_DIR / "replay_sample.csv"
    fieldnames = [
        "record_id",
        "source_id",
        "source_type",
        "headline",
        "body",
        "published_at",
        "timestamp_quality",
        "simulated_at",
        "is_synthetic",
        "primary_entity_id",
    ]
    with open(sample_csv, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(input_records)
    print(f"  OK: Wrote {len(input_records)} records to {sample_csv.relative_to(REPO_ROOT)}")

    # Write detached silver labels
    labels_csv = OUT_DIR / "silver_labels.csv"
    with open(labels_csv, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["record_id", "ticker", "sentiment_label", "sentiment_score"]
        )
        writer.writeheader()
        writer.writerows(silver_labels)
    print(f"  OK: Wrote {len(silver_labels)} labels to {labels_csv.relative_to(REPO_ROOT)}")

    # Write LICENSE attribution
    license_file = OUT_DIR / "LICENSE"
    with open(license_file, mode="w", encoding="utf-8") as f:
        f.write(LICENSE_TEXT)
    print(f"  OK: Wrote attribution notice to {license_file.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    convert_ticker_news()
