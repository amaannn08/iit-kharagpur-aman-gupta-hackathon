#!/usr/bin/env python3
"""Convert FinancialPhraseBank raw data into S&P Sentinel external dataset contract.

Converts raw FinancialPhraseBank (Malo et al. 2014) into:
1. data/external/phrasebank/sample.csv: Contract-compliant InputRecord schema (unlabeled)
2. data/external/phrasebank/silver_labels.csv: Detached sentiment labels keyed by record_id
3. data/external/phrasebank/LICENSE: Attribution and CC BY-NC-SA 4.0 license notice
"""

import csv
import hashlib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RAW_DIR = REPO_ROOT / "data" / "raw" / "kaggle" / "phrasebank"
OUT_DIR = REPO_ROOT / "data" / "external" / "phrasebank"

LICENSE_TEXT = """Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0)

Source: FinancialPhraseBank
Authors: Pekka Malo, Ankur Sinha, Pekka Korhonen, Jyrki Wallenius, and Pyry Takala (2014)
Paper: "Good debt or bad debt: Detecting semantic orientations in economic texts"
Journal of the Association for Information Science and Technology, 65(4), 782-796.

This sample dataset is distributed for academic research and evaluation purposes in accordance with CC BY-NC-SA 4.0.
"""


def convert_phrasebank(max_samples: int = 500) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    raw_files = list(RAW_DIR.glob("*.csv")) + list(RAW_DIR.glob("*.txt"))
    if not raw_files:
        print(f"Error: No raw phrasebank files found in {RAW_DIR}")
        return

    raw_file = raw_files[0]
    print(f"[CONVERT] Reading PhraseBank from {raw_file.relative_to(REPO_ROOT)}...")

    input_records = []
    silver_labels = []

    with open(raw_file, mode="r", encoding="latin-1") as f:
        reader = csv.reader(f)
        count = 0
        for i, row in enumerate(reader):
            if len(row) < 2:
                continue

            sentiment_raw = row[0].strip().lower()
            text_raw = row[1].strip()

            # Some versions swap columns: detect text vs label
            if len(sentiment_raw) > 20 and len(text_raw) <= 20:
                sentiment_raw, text_raw = text_raw, sentiment_raw

            if sentiment_raw not in ("positive", "negative", "neutral"):
                continue

            rec_id = f"pb-{hashlib.sha256(text_raw.encode('utf-8')).hexdigest()[:10]}"

            input_record = {
                "record_id": rec_id,
                "source_id": "kaggle_financial_phrasebank",
                "source_type": "NEWS",
                "headline": text_raw[:140],
                "body": text_raw,
                "published_at": "2024-01-01T00:00:00Z",
                "timestamp_quality": "DATE_ONLY",
                "simulated_at": "",
                "is_synthetic": "false",
                "primary_entity_id": "",  # Unresolved, let entity linking work
            }
            input_records.append(input_record)

            silver_labels.append({
                "record_id": rec_id,
                "sentiment": sentiment_raw,
                "confidence": 1.0,
            })

            count += 1
            if count >= max_samples:
                break

    # Write unlabeled input records
    sample_csv = OUT_DIR / "sample.csv"
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
        writer = csv.DictWriter(f, fieldnames=["record_id", "sentiment", "confidence"])
        writer.writeheader()
        writer.writerows(silver_labels)
    print(f"  OK: Wrote {len(silver_labels)} labels to {labels_csv.relative_to(REPO_ROOT)}")

    # Write LICENSE attribution
    license_file = OUT_DIR / "LICENSE"
    with open(license_file, mode="w", encoding="utf-8") as f:
        f.write(LICENSE_TEXT)
    print(f"  OK: Wrote attribution notice to {license_file.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    convert_phrasebank()
