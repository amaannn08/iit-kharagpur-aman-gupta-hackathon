"""Tests for human labeling CLI utility and agreement scoring."""

import importlib.util
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location(
    "label_cli", REPO_ROOT / "scripts" / "eval" / "label_cli.py"
)
label_cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(label_cli)


def test_load_stratified_candidates():
    candidates = label_cli.load_stratified_candidates(seed=42)
    assert len(candidates) >= 100
    sources = {c["source_id"] for c in candidates}
    assert "polygon_news" in sources
    assert any("gdelt" in s for s in sources)
    assert "sec_8k" in sources


def test_compute_agreement_metrics():
    df1 = pd.DataFrame(
        [
            {
                "record_id": "r1",
                "gold_event_class": "CREDIT",
                "gold_severity_score": 8,
            },
            {
                "record_id": "r2",
                "gold_event_class": "MACRO",
                "gold_severity_score": 6,
            },
            {
                "record_id": "r3",
                "gold_event_class": "EARNINGS",
                "gold_severity_score": 3,
            },
        ]
    )
    df2 = pd.DataFrame(
        [
            {
                "record_id": "r1",
                "gold_event_class": "CREDIT",
                "gold_severity_score": 8,
            },
            {
                "record_id": "r2",
                "gold_event_class": "MACRO",
                "gold_severity_score": 7,
            },
            {
                "record_id": "r3",
                "gold_event_class": "EARNINGS",
                "gold_severity_score": 3,
            },
        ]
    )
    ke, ks, mae = label_cli.compute_agreement(df1, df2)
    assert ke == 1.0  # perfect event match
    assert ks > 0.8  # close severity match
    assert abs(mae - 0.333) < 0.05
