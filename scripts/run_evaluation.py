#!/usr/bin/env python3
"""S&P Sentinel evaluation suites: every reported number comes from here.

Suites (default: all):
  public_real          held-out REAL labeled data (HF twitter-financial-news topic/sentiment
                       valid splits), full runtime path, plus baselines on identical rows
  entity_polygon       entity linking on 5,548 real Polygon articles vs their tickers[]
  market_impact        impact validation vs real abnormal returns (models/impact_v2.card.json)
  sec_8k               held-out real 8-K filings (models/event_v2.card.json)
  stress               Module B: historical scenarios and the PS example shock
  module_a             Module A back-test summary (docs/module_a_backtest.json)
  perf                 throughput, per-record latency, peak memory
  synthetic_regression the 105-row author-written set (synthetic: regression check only)

Writes docs/metrics.json and docs/evaluation_report.md; --write-readme injects the headline
table into README.md between <!-- METRICS:START --> and <!-- METRICS:END -->.
Usage: uv run python scripts/run_evaluation.py [--suite public_real,perf] [--write-readme]
"""

import argparse
import csv
import hashlib
import importlib.util
import json
import re
import resource
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix, f1_score

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA = REPO_ROOT / "data"
DOCS = REPO_ROOT / "docs"
MODELS = REPO_ROOT / "models"
sys.path.insert(0, str(REPO_ROOT / "src"))

from sentinel.contracts.records import InputRecord, SourceType  # noqa: E402
from sentinel.nlp.engine import NLPEngine  # noqa: E402
from sentinel.nlp.entities import EntityLinker  # noqa: E402
from sentinel.nlp.events import (  # noqa: E402
    EventClassifier,
    clean_for_classifier,
    ps_aligned_label,
)
from sentinel.nlp.sentiment import FinBERTSentimentAnalyzer  # noqa: E402

PS_CLASSES = ["CREDIT", "EARNINGS", "GEOPOLITICAL", "MACRO", "M_AND_A", "PRODUCT", "REGULATORY"]
PS_CLASSES_WITH_LABELS = PS_CLASSES  # plus OTHER; CYBER/SUPPLY_CHAIN have no labels in this split
TARGETS = {
    "event_macro_f1": 0.70,
    "sentiment_macro_f1": 0.75,
    "entity_precision": 0.90,
    "entity_recall_mentioned": 0.90,
    "severity_mae": 1.5,
    "p95_latency_s": 2.0,
    "peak_rss_gb": 4.0,
    "false_trigger_rate_routine": 0.05,
    "trigger_precision_lift": 1.5,
}

BASELINE_KEYWORDS = [
    ("CREDIT", ("downgrade", "covenant", "default", "restructuring", "coupon payment", "bankruptcy")),
    ("MACRO", ("federal reserve", "treasury yield", "central bank", "inflation", "gdp", "interest rate")),
    ("GEOPOLITICAL", ("sanction", "tariff", "naval", "nationalize", "treaty", "war ")),
    ("SUPPLY_CHAIN", ("strike", "shortage", "force majeure", "cargo", "supply chain")),
    ("EARNINGS", ("net income", "revenue", "quarterly earnings", "operating profit", "ebitda", "eps")),
    ("M_AND_A", ("acquire", "acquisition", "merger", "takeover", "tender offer", "buyout")),
    ("REGULATORY", ("antitrust", "regulator", "consent order", "penalty", "lawsuit", "sec ")),
    ("CYBER", ("zero-day", "ransomware", "ddos", "breach", "cyber", "hack")),
    ("PRODUCT", ("fda", "recall", "clinical trial", "launch", "unveil")),
]  # fmt: skip


def baseline_event(text: str) -> str:
    t = text.lower()
    return next((cls for cls, kws in BASELINE_KEYWORDS if any(k in t for k in kws)), "OTHER")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def macro_f1(y_true, y_pred, labels) -> float:
    return round(
        float(f1_score(y_true, y_pred, labels=labels, average="macro", zero_division=0)), 4
    )


def bootstrap_ratio_ci(hits: int, total: int, n: int = 1000, seed: int = 42) -> List[float]:
    if total == 0:
        return [0.0, 0.0]
    rng = np.random.default_rng(seed)
    arr = np.array([1] * hits + [0] * (total - hits))
    means = [float(np.mean(rng.choice(arr, size=total, replace=True))) for _ in range(n)]
    return [round(float(np.percentile(means, 2.5)), 4), round(float(np.percentile(means, 97.5)), 4)]


def suite_public_real() -> Dict[str, Any]:
    topic = DATA / "train" / "hf_fin_topic" / "topic_valid.csv"
    sent = DATA / "train" / "hf_fin_sentiment" / "sent_valid.csv"
    tv = pd.read_csv(topic)
    gold = [ps_aligned_label(lab, clean_for_classifier(t)) for lab, t in zip(tv.label, tv.text)]
    clf = EventClassifier()
    pred = [clf.predict(t).label for t in tv.text]  # runtime path: threshold + gates
    model_only = list(clf.pipeline.predict([clean_for_classifier(t) for t in tv.text]))
    seed = EventClassifier(model_path=MODELS / "__none__.joblib")  # old seed baseline
    seed_pred = [seed.predict(t).label for t in tv.text]
    kw_pred = [baseline_event(t) for t in tv.text]
    labels = PS_CLASSES_WITH_LABELS
    fired = np.array([p != "OTHER" for p in pred])
    correct = np.array([p == g for p, g in zip(pred, gold)])
    event = {
        "dataset": "zeroshot/twitter-financial-news-topic valid (real, held out)",
        "n": int(len(tv)),
        "sha256": sha256(topic),
        "classes_scored": labels,
        "macro_f1_model": macro_f1(gold, model_only, labels),
        "macro_f1_runtime_with_gates_and_abstention": macro_f1(gold, pred, labels),
        "precision_when_fired": round(float(correct[fired].mean()), 4),
        "fired_rate": round(float(fired.mean()), 4),
        "baseline_keyword_macro_f1": macro_f1(gold, kw_pred, labels),
        "baseline_seed_classifier_macro_f1": macro_f1(gold, seed_pred, labels),
        "per_class_f1_model": {
            c: round(
                float(f1_score(gold, model_only, labels=[c], average="macro", zero_division=0)), 4
            )
            for c in labels
        },
        "confusion_matrix_model": {
            "labels": labels + ["OTHER"],
            "matrix": confusion_matrix(gold, model_only, labels=labels + ["OTHER"]).tolist(),
        },
    }
    sv = pd.read_csv(sent)
    sgold = sv.label.map({0: "negative", 1: "positive", 2: "neutral"})
    analyzer = FinBERTSentimentAnalyzer()
    lexicon = FinBERTSentimentAnalyzer(
        model_dir=MODELS / "__none__", tfidf_path=MODELS / "__none__"
    )
    spred = [analyzer.analyze(t).label for t in sv.text]
    slex = [lexicon.analyze(t).label for t in sv.text]
    sentiment = {
        "dataset": "zeroshot/twitter-financial-news-sentiment valid (real, held out)",
        "n": int(len(sv)),
        "sha256": sha256(sent),
        "backend": analyzer.backend,
        "macro_f1": macro_f1(sgold, spred, ["negative", "neutral", "positive"]),
        "baseline_lexicon_macro_f1": macro_f1(sgold, slex, ["negative", "neutral", "positive"]),
    }
    card = json.loads((MODELS / "sentiment_v2.card.json").read_text())
    sentiment["polygon_news_vs_llm_silver_macro_f1"] = card["metrics"][
        "polygon_news_vs_llm_silver"
    ]["macro_f1"]
    return {"event": event, "sentiment": sentiment}


def suite_entity_polygon() -> Dict[str, Any]:
    from sentinel.nlp.entities import CANONICAL_SHARE_CLASSES

    news = pd.read_csv(DATA / "real" / "polygon_news" / "polygon_news.csv")
    silver = pd.read_csv(DATA / "real" / "polygon_news" / "silver_labels.csv")
    gold = (
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

    tp = fp = fn = n = 0
    tp_ment = fn_ment = 0
    for r in news.itertuples():
        g = gold.get(r.record_id, set()) & universe
        if not g:
            continue
        n += 1
        text = f"{r.headline}. {r.body if isinstance(r.body, str) else ''}"
        p = {
            CANONICAL_SHARE_CLASSES.get(t, t)
            for t in linker.find_companies(text)
            if CANONICAL_SHARE_CLASSES.get(t, t) in universe
        }
        tp += len(p & g)
        fp += len(p - g)
        fn += len(g - p)
        g_ment = {t for t in g if is_mentioned(t, text)}
        tp_ment += len(p & g_ment)
        fn_ment += len(g_ment - p)

    return {
        "dataset": "Polygon 2023 news (real), gold = article tickers[] within the S&P 500 universe",
        "articles": n,
        "precision": round(tp / (tp + fp), 4),
        "recall": round(tp / (tp + fn), 4),
        "recall_all_tags": round(tp / (tp + fn), 4),
        "recall_mentioned": round(tp_ment / (tp_ment + fn_ment), 4) if (tp_ment + fn_ment) else 0.0,
    }


def suite_market_impact() -> Dict[str, Any]:
    return json.loads((MODELS / "impact_v2.card.json").read_text())["metrics"]


def suite_sec_8k() -> Dict[str, Any]:
    return json.loads((MODELS / "event_v2.card.json").read_text())["metrics"][
        "sec_8k_heldout_filings"
    ]


def suite_stress() -> Dict[str, Any]:
    from sentinel.stress.engine import StressEngine

    engine = StressEngine()
    out = {"funded_book_usd": round(engine.portfolio.total_funded_exposure, 2),
           "funded_by_sleeve_usd": engine.portfolio.sleeve_totals(), "scenarios": {}}  # fmt: skip
    for s in engine.list_scenarios():
        if not s["scenario_id"].startswith("HIST-"):
            continue
        r = engine.run_scenario(s["scenario_id"])
        out["scenarios"][s["scenario_id"]] = {
            "total_pnl_usd": r.total_pnl_usd,
            "pnl_pct_of_funded": round(r.total_pnl_usd / r.funded_baseline_value_usd, 4),
            "by_sleeve_usd": {x.sleeve: x.total_pnl_usd for x in r.sleeve_breakdown},
            "reconciled": r.reconciliation_passed,
        }
    ps = engine.run_custom_stress(equity_shock_pct=-0.10, benchmark_yield_shift_bps=200)
    out["ps_example_equities_-10pct_rates_+200bp"] = {
        "total_pnl_usd": ps.total_pnl_usd,
        "by_sleeve_usd": {x.sleeve: x.total_pnl_usd for x in ps.sleeve_breakdown},
        "derivative_mtm_change_usd": ps.derivative_mtm_change_usd,
        "reconciled": ps.reconciliation_passed,
    }
    return out


def suite_module_a() -> Dict[str, Any]:
    path = DOCS / "module_a_backtest.json"
    return json.loads(path.read_text()) if path.exists() else {"status": "not run"}


def suite_perf(n: int = 2000) -> Dict[str, Any]:
    news = pd.read_csv(DATA / "real" / "polygon_news" / "polygon_news.csv").head(n)
    engine = NLPEngine()
    lat: List[float] = []
    t0 = time.perf_counter()
    for r in news.itertuples():
        rec = InputRecord(record_id=r.record_id, source_id="perf", source_type=SourceType.NEWS,
                          text=f"{r.headline}. {r.body if isinstance(r.body, str) else ''}")  # fmt: skip
        s = time.perf_counter()
        engine.process_record_multi(rec, "perf")
        lat.append(time.perf_counter() - s)
    total = time.perf_counter() - t0
    rss_gb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024**2  # Linux: KB
    return {
        "records": len(lat),
        "records_per_s": round(len(lat) / total, 1),
        "latency_p50_s": round(float(np.percentile(lat, 50)), 4),
        "latency_p95_s": round(float(np.percentile(lat, 95)), 4),
        "peak_rss_gb": round(rss_gb, 3),
        "note": "single process, CPU, full pipeline (linking, sentiment, event, impact)",
    }


def suite_synthetic_regression() -> Dict[str, Any]:
    path = DATA / "eval" / "synthetic_regression.csv"
    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    engine = NLPEngine()
    ev_t, ev_p, s_t, s_p, sev_err = [], [], [], [], []
    for i, r in enumerate(rows):
        rec = InputRecord(record_id=f"syn-{i}", source_id="synthetic", source_type=SourceType.NEWS,
                          text=r["text"], is_synthetic=True)  # fmt: skip
        sig = engine.process_record(rec, "synthetic")
        ev_t.append(r["gold_event_class"].upper())
        ev_p.append(sig.event.label)
        s_t.append(r["gold_sentiment_label"].lower())
        s_p.append(sig.sentiment.label)
        sev_err.append(abs(sig.impact.score - int(r["gold_severity_score"])))
    return {
        "warning": "author-written synthetic set (same fictional universe as the demo); "
        "regression check only, never a quality claim",
        "n": len(rows),
        "event_macro_f1": macro_f1(ev_t, ev_p, sorted(set(ev_t))),
        "sentiment_macro_f1": macro_f1(s_t, s_p, ["negative", "neutral", "positive"]),
        "severity_mae": round(float(np.mean(sev_err)), 3),
    }


def suite_pipeline() -> Dict[str, Any]:
    from sentinel.nlp.impact_model import LearnedImpactModel
    from sentinel.nlp.severity import SeverityRubricEngine
    from sentinel.replay.dedup import ExactTextDeduplicator
    from sentinel.stress.engine import StressEngine

    # 1. Fit impact model on temporal training split (2023-01..2023-09)
    spec = importlib.util.spec_from_file_location(
        "train_impact", REPO_ROOT / "scripts" / "models" / "train_impact.py"
    )
    ti = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ti)

    feat_parquet = DATA / "market" / "impact_train_features.parquet"
    if feat_parquet.exists():
        feat_df = pd.read_parquet(feat_parquet)
    else:
        labels = pd.read_csv(DATA / "market" / "reaction_labels.csv")
        train_labels = labels[labels.reaction_date < "2023-10-01"]
        feat_df = ti.build_features(train_labels)

    bundle = ti.fit(feat_df)
    model = LearnedImpactModel(bundle)
    rubric = SeverityRubricEngine(impact_model=model)
    nlp_engine = NLPEngine(severity_engine=rubric)
    stress_engine = StressEngine()
    dedup = ExactTextDeduplicator()

    # 2. Load holdout reaction labels (2023-10..2023-12)
    labels = pd.read_csv(DATA / "market" / "reaction_labels.csv")
    holdout = labels[labels.reaction_date >= "2023-10-01"].copy()
    base_rate_z2 = float((holdout.abnormal_z.abs() >= 2.0).mean())
    base_rate_z3 = float((holdout.abnormal_z.abs() >= 3.0).mean())
    gold_high = holdout[holdout.abnormal_z.abs() >= 3.0]
    z_map = {(r.record_id, r.ticker): abs(r.abnormal_z) for r in holdout.itertuples()}

    # 3. Evaluate full pipeline on holdout articles from Polygon news (2023-10..2023-12)
    news = pd.read_csv(DATA / "real" / "polygon_news" / "polygon_news.csv")
    news["pub"] = pd.to_datetime(news.published_at)
    q4_news = news[(news.pub >= "2023-10-01") & (news.pub <= "2023-12-31")].copy()

    total_signals = 0
    eligible_signals = 0
    stress_triggers = 0
    matched_eligible = []
    captured_high = set()
    dup_records = 0
    dup_eligible = 0

    for r in q4_news.itertuples():
        text = f"{r.headline}. {r.body if isinstance(r.body, str) else ''}"
        decision = dedup.process(r.record_id, text)
        if decision.is_duplicate:
            dup_records += 1
        rec = InputRecord(
            record_id=r.record_id,
            source_id="polygon",
            source_type=SourceType.NEWS,
            text=text,
        )
        sigs = nlp_engine.process_record_multi(rec, "polygon")
        for s in sigs:
            total_signals += 1
            if s.eligible_for_action:
                eligible_signals += 1
                if decision.is_duplicate:
                    dup_eligible += 1
                key = (r.record_id, s.entity.ticker)
                if key in z_map:
                    z = z_map[key]
                    matched_eligible.append(z)
                    if z >= 3.0:
                        captured_high.add(key)
            if stress_engine.should_trigger(s):
                stress_triggers += 1

    # Precision & recall metrics
    n_mat = len(matched_eligible)
    prec_z2_hits = sum(z >= 2.0 for z in matched_eligible)
    prec_z2 = round(prec_z2_hits / n_mat, 4) if n_mat else 0.0
    prec_lift = round(prec_z2 / base_rate_z2, 2) if base_rate_z2 else 0.0
    prec_ci = bootstrap_ratio_ci(prec_z2_hits, n_mat)

    n_gold_high = len(gold_high)
    rec_hits = len(captured_high)
    recall_z3 = round(rec_hits / n_gold_high, 4) if n_gold_high else 0.0
    recall_ci = bootstrap_ratio_ci(rec_hits, n_gold_high)

    # 4. Evaluate routine false-trigger rates on 3 negative controls
    routine_counts = {}

    # 4a. Routine 8-Ks (gold OTHER/EARNINGS)
    s8k = pd.read_csv(DATA / "train" / "sec_8k" / "items.csv")
    routine_8k = s8k[s8k.label.isin(["OTHER", "EARNINGS"])]
    s8k_trigs = 0
    for r in routine_8k.itertuples():
        rec = InputRecord(
            record_id=r.record_id,
            source_id="8k",
            source_type=SourceType.NEWS,
            text=str(r.text),
        )
        for s in nlp_engine.process_record_multi(rec, "8k"):
            if stress_engine.should_trigger(s):
                s8k_trigs += 1
    routine_counts["sec_8k_routine"] = (s8k_trigs, len(routine_8k))

    # 4b. GDELT snapshot sample
    gd = pd.read_csv(DATA / "real" / "gdelt" / "snapshot.csv").head(1000)
    gd_trigs = 0
    for r in gd.itertuples():
        text = f"{r.headline}. {r.body if isinstance(r.body, str) else ''}"
        rec = InputRecord(
            record_id=r.record_id,
            source_id="gdelt",
            source_type=SourceType.NEWS,
            text=text,
        )
        for s in nlp_engine.process_record_multi(rec, "gdelt"):
            if stress_engine.should_trigger(s):
                gd_trigs += 1
    routine_counts["gdelt_snapshot"] = (gd_trigs, len(gd))

    # 4c. Social tweets sample (should be ~0 due to social filters)
    tw = pd.read_csv(DATA / "train" / "hf_fin_topic" / "topic_train.csv").head(2000)
    tw_trigs = 0
    for idx, r in enumerate(tw.itertuples()):
        rec = InputRecord(
            record_id=f"tw-{idx}",
            source_id="twitter",
            source_type=SourceType.SOCIAL,
            text=str(r.text),
        )
        for s in nlp_engine.process_record_multi(rec, "twitter"):
            if stress_engine.should_trigger(s):
                tw_trigs += 1
    routine_counts["social_tweets"] = (tw_trigs, len(tw))

    total_routine_trigs = sum(t for t, _ in routine_counts.values())
    total_routine_records = sum(n for _, n in routine_counts.values())
    false_trigger_rate_routine = round(total_routine_trigs / total_routine_records, 4)

    return {
        "dataset": "Polygon 2023 Q4 holdout + SEC 8-K routine + GDELT + Twitter controls",
        "train_window": "2023-01..2023-09",
        "holdout_window": "2023-10..2023-12",
        "holdout_articles": len(q4_news),
        "total_signals": total_signals,
        "actionable_signals": eligible_signals,
        "actionable_rate": round(eligible_signals / total_signals, 4) if total_signals else 0.0,
        "trigger_rate_per_1k_records": round(stress_triggers / (len(q4_news) / 1000), 2),
        "high_impact_recall": recall_z3,
        "high_impact_recall_ci95": recall_ci,
        "gold_base_rate_z3": round(base_rate_z3, 4),
        "gold_high_impact_events": n_gold_high,
        "trigger_precision_market": prec_z2,
        "trigger_precision_market_ci95": prec_ci,
        "trigger_precision_lift": prec_lift,
        "gold_base_rate_z2": round(base_rate_z2, 4),
        "false_trigger_rate_routine": false_trigger_rate_routine,
        "routine_eval_records": total_routine_records,
        "false_trigger_rates_by_source": {
            k: round(t / n, 4) for k, (t, n) in routine_counts.items()
        },
        "duplicate_records": dup_records,
        "duplicate_suppression": round(dup_records / len(q4_news), 4),
    }


SUITES = {
    "public_real": suite_public_real,
    "entity_polygon": suite_entity_polygon,
    "market_impact": suite_market_impact,
    "sec_8k": suite_sec_8k,
    "pipeline": suite_pipeline,
    "stress": suite_stress,
    "module_a": suite_module_a,
    "perf": suite_perf,
    "synthetic_regression": suite_synthetic_regression,
}


def headline_rows(m: Dict[str, Any]) -> List[List[str]]:
    rows = []
    if pr := m.get("public_real"):
        e, s = pr["event"], pr["sentiment"]
        rows.append([f"Event macro-F1, {e['n']:,} held-out real financial tweets",
                     f"{e['macro_f1_model']:.3f}", f">= {TARGETS['event_macro_f1']}",
                     f"keyword {e['baseline_keyword_macro_f1']:.3f} / old seed model {e['baseline_seed_classifier_macro_f1']:.3f}"])  # fmt: skip
        rows.append(
            [
                "Event, runtime path (abstention + evidence gates), same rows",
                f"F1 {e['macro_f1_runtime_with_gates_and_abstention']:.3f}, "
                f"precision {e['precision_when_fired']:.3f} when it fires",
                "precision first",
                f"fires on {e['fired_rate']:.0%} of rows (precision/recall trade-off)",
            ]
        )
        rows.append([f"Sentiment macro-F1, {s['n']:,} held-out real financial tweets",
                     f"{s['macro_f1']:.3f}", f">= {TARGETS['sentiment_macro_f1']}",
                     f"lexicon {s['baseline_lexicon_macro_f1']:.3f}"])  # fmt: skip
    if ent := m.get("entity_polygon"):
        rec_ment = ent.get("recall_mentioned", ent["recall"])
        rec_all = ent.get("recall_all_tags", ent["recall"])
        rows.append([
            f"Entity linking, {ent['articles']:,} real news articles",
            f"P {ent['precision']:.3f} / R {rec_ment:.3f} (mentioned)",
            f"P >= {TARGETS['entity_precision']}, R >= 0.90",
            f"all tags R {rec_all:.3f} (incl. unmentioned tags)",
        ])
    if mi := m.get("market_impact"):
        lo, hi = mi["learned_oof_spearman_ci95"]
        rows.append([f"Impact vs next-day abnormal return, {mi['events']:,} real events",
                     f"Spearman {mi['learned_oof_spearman']:.3f} [{lo:.3f}, {hi:.3f}]", "> 0",
                     f"rubric {mi['rubric_v1_spearman']:.3f}"])  # fmt: skip
    if pl := m.get("pipeline"):
        r_ci = pl["high_impact_recall_ci95"]
        p_ci = pl["trigger_precision_market_ci95"]
        rows.append([
            f"Pipeline temporal holdout (Q4 2023), {pl['holdout_articles']:,} articles",
            f"Precision lift {pl['trigger_precision_lift']:.2f}x ({pl['trigger_precision_market']:.1%} [{p_ci[0]:.1%}, {p_ci[1]:.1%}] vs base {pl['gold_base_rate_z2']:.1%})",
            f"> {TARGETS['trigger_precision_lift']}x lift",
            f"recall {pl['high_impact_recall']:.1%} [{r_ci[0]:.1%}, {r_ci[1]:.1%}] (|z|>=3)",
        ])
        rows.append([
            f"Routine false-trigger rate, {pl['routine_eval_records']:,} routine texts",
            f"{pl['false_trigger_rate_routine']:.2%}",
            f"<= {TARGETS['false_trigger_rate_routine']:.0%}",
            f"8-K {pl['false_trigger_rates_by_source']['sec_8k_routine']:.1%}, social {pl['false_trigger_rates_by_source']['social_tweets']:.1%}, gdelt {pl['false_trigger_rates_by_source']['gdelt_snapshot']:.1%}",
        ])
    if p := m.get("perf"):
        rows.append(["Latency per record (p95), CPU", f"{p['latency_p95_s']:.3f} s",
                     f"<= {TARGETS['p95_latency_s']} s", f"{p['records_per_s']:.0f} records/s"])  # fmt: skip
    return rows


def write_report(m: Dict[str, Any]) -> str:
    table = ["| Metric | Measured | Target | Comparison |", "|---|---|---|---|"]
    table += [f"| {' | '.join(r)} |" for r in headline_rows(m)]
    lines = ["# Evaluation report (generated by scripts/run_evaluation.py)", "",
             f"Generated: {m['generated_at']}", "", *table, "",
             "All raw values: [`docs/metrics.json`](metrics.json).", ""]  # fmt: skip
    for name, body in m.items():
        if name in ("generated_at", "targets"):
            continue
        lines += [f"## {name}", "", "```json", json.dumps(body, indent=1)[:6000], "```", ""]
    (DOCS / "evaluation_report.md").write_text("\n".join(lines))
    return "\n".join(table)


def inject_readme(table: str) -> None:
    readme = REPO_ROOT / "README.md"
    text = readme.read_text()
    start, end = "<!-- METRICS:START -->", "<!-- METRICS:END -->"
    if start not in text:
        print("README has no METRICS markers; skipped")
        return
    head, rest = text.split(start, 1)
    _, tail = rest.split(end, 1)
    readme.write_text(f"{head}{start}\n{table}\n{end}{tail}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--suite", default=",".join(SUITES))
    ap.add_argument("--write-readme", action="store_true")
    args = ap.parse_args()
    out_path = DOCS / "metrics.json"
    metrics: Dict[str, Any] = json.loads(out_path.read_text()) if out_path.exists() else {}
    for name in args.suite.split(","):
        t0 = time.time()
        metrics[name] = SUITES[name]()
        print(f"[eval] {name}: {time.time() - t0:.1f}s")
    metrics["generated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    metrics["targets"] = TARGETS
    out_path.write_text(json.dumps(metrics, indent=1) + "\n")
    table = write_report(metrics)
    if args.write_readme:
        inject_readme(table)
    print(table)


if __name__ == "__main__":
    main()
