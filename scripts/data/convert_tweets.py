#!/usr/bin/env python3
"""Convert Kaggle Stock Tweets dataset into S&P Sentinel external dataset contract.

Converts raw tweets (thedevastator/tweet-sentiment-s-impact-on-stock-returns) into:
1. data/external/tweets/replay_sample.csv: Contract-compliant Social InputRecord schema
2. data/external/tweets/outcomes.csv: Detached forward returns and volatility for backtesting
3. data/external/tweets/LICENSE: Attribution and CC0 license notice
"""

import csv
import hashlib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RAW_DIR = REPO_ROOT / "data" / "raw" / "kaggle" / "tweets"
OUT_DIR = REPO_ROOT / "data" / "external" / "tweets"

LICENSE_TEXT = """Creative Commons CC0: Public Domain Dedication

Source: Tweet Sentiment's Impact on Stock Returns
Curator: thedevastator (Kaggle)
Description: Historical stock tweets and subsequent 1-day/7-day forward return metrics.
License: CC0 1.0 Universal (CC0 1.0) Public Domain Dedication.
"""


def convert_tweets(max_samples: int = 500) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    raw_files = list(RAW_DIR.glob("*.csv"))
    if not raw_files:
        print(f"Error: No raw tweets files found in {RAW_DIR}")
        return

    raw_file = raw_files[0]
    print(f"[CONVERT] Reading Tweets from {raw_file.relative_to(REPO_ROOT)}...")

    input_records = []
    outcomes = []

    with open(raw_file, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        count = 0
        for row in reader:
            text = (row.get("tweet") or row.get("text") or "").strip()
            stock = (row.get("stock") or row.get("ticker") or "").strip()
            date_str = (row.get("date") or "2026-03-15").strip()
            ret_1d = float(row.get("forward_return_1d") or 0.0)
            ret_7d = float(row.get("forward_return_7d") or 0.0)
            vol = float(row.get("volatility") or 0.20)

            if not text:
                continue

            rec_id = f"tw-{hashlib.sha256(text.encode('utf-8')).hexdigest()[:10]}"

            # Parse cashtags
            cashtag = f"${stock}" if stock else ""

            input_record = {
                "record_id": rec_id,
                "source_id": "kaggle_stock_tweets",
                "source_type": "SOCIAL",
                "text": text,
                "author_handle": "trader_quant",
                "published_at": f"{date_str}T14:30:00Z",
                "timestamp_quality": "DATE_ONLY",
                "simulated_at": "",
                "is_synthetic": "false",
                "cashtags": cashtag,
                "primary_entity_id": "",  # Unresolved, let entity linking extract ticker
            }
            input_records.append(input_record)

            outcomes.append({
                "record_id": rec_id,
                "stock": stock,
                "forward_return_1d": ret_1d,
                "forward_return_7d": ret_7d,
                "volatility": vol,
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
        "text",
        "author_handle",
        "published_at",
        "timestamp_quality",
        "simulated_at",
        "is_synthetic",
        "cashtags",
        "primary_entity_id",
    ]
    with open(sample_csv, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(input_records)
    print(f"  OK: Wrote {len(input_records)} records to {sample_csv.relative_to(REPO_ROOT)}")

    # Write detached outcomes
    outcomes_csv = OUT_DIR / "outcomes.csv"
    with open(outcomes_csv, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["record_id", "stock", "forward_return_1d", "forward_return_7d", "volatility"]
        )
        writer.writeheader()
        writer.writerows(outcomes)
    print(f"  OK: Wrote {len(outcomes)} outcomes to {outcomes_csv.relative_to(REPO_ROOT)}")

    # Write LICENSE attribution
    license_file = OUT_DIR / "LICENSE"
    with open(license_file, mode="w", encoding="utf-8") as f:
        f.write(LICENSE_TEXT)
    print(f"  OK: Wrote attribution notice to {license_file.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    convert_tweets()
