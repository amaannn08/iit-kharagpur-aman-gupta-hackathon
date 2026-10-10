#!/usr/bin/env python3
"""Sample 300 REAL headlines for the human-labeled news holdout (plan section 6).

  150 Polygon 2023 articles (excluding headlines used as weak training labels), stratified by the current model's predicted class with rare
      classes oversampled (so CREDIT / GEOPOLITICAL / SUPPLY_CHAIN / CYBER reach >= 20 rows)
  100 GDELT snapshot headlines
   50 SEC 8-K statements, ONLY from filings the event model never trained on: the held-out
      20% split of data/train/sec_8k (same split as train_event.py) plus live captures

Writes data/eval/holdout_v2_news.todo.csv with empty gold_* columns. Fill them in yourself
following data/eval/annotation_rubric.md, save as data/eval/holdout_v2_news.csv, record its
SHA-256 in data/eval/FROZEN.txt, and never train on it. Predicted labels are used only to
choose which rows to sample; they are not written to the file, so they cannot anchor labels.

Usage: uv run python scripts/eval/sample_for_labeling.py [--seed 7]
"""

import argparse
import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATA = REPO_ROOT / "data"
sys.path.insert(0, str(REPO_ROOT / "src"))

from sentinel.nlp.events import EventClassifier  # noqa: E402

GOLD_COLUMNS = [
    "gold_entities", "gold_event", "gold_sentiment", "gold_sentiment_score",
    "gold_impact", "gold_evidence", "ambiguous", "annotator", "labeled_at",
]  # fmt: skip
RARE = {"CREDIT", "GEOPOLITICAL", "SUPPLY_CHAIN", "CYBER", "REGULATORY", "M_AND_A", "MACRO"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()
    out = DATA / "eval" / "holdout_v2_news.todo.csv"
    if (DATA / "eval" / "holdout_v2_news.csv").exists():
        sys.exit("holdout_v2_news.csv already exists (frozen); refusing to resample")

    clf = EventClassifier()
    news = pd.read_csv(DATA / "real" / "polygon_news" / "polygon_news.csv")
    news["text"] = news.headline.fillna("") + ". " + news.body.fillna("")
    # Headlines matching the weak-label patterns were event-model training data: exclude them
    spec = importlib.util.spec_from_file_location(
        "train_event", REPO_ROOT / "scripts/models/train_event.py"
    )
    train_event = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(train_event)
    weak = news.headline.fillna("").map(
        lambda h: any(p.search(h) for p in train_event.WEAK_PATTERNS.values())
    )
    news = news[~weak].copy()
    news["pred"] = [clf.predict(t).label for t in news.text]
    shuffled = news.sample(frac=1.0, random_state=args.seed)
    rare = shuffled[shuffled.pred.isin(RARE)].groupby("pred").head(20)
    rest = shuffled.drop(rare.index).head(max(0, 150 - len(rare)))
    polygon = pd.concat([rare, rest]).head(150).assign(source="polygon_2023")

    gdelt = pd.read_csv(DATA / "real" / "gdelt" / "snapshot.csv").sample(
        n=100, random_state=args.seed
    )
    gdelt = gdelt.assign(text=gdelt.headline, source="gdelt_snapshot")

    sec = pd.read_csv(DATA / "train" / "sec_8k" / "items.csv")
    _, held_ids = train_test_split(
        np.asarray(sorted(sec.accession.unique()), dtype=object), test_size=0.2, random_state=42
    )  # identical to scripts/models/train_event.py: these filings were never trained on
    held = sec[sec.accession.isin(held_ids)]
    held = held.assign(
        source="sec_8k_heldout", headline=held.company + " 8-K Item " + held.item.astype(str)
    )
    held = held.rename(columns={"file_date": "published_at"})
    cyber = held[held.label == "CYBER"]
    held = pd.concat([cyber, held.drop(cyber.index).sample(frac=1.0, random_state=args.seed)])
    parts = [held.head(50)]
    live = DATA / "live" / "sec_8k_live.csv"
    if len(parts[0]) < 50 and live.exists():
        lv = pd.read_csv(live).sample(frac=1.0, random_state=args.seed)
        lv = lv.assign(source="sec_8k_live", text=lv.headline + ". " + lv.body.fillna(""))
        parts.append(lv.head(50 - len(parts[0])))
    sec = pd.concat(parts)

    cols = ["record_id", "source", "published_at", "headline", "text"]
    todo = pd.concat([polygon[cols], gdelt[cols], sec[cols]]).sample(
        frac=1.0, random_state=args.seed
    )
    for c in GOLD_COLUMNS:
        todo[c] = ""
    todo.to_csv(out, index=False)
    print(
        f"wrote {out.relative_to(REPO_ROOT)}: {len(todo)} rows ({todo.source.value_counts().to_dict()})"
    )
    print("SEC rows are held-out or live filings; exclude labeled rows from any future retraining.")


if __name__ == "__main__":
    main()
