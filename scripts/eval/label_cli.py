#!/usr/bin/env python3
"""Interactive CLI for human ground-truth annotation on held-out news records.

Target: 120 rows stratified across Polygon (60), GDELT (40), and SEC 8-K (20).
Autosaves to data/eval/holdout_v2_news.csv after every labeled row.
Supports --agreement RELABEL_CSV: Cohen's kappa and severity MAE between the holdout and an
independent second labeling pass of a subset (e.g. the same annotator a day later).
Supports --freeze to lock SHA-256 into data/eval/FROZEN.txt.
"""

import argparse
import csv
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
from sklearn.metrics import cohen_kappa_score

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATA = REPO_ROOT / "data"
EVAL_DIR = DATA / "eval"
HOLDOUT_CSV = EVAL_DIR / "holdout_v2_news.csv"
FROZEN_TXT = EVAL_DIR / "FROZEN.txt"
RUBRIC_MD = EVAL_DIR / "annotation_rubric.md"

EVENT_CLASSES = [
    "OTHER",         # 0
    "CREDIT",        # 1
    "EARNINGS",      # 2
    "GEOPOLITICAL",  # 3
    "MACRO",         # 4
    "M_AND_A",       # 5
    "PRODUCT",       # 6
    "REGULATORY",    # 7
    "SUPPLY_CHAIN",  # 8
    "CYBER",         # 9
]

EVENT_KEY_MAP = {
    "0": "OTHER",
    "1": "CREDIT",
    "2": "EARNINGS",
    "3": "GEOPOLITICAL",
    "4": "MACRO",
    "5": "M_AND_A",
    "6": "PRODUCT",
    "7": "REGULATORY",
    "8": "SUPPLY_CHAIN",
    "9": "CYBER",
}

SENTIMENT_KEY_MAP = {
    "-": "negative",
    "0": "neutral",
    "+": "positive",
    "neg": "negative",
    "neu": "neutral",
    "pos": "positive",
}

FIELDNAMES = [
    "record_id",
    "source_type",
    "source_id",
    "headline",
    "body",
    "gold_event_class",
    "gold_sentiment_label",
    "gold_severity_score",
    "should_trigger",
    "annotator",
]


def load_stratified_candidates(seed: int = 42) -> List[Dict[str, Any]]:
    """Sample 120 candidate rows: 60 Polygon, 40 GDELT, 20 SEC 8-K."""
    candidates: List[Dict[str, Any]] = []

    # 1. Polygon news (60 rows: 20 each from Q4 months, diverse tickers)
    poly_path = DATA / "real" / "polygon_news" / "polygon_news.csv"
    if poly_path.exists():
        df_p = pd.read_csv(poly_path)
        df_p["pub"] = pd.to_datetime(df_p.published_at)
        q4 = df_p[df_p.pub >= "2023-10-01"].copy()
        if len(q4) < 60:
            q4 = df_p.copy()
        sample_p = q4.sample(n=min(60, len(q4)), random_state=seed)
        for r in sample_p.itertuples():
            candidates.append(
                {
                    "record_id": r.record_id,
                    "source_type": "news",
                    "source_id": "polygon_news",
                    "headline": str(r.headline or ""),
                    "body": str(r.body or "")[:1500],
                }
            )

    # 2. GDELT (40 rows: 20 from SVB weekend, 20 from snapshot)
    gdelt_svb = DATA / "real" / "gdelt" / "svb_weekend.csv"
    if gdelt_svb.exists():
        df_svb = pd.read_csv(gdelt_svb)
        sample_svb = df_svb.sample(n=min(20, len(df_svb)), random_state=seed)
        for r in sample_svb.itertuples():
            candidates.append(
                {
                    "record_id": r.record_id,
                    "source_type": "news",
                    "source_id": "gdelt_svb_2023",
                    "headline": str(r.headline or ""),
                    "body": str(r.body or "")[:1500],
                }
            )
    gdelt_snap = DATA / "real" / "gdelt" / "snapshot.csv"
    if gdelt_snap.exists():
        df_snap = pd.read_csv(gdelt_snap)
        sample_snap = df_snap.sample(n=min(20, len(df_snap)), random_state=seed)
        for r in sample_snap.itertuples():
            candidates.append(
                {
                    "record_id": r.record_id,
                    "source_type": "news",
                    "source_id": "gdelt_snapshot",
                    "headline": str(r.headline or ""),
                    "body": str(r.body or "")[:1500],
                }
            )

    # 3. SEC 8-K (20 rows: stratified across item labels)
    sec_path = DATA / "train" / "sec_8k" / "items.csv"
    if sec_path.exists():
        df_sec = pd.read_csv(sec_path)
        sample_sec = df_sec.sample(n=min(20, len(df_sec)), random_state=seed)
        for r in sample_sec.itertuples():
            candidates.append(
                {
                    "record_id": r.record_id,
                    "source_type": "news",
                    "source_id": "sec_8k",
                    "headline": f"SEC 8-K Item {r.item}: {r.company}",
                    "body": str(r.text or "")[:1500],
                }
            )

    return candidates


def load_labeled_records() -> Dict[str, Dict[str, Any]]:
    """Load existing annotations by record_id."""
    if not HOLDOUT_CSV.exists():
        return {}
    with open(HOLDOUT_CSV, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return {r["record_id"]: r for r in reader}


def append_annotation(row: Dict[str, Any]) -> None:
    """Safely append a single annotation to holdout_v2_news.csv."""
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    file_exists = HOLDOUT_CSV.exists()
    with open(HOLDOUT_CSV, mode="a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, lineterminator="\n")
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


def freeze_holdout() -> str:
    """Calculate SHA-256 of holdout_v2_news.csv and write to FROZEN.txt."""
    if not HOLDOUT_CSV.exists():
        raise FileNotFoundError(f"{HOLDOUT_CSV} does not exist.")
    sha = hashlib.sha256(HOLDOUT_CSV.read_bytes()).hexdigest()
    count = sum(1 for _ in open(HOLDOUT_CSV, encoding="utf-8")) - 1
    content = f"dataset: data/eval/holdout_v2_news.csv\nrows: {count}\nsha256: {sha}\n"
    FROZEN_TXT.write_text(content)
    print(f"Locked {count} rows in {FROZEN_TXT}:\nSHA-256: {sha}")
    return sha


def compute_agreement(
    ref_df: pd.DataFrame, test_df: pd.DataFrame
) -> Tuple[float, float, float]:
    """Compute Cohen's kappa (event), Cohen's kappa (severity), and severity MAE."""
    merged = ref_df.merge(test_df, on="record_id", suffixes=("_ref", "_test"))
    if merged.empty:
        return 0.0, 0.0, 0.0

    # Event Cohen's kappa
    kappa_event = float(
        cohen_kappa_score(merged["gold_event_class_ref"], merged["gold_event_class_test"])
    )

    # Severity quadratic weighted kappa & MAE
    sev_ref = merged["gold_severity_score_ref"].astype(int)
    sev_test = merged["gold_severity_score_test"].astype(int)
    kappa_sev = float(cohen_kappa_score(sev_ref, sev_test, weights="quadratic"))
    mae_sev = float(np.mean(np.abs(sev_ref - sev_test)))

    return round(kappa_event, 3), round(kappa_sev, 3), round(mae_sev, 3)


def print_rubric() -> None:
    if RUBRIC_MD.exists():
        print("\n" + "=" * 60)
        print(RUBRIC_MD.read_text())
        print("=" * 60 + "\n")
    else:
        print("Rubric file not found.")


def run_labeling_session(annotator_name: str = "Aman Gupta") -> None:
    """Run interactive labeling loop."""
    existing = load_labeled_records()
    candidates = load_stratified_candidates()

    remaining = [c for c in candidates if c["record_id"] not in existing]
    total_needed = 120
    print(
        f"\nS&P Sentinel Ground-Truth Labeling CLI\n"
        f"Progress: {len(existing)} / {total_needed} labeled ({len(remaining)} remaining)\n"
        f"Keys: Event [0-9], Sentiment [-,0,+], Severity [1-10], Trigger [y/n], '?' rubric, 's' skip, 'q' quit\n"
    )

    for i, c in enumerate(remaining, start=len(existing) + 1):
        print("=" * 80)
        print(f"[{i}/{total_needed}] Source: {c['source_id']} ({c['source_type']}) | ID: {c['record_id']}")
        print(f"Headline: {c['headline']}")
        body_prev = c["body"][:300].replace("\n", " ")
        if len(c["body"]) > 300:
            body_prev += "..."
        print(f"Body: {body_prev}")
        print("-" * 80)

        # 1. Event class
        event = None
        while event is None:
            inp = input("Event class [0=OTHER, 1=CREDIT, 2=EARNINGS, 3=GEOPOL, 4=MACRO, 5=M&A, 6=PROD, 7=REG, 8=SUPPLY, 9=CYBER, ?=rubric]: ").strip()
            if inp == "?":
                print_rubric()
                continue
            if inp.lower() == "q":
                print("Session ended.")
                return
            if inp.lower() == "s":
                print("Skipped record.")
                break
            if inp in EVENT_KEY_MAP:
                event = EVENT_KEY_MAP[inp]
            elif inp.upper() in EVENT_CLASSES:
                event = inp.upper()
            else:
                print("Invalid input. Enter 0-9 or ?.")

        if event is None:
            continue

        # 2. Sentiment
        sentiment = None
        while sentiment is None:
            inp = input("Sentiment [-=negative, 0=neutral, +=positive]: ").strip()
            if inp.lower() == "q":
                return
            if inp in SENTIMENT_KEY_MAP:
                sentiment = SENTIMENT_KEY_MAP[inp]
            else:
                print("Invalid sentiment. Enter -, 0, or +.")

        # 3. Severity
        severity = None
        while severity is None:
            inp = input("Severity [1-10]: ").strip()
            if inp.lower() == "q":
                return
            try:
                val = int(inp)
                if 1 <= val <= 10:
                    severity = val
                else:
                    print("Score must be between 1 and 10.")
            except ValueError:
                print("Invalid number.")

        # 4. Should trigger stress test
        should_trig = None
        while should_trig is None:
            inp = input("Should trigger stress test? [y/n]: ").strip().lower()
            if inp == "q":
                return
            if inp in ("y", "yes", "true", "1"):
                should_trig = "true"
            elif inp in ("n", "no", "false", "0"):
                should_trig = "false"
            else:
                print("Enter y or n.")

        row = {
            "record_id": c["record_id"],
            "source_type": c["source_type"],
            "source_id": c["source_id"],
            "headline": c["headline"],
            "body": c["body"],
            "gold_event_class": event,
            "gold_sentiment_label": sentiment,
            "gold_severity_score": severity,
            "should_trigger": should_trig,
            "annotator": annotator_name,
        }
        append_annotation(row)
        print(f"Saved: {event} | {sentiment} | severity={severity} | trigger={should_trig}\n")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--freeze", action="store_true", help="Lock SHA-256 to FROZEN.txt")
    ap.add_argument("--agreement", type=Path, default=None, metavar="RELABEL_CSV",
                    help="Second, independent labeling pass of a subset of the holdout rows")
    ap.add_argument("--annotator", default=None, help="Annotator name (required to label)")
    args = ap.parse_args()

    if args.freeze:
        freeze_holdout()
        return

    if args.agreement is not None:
        if not HOLDOUT_CSV.exists() or not args.agreement.exists():
            raise SystemExit("Both the holdout and the re-label file must exist.")
        ref, test = pd.read_csv(HOLDOUT_CSV), pd.read_csv(args.agreement)
        if ref.equals(test):
            raise SystemExit("The re-label file is identical to the holdout; agreement needs "
                             "an independent second pass.")
        ke, ks, mae = compute_agreement(ref, test)
        print(f"Rows compared: {len(ref.merge(test, on='record_id'))}")
        print(f"Cohen's kappa (event): {ke:.3f}")
        print(f"Cohen's kappa (severity quadratic): {ks:.3f}")
        print(f"Severity MAE: {mae:.3f}")
        return

    if not args.annotator:
        raise SystemExit("--annotator is required for a labeling session")
    run_labeling_session(args.annotator)


if __name__ == "__main__":
    main()
