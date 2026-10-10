#!/usr/bin/env python3
"""Train the tier-1 sentiment model from committed real data and write models/sentiment_v2.*.

Training: data/train/hf_fin_sentiment/sent_train.csv (9,543 real labeled financial tweets, MIT)
          + data/train/phrasebank/sample.csv (600 rows, CC BY-NC-SA 3.0; training only)
          + weak negatives: real 8-K statements filed under item 1.03 (bankruptcy) or 1.05
            (material cybersecurity incident), which are adverse by definition. Item 2.04 is
            excluded because those statements include waivers and cures. Only the filings in
            the event model's training split are used.
Evaluation (never used for fitting):
  - data/train/hf_fin_sentiment/sent_valid.csv (2,388 held-out real tweets)
  - data/real/polygon_news: single-ticker articles vs the publisher's LLM sentiment (silver)

Usage: uv run python scripts/models/train_sentiment.py
"""

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import FeatureUnion, make_pipeline

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATA = REPO_ROOT / "data"
MODELS = REPO_ROOT / "models"
sys.path.insert(0, str(REPO_ROOT / "src"))

from sentinel.nlp.events import clean_for_classifier  # noqa: E402

HF_LABELS = {0: "negative", 1: "positive", 2: "neutral"}  # bearish / bullish / neutral


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def polygon_silver() -> pd.DataFrame:
    news = pd.read_csv(DATA / "real" / "polygon_news" / "polygon_news.csv")
    silver = pd.read_csv(DATA / "real" / "polygon_news" / "silver_labels.csv")
    silver = silver[silver.label_source == "polygon_llm_insight"]
    silver = silver[silver.sentiment.isin(["positive", "negative", "neutral"])]
    single = silver.groupby("record_id").filter(lambda g: len(g) == 1)  # unambiguous articles
    df = news.merge(single[["record_id", "sentiment"]], on="record_id")
    df["text"] = (df.headline.fillna("") + ". " + df.body.fillna("")).map(clean_for_classifier)
    return df


def main() -> None:
    train_path = DATA / "train" / "hf_fin_sentiment" / "sent_train.csv"
    valid_path = DATA / "train" / "hf_fin_sentiment" / "sent_valid.csv"
    pb_path = DATA / "train" / "phrasebank" / "sample.csv"

    tr = pd.read_csv(train_path)
    va = pd.read_csv(valid_path)
    pb = pd.read_csv(pb_path)
    for d in (tr, va):
        d["y"] = d.label.map(HF_LABELS)
        d["text"] = d.text.map(clean_for_classifier)
    sec = pd.read_csv(DATA / "train" / "sec_8k" / "items.csv")
    _, sec_test_ids = train_test_split(
        np.asarray(sorted(sec.accession.unique()), dtype=object), test_size=0.2, random_state=42
    )  # identical split to train_event.py
    sec_neg = sec[sec.item.astype(str).isin(["1.03", "1.05"]) & ~sec.accession.isin(sec_test_ids)]
    sec_neg = pd.DataFrame({"text": sec_neg.text.map(clean_for_classifier), "y": "negative"})
    train = pd.concat(
        [tr[["text", "y"]], pb.rename(columns={"label": "y"})[["text", "y"]], sec_neg]
    )

    features = FeatureUnion(
        [
            (
                "word",
                TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True, dtype=np.float32),
            ),
            (
                "char",
                TfidfVectorizer(
                    analyzer="char_wb",
                    ngram_range=(3, 5),
                    min_df=3,
                    sublinear_tf=True,
                    dtype=np.float32,
                ),
            ),
        ]
    )
    model = make_pipeline(
        features, LogisticRegression(C=6, max_iter=3000, class_weight="balanced", random_state=42)
    ).fit(train.text, train.y)
    for _, vec in model.steps[0][1].transformer_list:  # introspection-only, unordered set
        if hasattr(vec, "stop_words_"):
            delattr(vec, "stop_words_")

    pred = model.predict(va.text)
    report = classification_report(va.y, pred, output_dict=True, zero_division=0)
    news = polygon_silver()
    news_pred = model.predict(news.text)
    metrics = {
        "hf_sentiment_valid": {
            "n": int(len(va)),
            "macro_f1": round(f1_score(va.y, pred, average="macro"), 4),
            "per_class": {
                c: {k: round(v, 4) for k, v in report[c].items()}
                for c in ("negative", "neutral", "positive")
            },
        },
        "polygon_news_vs_llm_silver": {
            "n": int(len(news)),
            "macro_f1": round(f1_score(news.sentiment, news_pred, average="macro"), 4),
            "note": "silver labels are the publisher's LLM output, skewed positive; domain shift "
            "from tweets to news",
        },
    }
    MODELS.mkdir(exist_ok=True)
    out = MODELS / "sentiment_v2.joblib"
    joblib.dump(model, out, compress=3)
    card = {
        "model": "sentiment_v2",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "algorithm": "TF-IDF word (1-2) + char_wb (3-5) n-grams + balanced logistic regression",
        "score_definition": "P(positive) - P(negative), in [-1, 1]",
        "classes": list(model.classes_),
        "training_rows": {
            "hf_sentiment_train": int(len(tr)),
            "phrasebank_sample": int(len(pb)),
            "sec_8k_adverse_items_weak_negative": int(len(sec_neg)),
        },
        "data_sha256": {
            str(p.relative_to(REPO_ROOT)): sha256(p)
            for p in (train_path, valid_path, pb_path, DATA / "train" / "sec_8k" / "items.csv")
        },
        "reproducibility": "metrics reproduce to 4 d.p.; artifact bytes can differ between runs "
        "because multithreaded BLAS changes float rounding in the solver",
        "metrics": metrics,
        "model_sha256": sha256(out),
    }
    (MODELS / "sentiment_v2.card.json").write_text(json.dumps(card, indent=1) + "\n")
    print(json.dumps(metrics, indent=1))


if __name__ == "__main__":
    main()
