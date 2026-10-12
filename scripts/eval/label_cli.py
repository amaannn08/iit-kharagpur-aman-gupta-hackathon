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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.metrics import cohen_kappa_score

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATA = REPO_ROOT / "data"
EVAL_DIR = DATA / "eval"
HOLDOUT_CSV = EVAL_DIR / "holdout_v2_news.csv"
RELABEL_CSV = EVAL_DIR / "holdout_v2_news.relabel.csv"
MIN_RELABEL_GAP_HOURS = 12
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
    "labeled_at",  # UTC time the row was labeled; agreement checks rely on it
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


def load_labeled_records(path: Path = HOLDOUT_CSV) -> Dict[str, Dict[str, Any]]:
    """Load existing annotations by record_id."""
    if not path.exists():
        return {}
    with open(path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return {r["record_id"]: r for r in reader}


def append_annotation(row: Dict[str, Any], path: Path = HOLDOUT_CSV) -> None:
    """Append one annotation (autosave after every row)."""
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    file_exists = path.exists()
    if file_exists:
        with open(path, encoding="utf-8") as f:
            header = next(csv.reader(f), [])
        if header != FIELDNAMES:
            raise SystemExit(f"{path} was not written by this tool (columns {header}); "
                             "label into a new file with --out.")
    row = {**row, "labeled_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    with open(path, mode="a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, lineterminator="\n")
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


def validate_relabel(ref: pd.DataFrame, test: pd.DataFrame) -> Tuple[pd.DataFrame, str]:
    """Rows of the re-label pass that count for agreement, and why others were rejected.

    A row counts only if it was written by a labeling session (it has its own labeled_at) at
    least MIN_RELABEL_GAP_HOURS after the first-pass row, when the first pass has timestamps.
    A copied subset of the holdout has no labeled_at of its own and yields no rows.
    """
    if "labeled_at" not in test.columns:
        return test.iloc[0:0], "re-label file has no labeled_at column (not written by a labeling session)"
    merged = ref.merge(test, on="record_id", suffixes=("_ref", "_test"))
    t_test = pd.to_datetime(merged["labeled_at_test" if "labeled_at" in ref.columns else "labeled_at"],
                            errors="coerce", utc=True)  # fmt: skip
    ok = t_test.notna()
    reason = ""
    if "labeled_at" in ref.columns:
        t_ref = pd.to_datetime(merged["labeled_at_ref"], errors="coerce", utc=True)
        gap_ok = (t_test - t_ref) >= pd.Timedelta(hours=MIN_RELABEL_GAP_HOURS)
        if (ok & ~gap_ok).any():
            reason = f"{int((ok & ~gap_ok).sum())} rows re-labeled less than {MIN_RELABEL_GAP_HOURS} h after the first pass"
        ok &= gap_ok
    return merged[ok.values], reason


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
    return agreement_from_merged(merged)


def agreement_from_merged(merged: pd.DataFrame) -> Tuple[float, float, float]:
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


def run_labeling_session(annotator_name: str, out_path: Path = HOLDOUT_CSV,
                         candidates: Optional[List[Dict[str, Any]]] = None) -> None:
    """Run interactive labeling loop; only the text is shown, never earlier labels."""
    existing = load_labeled_records(out_path)
    candidates = candidates if candidates is not None else load_stratified_candidates()

    remaining = [c for c in candidates if c["record_id"] not in existing]
    total_needed = len(candidates)
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
        append_annotation(row, out_path)
        print(f"Saved: {event} | {sentiment} | severity={severity} | trigger={should_trig}\n")


HUMAN_CSV = EVAL_DIR / "holdout_v2_news.human.csv"


def load_candidates_from_holdout(path: Path = HOLDOUT_CSV) -> List[Dict[str, Any]]:
    """Load text fields blind from holdout_v2_news.csv (stripping existing labels)."""
    if not path.exists():
        return load_stratified_candidates()
    df = pd.read_csv(path)
    required = ["record_id", "source_type", "source_id", "headline", "body"]
    for col in required:
        if col not in df.columns:
            return load_stratified_candidates()
    return df[required].fillna("").to_dict("records")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--freeze", action="store_true", help="Lock SHA-256 to FROZEN.txt")
    ap.add_argument(
        "--agreement",
        action="store_true",
        help=f"Agreement between {HOLDOUT_CSV.name} and {HUMAN_CSV.name} (or {RELABEL_CSV.name})",
    )
    ap.add_argument(
        "--compare-file",
        type=Path,
        default=None,
        help="Specific second file to compare against holdout_v2_news.csv",
    )
    ap.add_argument(
        "--relabel",
        type=int,
        default=0,
        metavar="N",
        help=f"Second-pass session on N random holdout rows, into {RELABEL_CSV.name}",
    )
    ap.add_argument(
        "--source",
        type=Path,
        default=HOLDOUT_CSV,
        help="Source CSV containing text items to label (defaults to holdout_v2_news.csv)",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=HUMAN_CSV,
        help="Output CSV for human annotations (defaults to holdout_v2_news.human.csv)",
    )
    ap.add_argument("--annotator", default=None, help="Annotator name (required to label)")
    args = ap.parse_args()

    if args.freeze:
        freeze_holdout()
        return

    if args.agreement:
        test_file = args.compare_file
        if test_file is None:
            if HUMAN_CSV.exists():
                test_file = HUMAN_CSV
            elif RELABEL_CSV.exists():
                test_file = RELABEL_CSV
            else:
                raise SystemExit(
                    f"Neither {HUMAN_CSV.name} nor {RELABEL_CSV.name} exists. "
                    "Label rows first using --annotator '<name>' --out data/eval/holdout_v2_news.human.csv"
                )
        if not HOLDOUT_CSV.exists() or not test_file.exists():
            raise SystemExit(f"Both {HOLDOUT_CSV.name} and {test_file.name} must exist.")
        ref_df = pd.read_csv(HOLDOUT_CSV)
        test_df = pd.read_csv(test_file)
        ke, ks, mae = compute_agreement(ref_df, test_df)
        merged = ref_df.merge(test_df, on="record_id")
        print(f"Comparison: {HOLDOUT_CSV.name} vs {test_file.name}")
        print(f"Rows compared: {len(merged)}")
        print(f"Cohen's kappa (event): {ke:.3f}")
        print(f"Cohen's kappa (severity quadratic): {ks:.3f}")
        print(f"Severity MAE: {mae:.3f}")
        return

    if not args.annotator:
        raise SystemExit("--annotator is required for a labeling session")
    if args.relabel:
        first = pd.read_csv(HOLDOUT_CSV).sample(n=min(args.relabel, 120), random_state=None)
        cands = first[["record_id", "source_type", "source_id", "headline", "body"]].fillna("")
        run_labeling_session(args.annotator, RELABEL_CSV, cands.to_dict("records"))
        return

    # Blind labeling session: candidate texts loaded from source CSV without labels
    candidates = load_candidates_from_holdout(args.source)
    run_labeling_session(args.annotator, args.out, candidates)


if __name__ == "__main__":
    main()

