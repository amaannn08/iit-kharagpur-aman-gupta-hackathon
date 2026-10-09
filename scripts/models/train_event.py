#!/usr/bin/env python3
"""Train the event classifier v2 from committed real data and write models/event_v2.*.

Training data (all committed under data/):
  - train/hf_fin_topic/topic_train.csv: 16,990 real labeled financial tweets (MIT), mapped to
    the PS event classes; topics with no PS equivalent become OTHER
  - train/sec_8k/items.csv: real 8-K item statements (CYBER, CREDIT); 20% of filings held out
  - weak labels: real Polygon/tweet headlines matching strict SUPPLY_CHAIN / CYBER patterns
  - train/synthetic_seeds.csv: hand-written CYBER / SUPPLY_CHAIN examples (flagged synthetic)

Evaluation: train/hf_fin_topic/topic_valid.csv (4,117 held-out real tweets, never used for
fitting or threshold selection) and the held-out 8-K filings.
The abstention threshold is chosen on a dev split carved from the training data.

Usage: uv run python scripts/models/train_event.py
"""

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATA = REPO_ROOT / "data"
MODELS = REPO_ROOT / "models"
sys.path.insert(0, str(REPO_ROOT / "src"))

from sentinel.nlp.events import (  # noqa: E402
    TOPIC_TO_PS_CLASS,
    clean_for_classifier,
    ps_aligned_label,
)

PS_CLASSES = sorted(set(TOPIC_TO_PS_CLASS.values()))  # the 8 classes with real labels
TARGET_PRECISION = 0.90
SEED = 42

# Strict labeling functions for classes the public tweet datasets do not cover.
WEAK_PATTERNS = {
    "SUPPLY_CHAIN": re.compile(
        r"\b(supply[- ]chain (disruption|issues?|problems?|crisis|bottlenecks?|constraints?|woes)|"
        r"(chip|semiconductor|parts|component) shortages?|port (congestion|strike|closures?)|"
        r"dockworkers?|shipping (delays?|disruptions?)|production (halt|halted|shutdown|suspended)|"
        r"plant (shutdown|closure|fire)|force majeure|logistics (disruption|delays?))\b",
        re.I,
    ),
    "CYBER": re.compile(
        r"\b(ransomware|cyber ?attacks?|data breach(es)?|hack(ed|ers)|cybersecurity incident|"
        r"security breach|malware|zero-day)\b",
        re.I,
    ),
}
WEAK_CAP = 400


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def weak_labeled_headlines() -> pd.DataFrame:
    news = pd.read_csv(DATA / "real" / "polygon_news" / "polygon_news.csv")
    social = pd.read_csv(DATA / "real" / "stock_tweets" / "sample.csv")
    texts = pd.concat([news.headline.fillna(""), social.text.fillna("")], ignore_index=True)
    rows = []
    for label, pattern in WEAK_PATTERNS.items():
        hits = [t for t in texts if pattern.search(t)]
        rows += [(t, label) for t in hits[:WEAK_CAP]]
    return pd.DataFrame(rows, columns=["text", "y"])


def build_model():
    return make_pipeline(
        TfidfVectorizer(
            ngram_range=(1, 2), min_df=2, sublinear_tf=True, max_features=60_000, dtype=np.float32
        ),
        CalibratedClassifierCV(
            LogisticRegression(C=8, max_iter=3000, class_weight="balanced", random_state=SEED),
            method="isotonic",
            cv=3,
        ),
    )


def choose_threshold(model, x_dev, y_dev):
    """Smallest confidence threshold whose non-OTHER predictions reach TARGET_PRECISION."""
    proba = model.predict_proba(x_dev)
    pred = model.classes_[proba.argmax(1)]
    conf = proba.max(1)
    y_dev = np.asarray(y_dev)
    for thr in np.round(np.arange(0.30, 0.96, 0.05), 2):
        keep = (conf >= thr) & (pred != "OTHER")
        if keep.sum() and (pred[keep] == y_dev[keep]).mean() >= TARGET_PRECISION:
            return float(thr)
    return 0.95


def abstention_stats(model, x, y, thr):
    proba = model.predict_proba(x)
    pred = model.classes_[proba.argmax(1)]
    conf = proba.max(1)
    y = np.asarray(y)
    keep = (conf >= thr) & (pred != "OTHER")
    positives = y != "OTHER"
    return {
        "precision": round(float((pred[keep] == y[keep]).mean()), 4),
        "coverage": round(float(keep.sum() / max(positives.sum(), 1)), 4),
    }


def main() -> None:
    topic_train = DATA / "train" / "hf_fin_topic" / "topic_train.csv"
    topic_valid = DATA / "train" / "hf_fin_topic" / "topic_valid.csv"
    sec_path = DATA / "train" / "sec_8k" / "items.csv"
    seeds_path = DATA / "train" / "synthetic_seeds.csv"

    tr = pd.read_csv(topic_train)
    va = pd.read_csv(topic_valid)
    for d in (tr, va):
        d["text"] = d.text.map(clean_for_classifier)
        d["y_plain"] = d.label.map(TOPIC_TO_PS_CLASS).fillna("OTHER")
        d["y"] = [ps_aligned_label(lab, t) for lab, t in zip(d.label, d.text)]

    sec = pd.read_csv(sec_path)
    sec_train_ids, sec_test_ids = train_test_split(
        np.asarray(sorted(sec.accession.unique()), dtype=object), test_size=0.2, random_state=SEED
    )
    sec["text"] = sec.text.map(clean_for_classifier)
    sec_train = sec[sec.accession.isin(sec_train_ids)].rename(columns={"label": "y"})
    sec_test = sec[sec.accession.isin(sec_test_ids)].rename(columns={"label": "y"})

    weak = weak_labeled_headlines()
    weak["text"] = weak.text.map(clean_for_classifier)
    seeds = pd.read_csv(seeds_path)
    seeds = seeds[seeds.label.isin(["CYBER", "SUPPLY_CHAIN"])].rename(columns={"label": "y"})

    train_all = pd.concat(
        [tr[["text", "y"]], sec_train[["text", "y"]], weak, pd.concat([seeds[["text", "y"]]] * 5)],
        ignore_index=True,
    )
    fit_df, dev_df = train_test_split(
        train_all, test_size=0.1, random_state=SEED, stratify=train_all.y
    )

    model = build_model().fit(fit_df.text, fit_df.y)
    threshold = choose_threshold(model, dev_df.text, dev_df.y)

    pred_va = model.predict(va.text)
    report = classification_report(va.y, pred_va, output_dict=True, zero_division=0)
    sec_pred = model.predict(sec_test.text)
    metrics = {
        "hf_topic_valid": {
            "n": int(len(va)),
            "label_mapping": "ps_aligned (see sentinel.nlp.events.ps_aligned_label)",
            "macro_f1_8_ps_classes": round(
                f1_score(va.y, pred_va, labels=PS_CLASSES, average="macro"), 4
            ),
            "macro_f1_8_ps_classes_plain_topic_mapping": round(
                f1_score(va.y_plain, pred_va, labels=PS_CLASSES, average="macro"), 4
            ),
            "relabeled_rows": int((va.y != va.y_plain).sum()),
            "macro_f1_incl_other": round(f1_score(va.y, pred_va, average="macro"), 4),
            "per_class": {
                c: {k: round(v, 4) for k, v in report[c].items()} for c in PS_CLASSES + ["OTHER"]
            },
            "abstention_at_threshold": abstention_stats(model, va.text, va.y, threshold),
        },
        "sec_8k_heldout_filings": {
            "n": int(len(sec_test)),
            "recall_by_class": {
                c: round(float((sec_pred[sec_test.y.values == c] == c).mean()), 4)
                for c in sorted(sec_test.y.unique())
            },
        },
    }
    card = {
        "model": "event_v2",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "algorithm": "TF-IDF (1-2 gram, 60k) + isotonic-calibrated logistic regression",
        "classes": list(model.classes_),
        "abstain_threshold": threshold,
        "reproducibility": "metrics reproduce to 4 d.p.; artifact bytes can differ between runs "
        "because multithreaded BLAS changes float rounding in the solver",
        "threshold_selection": f"smallest threshold with precision >= {TARGET_PRECISION} on a 10% dev split of training data",
        "topic_to_ps_class": {str(k): v for k, v in TOPIC_TO_PS_CLASS.items()},
        "training_rows": {
            "hf_topic_train": int(len(tr)),
            "hf_topic_train_relabeled_by_ps_mapping": int((tr.y != tr.y_plain).sum()),
            "sec_8k_train": int(len(sec_train)),
            "weak_labeled_real_headlines": weak.y.value_counts().to_dict(),
            "synthetic_seeds_x5": seeds.y.value_counts().to_dict(),
        },
        "data_sha256": {
            str(p.relative_to(REPO_ROOT)): sha256(p)
            for p in (topic_train, topic_valid, sec_path, seeds_path)
        },
        "metrics": metrics,
    }
    # stop_words_ is introspection-only (sklearn docs) and is a set, whose pickle order varies
    # per process: drop it so the committed artifact is byte-reproducible and smaller.
    if hasattr(model.steps[0][1], "stop_words_"):
        delattr(model.steps[0][1], "stop_words_")
    MODELS.mkdir(exist_ok=True)
    joblib.dump(model, MODELS / "event_v2.joblib", compress=3)
    card["model_sha256"] = sha256(MODELS / "event_v2.joblib")
    (MODELS / "event_v2.card.json").write_text(json.dumps(card, indent=1) + "\n")
    print(json.dumps({"threshold": threshold, **metrics}, indent=1))


if __name__ == "__main__":
    main()
