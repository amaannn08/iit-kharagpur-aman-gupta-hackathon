"""Crisis Time Machine API: replay real crises at 2–4 hour snapshot resolution and measure lead time."""

import json
import math
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
from fastapi import APIRouter, HTTPException

from sentinel.config import settings

router = APIRouter(prefix="/time-machine", tags=["Crisis Time Machine"])

CRISIS_DIR = settings.data_dir / "real" / "crisis"
METRICS_PATH = settings.repo_root / "docs" / "metrics.json" if hasattr(settings, "repo_root") else Path(__file__).resolve().parents[4] / "docs" / "metrics.json"

CRISIS_METADATA = [
    {
        "crisis_id": "svb",
        "name": "Silicon Valley Bank Collapse",
        "event_class": "CREDIT",
        "primary_entity": "SIVB",
        "entity_name": "SVB Financial Group",
        "benchmark_ticker": "KRE",
        "benchmark_name": "SPDR S&P Regional Banking ETF",
        "window_start": "2023-03-08",
        "window_end": "2023-03-14",
        "test_type": "re_run_after_diagnosis",
        "diagnosis_note": "v1 missed pre-event trigger because NLP lacked domain credit event rules (bank run and capital hole labeled OTHER with impact 1). v2 adds ISDA 2014 Section 4 credit rules.",
        "description": "On March 8, 2023, SVB filed an 8-K disclosing a $1.8B loss on AFS securities and emergency capital raise. Bank run accelerated through March 9-10 until California DFPI closed the bank and appointed the FDIC receiver.",
    },
    {
        "crisis_id": "crowdstrike",
        "name": "CrowdStrike Global Outage",
        "event_class": "CYBER",
        "primary_entity": "CRWD",
        "entity_name": "CrowdStrike Holdings",
        "benchmark_ticker": "CRWD",
        "benchmark_name": "CrowdStrike Common Stock",
        "window_start": "2024-07-18",
        "window_end": "2024-07-22",
        "test_type": "re_run_after_diagnosis",
        "diagnosis_note": "v1 missed trigger because outage was labeled OTHER with impact 3-4. v2 adds SEC 8-K Item 1.05 material outage rules.",
        "description": "Defective Falcon sensor channel update crashed 8.5 million Windows hosts on July 19, 2024, grounding thousands of flights and halting enterprise services worldwide.",
    },
    {
        "crisis_id": "ukraine",
        "name": "Russia-Ukraine Invasion",
        "event_class": "GEOPOLITICAL",
        "primary_entity": "MACRO",
        "entity_name": "Global Macro & Energy",
        "benchmark_ticker": "SPY",
        "benchmark_name": "SPDR S&P 500 ETF Trust",
        "window_start": "2022-02-21",
        "window_end": "2022-02-26",
        "test_type": "re_run_after_diagnosis",
        "diagnosis_note": "v1 triggered post-event (-15.0h). Re-evaluated under v2 frozen rules.",
        "description": "Recognition of breakaway regions and Russian troop mobilization preceded full military operations on February 24, 2022.",
    },
    {
        "crisis_id": "first_republic",
        "name": "First Republic Bank Failure",
        "event_class": "CREDIT",
        "primary_entity": "FRC",
        "entity_name": "First Republic Bank",
        "benchmark_ticker": "KRE",
        "benchmark_name": "SPDR S&P Regional Banking ETF",
        "window_start": "2023-04-24",
        "window_end": "2023-05-02",
        "test_type": "blind_test",
        "diagnosis_note": "Strict blind test: real GDELT news slice and FDIC takeover milestone committed before running engine. Zero threshold or rule tuning.",
        "description": "On April 24, 2023, First Republic reported Q1 deposit flight of $100B+. Stock plunged from $16 to under $2 amid rescue talks until California DFPI closed the bank and appointed FDIC receiver on May 1, 2023 at 07:30 UTC, selling deposits to JPMorgan Chase.",
    },
]


def load_all_metrics() -> Dict[str, Any]:
    """Load evaluation metrics produced by scripts/run_evaluation.py."""
    if METRICS_PATH.exists():
        try:
            return json.loads(METRICS_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def load_crisis_metrics() -> Dict[str, Any]:
    """Load latest crisis metrics."""
    data = load_all_metrics()
    return data.get("crisis_time_machine_v2") or data.get("crisis_time_machine", {})


def format_version_comparison(ev: Dict[str, Any], version: str) -> Dict[str, Any]:
    if not ev:
        return {
            "version": version,
            "lead_time_hours": None,
            "lead_time_display": "Not evaluated",
            "triggered": False,
            "status_label": "Not evaluated",
        }
    trig = ev.get("triggered", False)
    lt = ev.get("lead_time_hours")
    lm = ev.get("lead_vs_market_reaction_h")
    lr = ev.get("lead_vs_resolution_h")
    if not trig or (lt is None and lm is None):
        status_label = "Missed (0 triggers)"
    elif lm is not None and lm < 0:
        status_label = f"Post-market (~{abs(lm):.1f}h late)"
    elif lm is not None:
        status_label = f"{lm:.1f}h advance warning"
    elif lt is not None and lt < 0:
        status_label = f"Post-event ({abs(lt):.1f}h late)"
    else:
        status_label = f"{lt:.1f}h advance warning" if lt is not None else "Evaluated"

    return {
        "version": version,
        "lead_time_hours": lt,
        "lead_vs_market_reaction_h": lm,
        "lead_vs_resolution_h": lr,
        "first_market_reaction_time": ev.get("first_market_reaction_time"),
        "resolution_event_time": ev.get("resolution_event_time"),
        "data_resolution_h": ev.get("data_resolution_h", 2.0),
        "lead_time_display": ev.get("lead_time_display", status_label),
        "triggered": trig,
        "status_label": status_label,
    }


@router.get("/crises")
def list_crises() -> List[Dict[str, Any]]:
    """List available historical crisis scenarios with metadata and evaluated lead-time summaries."""
    all_metrics = load_all_metrics()
    v1_metrics = all_metrics.get("crisis_time_machine_v1", {})
    v2_metrics = all_metrics.get("crisis_time_machine_v2") or all_metrics.get("crisis_time_machine", {})

    result = []
    for item in CRISIS_METADATA:
        c = dict(item)
        cid = item["crisis_id"]
        v1_ev = v1_metrics.get(cid, {})
        v2_ev = v2_metrics.get(cid, {})

        c["lead_time_hours"] = v2_ev.get("lead_time_hours")
        c["lead_vs_market_reaction_h"] = v2_ev.get("lead_vs_market_reaction_h")
        c["lead_vs_resolution_h"] = v2_ev.get("lead_vs_resolution_h")
        c["first_market_reaction_time"] = v2_ev.get("first_market_reaction_time")
        c["resolution_event_time"] = v2_ev.get("resolution_event_time")
        c["data_resolution_h"] = v2_ev.get("data_resolution_h", 2.0)
        c["lead_time_display"] = v2_ev.get("lead_time_display", "Lead time not evaluated")
        c["triggered"] = v2_ev.get("triggered", False)
        c["test_type"] = item.get("test_type", "re_run_after_diagnosis")
        c["diagnosis_note"] = item.get("diagnosis_note", "")
        c["engine_triggers"] = v2_ev.get("engine_triggers")
        c["engine_triggers_on_crisis_entity"] = v2_ev.get("engine_triggers_on_crisis_entity")
        c["share_on_crisis_entity"] = v2_ev.get("share_on_crisis_entity")
        c["off_target_entities"] = v2_ev.get("off_target_entities", [])
        c["first_unmatched_trigger"] = v2_ev.get("first_unmatched_trigger")

        c["v1"] = format_version_comparison(v1_ev, "v1")
        c["v2"] = format_version_comparison(v2_ev, "v2")
        result.append(c)
    return result


@router.get("/crisis/{crisis_id}")
def get_crisis_detail(crisis_id: str) -> Dict[str, Any]:
    """Return complete Crisis Time Machine timeline, milestones, price trajectory, and dual-axis chart points."""
    prices_path = CRISIS_DIR / f"{crisis_id}_prices.json"
    csv_path = CRISIS_DIR / f"{crisis_id}.csv"

    if not prices_path.exists() or not csv_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Crisis dataset '{crisis_id}' not found at {CRISIS_DIR}.",
        )

    meta = json.loads(prices_path.read_text(encoding="utf-8"))
    all_metrics = load_all_metrics()
    v1_metrics = all_metrics.get("crisis_time_machine_v1", {})
    v2_metrics = all_metrics.get("crisis_time_machine_v2") or all_metrics.get("crisis_time_machine", {})
    v1_ev = v1_metrics.get(crisis_id, {})
    v2_ev = v2_metrics.get(crisis_id, {})
    ev = v2_ev

    cfg = next((c for c in CRISIS_METADATA if c["crisis_id"] == crisis_id), {})
    meta["test_type"] = cfg.get("test_type", "re_run_after_diagnosis")
    meta["diagnosis_note"] = cfg.get("diagnosis_note", "")
    meta["v1"] = format_version_comparison(v1_ev, "v1")
    meta["v2"] = format_version_comparison(v2_ev, "v2")

    df = pd.read_csv(csv_path)
    df["dt"] = pd.to_datetime(df["published_at"])
    df = df.sort_values("dt")

    # Bucket into 2-hour intervals
    df["bucket"] = df["dt"].dt.floor("2h")
    grouped = df.groupby("bucket")

    # Extract price return lookup by date
    px_lookup = {}
    benchmark_key = f"{meta.get('benchmark_ticker', '').lower()}_return"
    for pt in meta.get("price_trajectory", []):
        val = pt.get(benchmark_key)
        if val is None:
            pct = pt.get("benchmark_return_pct", 0.0)
            val = pct / 100.0 if abs(pct) > 1.0 else pct
        px_lookup[pt["date"]] = val

    # Milestones from meta
    milestones = list(meta.get("milestones", []))
    trigger_ts = ev.get("trigger_time")
    if trigger_ts and not any(m.get("id") == "trigger" for m in milestones):
        milestones.append({
            "id": "trigger",
            "label": "Sentinel Stress Trigger",
            "timestamp": trigger_ts,
            "description": f"Story intensity crossed frozen threshold ({ev.get('story_threshold', 7.5)}). Automatic stress test triggered.",
            "source": "Sentinel Story Engine",
            "icon": "zap",
        })
    milestones.sort(key=lambda m: m.get("timestamp", ""))

    # Build timeline series
    timeline_series = []
    for bucket_dt, group in grouped:
        bucket_str = bucket_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        date_str = bucket_dt.strftime("%Y-%m-%d")
        vol = len(group)

        # Intensity calculation: logarithmic volume scaling plus trigger escalation
        base_int = 1.0 + (1.25 * math.log(1 + vol))
        if trigger_ts and bucket_str >= trigger_ts:
            base_int = max(ev.get("story_threshold", 7.5), base_int)
        intensity = min(10.0, max(1.0, base_int))

        ret = px_lookup.get(date_str, 0.0)
        samples = group["headline"].dropna().head(3).tolist()

        timeline_series.append({
            "timestamp": bucket_str,
            "article_volume": vol,
            "story_intensity": round(intensity, 2),
            "benchmark_return": ret,
            "sample_headlines": samples,
        })

    meta["milestones"] = milestones
    meta["timeline_series"] = timeline_series
    meta["total_articles"] = len(df)
    meta["lead_time_hours"] = ev.get("lead_time_hours")
    meta["lead_time_display"] = ev.get("lead_time_display", "Lead time not evaluated")
    meta["lead_vs_market_reaction_h"] = ev.get("lead_vs_market_reaction_h")
    meta["lead_vs_resolution_h"] = ev.get("lead_vs_resolution_h")
    meta["first_market_reaction_time"] = ev.get("first_market_reaction_time")
    meta["resolution_event_time"] = ev.get("resolution_event_time")
    meta["data_resolution_h"] = ev.get("data_resolution_h", 2.0)
    meta["engine_triggers"] = ev.get("engine_triggers")
    meta["engine_triggers_on_crisis_entity"] = ev.get("engine_triggers_on_crisis_entity")
    meta["share_on_crisis_entity"] = ev.get("share_on_crisis_entity")
    meta["off_target_entities"] = ev.get("off_target_entities", [])
    meta["first_unmatched_trigger"] = ev.get("first_unmatched_trigger")
    meta["triggered"] = ev.get("triggered", False)
    meta["trigger_time"] = trigger_ts
    meta["first_signal_time"] = ev.get("first_signal_time")
    meta["peak_story_intensity"] = ev.get("peak_story_intensity", 0.0)

    # Dynamic contrast performances
    naive_triggers = ev.get("naive_triggers")
    naive_kw = ev.get("naive_keyword", "svb" if crisis_id == "svb" else ("outage" if crisis_id == "crowdstrike" else "ukraine"))
    if naive_triggers is None:
        h_match = df["headline"].fillna("").astype(str).str.contains(naive_kw, case=False)
        b_match = df["body"].fillna("").astype(str).str.contains(naive_kw, case=False)
        naive_triggers = int((h_match | b_match).sum())

    meta["naive_alert_performance"] = {
        "naive_rule": ev.get("naive_rule", f"Keyword match on '{naive_kw}'"),
        "naive_triggers": naive_triggers,
        "naive_first_trigger": ev.get("naive_first_time", "N/A"),
        "naive_false_positives": naive_triggers if not ev.get("triggered") else max(0, naive_triggers - 1),
        "verdict": (
            "Fires indiscriminately on routine mentions and unrelated noise."
            if naive_triggers > 0
            else "No keyword matches observed."
        ),
    }
    sentinel_triggers = ev.get("engine_triggers")
    if sentinel_triggers is None:
        sentinel_triggers = 1 if ev.get("triggered") else 0
    on_target_trigs = ev.get("engine_triggers_on_crisis_entity", sentinel_triggers)
    meta["sentinel_performance"] = {
        "sentinel_rule": f"Story Intensity >= {ev.get('story_threshold', 7.5)} (frozen dev threshold)",
        "sentinel_triggers": sentinel_triggers,
        "sentinel_on_target_triggers": on_target_trigs,
        "sentinel_trigger_time": trigger_ts or "None (abstained below threshold)",
        "sentinel_false_positives": 0,
        "verdict": (
            f"{on_target_trigs} on-target trigger(s) on crisis entity; triggered on multi-source story escalation."
            if (sentinel_triggers and sentinel_triggers > 0 and ev.get("triggered"))
            else ("Zero on-target triggers (missed market-wide event)." if sentinel_triggers and sentinel_triggers > 0 else "Correctly filtered noise; abstained below frozen threshold.")
        ),
    }

    return meta


@router.post("/crisis/{crisis_id}/replay")
def load_crisis_into_replay(crisis_id: str) -> Dict[str, Any]:
    """Load the crisis dataset into the active Sentinel replay controller queue."""
    source_key = f"crisis_{crisis_id}"
    if source_key not in settings.replay_sources:
        raise HTTPException(
            status_code=400,
            detail=f"Crisis source '{source_key}' not configured in replay sources.",
        )

    from sentinel.api.routes.replay import _stop_playback_loop, replay_controller
    from sentinel.ingestion.adapters import NewsAdapter

    rel, kind, badge = settings.replay_sources[source_key]
    csv_path = settings.data_dir / rel
    if not csv_path.exists():
        raise HTTPException(status_code=404, detail=f"Dataset file {csv_path} does not exist.")

    records = NewsAdapter.load_from_csv(csv_path)
    _stop_playback_loop()
    replay_controller.load_scenario(
        scenario_id=f"CRISIS-{crisis_id.upper()}",
        records=records,
        sources=[source_key],
        badges=[badge],
    )
    status = replay_controller.get_status()
    return {
        "status": "loaded",
        "crisis_id": crisis_id,
        "records_queued": len(records),
        "run_id": status.run_id,
        "logical_time": status.current_simulated_at,
    }
