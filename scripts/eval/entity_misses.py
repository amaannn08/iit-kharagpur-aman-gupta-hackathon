#!/usr/bin/env python3
"""Inspect and tabulate real entity extraction misses against Polygon silver labels."""

import re
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from sentinel.nlp.entities import CANONICAL_SHARE_CLASSES, EntityLinker  # noqa: E402

DATA = REPO_ROOT / "data"


def main() -> None:
    news = pd.read_csv(DATA / "real" / "polygon_news" / "polygon_news.csv")
    silver = pd.read_csv(DATA / "real" / "polygon_news" / "silver_labels.csv")
    gold_raw = (
        silver[silver.label_source == "polygon_tickers"]
        .groupby("record_id")
        .ticker.apply(
            lambda s: {
                CANONICAL_SHARE_CLASSES.get(t.replace(".", "-"), t.replace(".", "-")) for t in s
            }
        )
    )
    linker = EntityLinker()
    universe = {
        CANONICAL_SHARE_CLASSES.get(t, t)
        for t, e in linker.entities.items()
        if not e.is_synthetic
    }

    def is_mentioned(ticker: str, text: str) -> bool:
        ke = linker.entities.get(ticker)
        if not ke:
            return False
        if re.search(rf"(\$|\b){re.escape(ticker)}\b", text, re.I):
            return True
        if ke.canonical_name.lower() in text.lower():
            return True
        for a in ke.aliases:
            if len(a) >= 3 and a.lower() in text.lower():
                return True
        return False

    rows = []
    unmentioned_count = 0
    total_gold = 0

    for r in news.itertuples():
        g = gold_raw.get(r.record_id, set()) & universe
        if not g:
            continue
        text = f"{r.headline}. {r.body if isinstance(r.body, str) else ''}"
        p = {
            CANONICAL_SHARE_CLASSES.get(t, t)
            for t in linker.find_companies(text)
            if CANONICAL_SHARE_CLASSES.get(t, t) in universe
        }
        for t in g:
            total_gold += 1
            if not is_mentioned(t, text):
                unmentioned_count += 1
            elif t not in p:
                rows.append(
                    {
                        "record_id": r.record_id,
                        "ticker": t,
                        "canonical_name": linker.entities[t].canonical_name,
                        "headline": r.headline[:70],
                    }
                )

    df = pd.DataFrame(rows)
    print(f"Total gold mentions in universe: {total_gold}")
    print(f"Unmentioned related-ticker tags (Polygon metadata): {unmentioned_count} ({unmentioned_count/total_gold:.1%})")
    print(f"Mentioned misses: {len(df)}")
    print("\n--- Misses by Ticker ---")
    if not df.empty:
        print(df.ticker.value_counts().to_string())
        print("\n--- Detailed Miss Table ---")
        print(df.to_string())


if __name__ == "__main__":
    main()
