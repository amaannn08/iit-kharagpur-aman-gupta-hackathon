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


def _rows(ids, ts=None, cls="CREDIT"):
    import pandas as pd

    d = pd.DataFrame({"record_id": ids, "gold_event_class": cls, "gold_severity_score": 5})
    if ts is not None:
        d["labeled_at"] = ts
    return d


def test_copied_subset_of_holdout_gives_no_agreement_rows():
    ref = _rows(["a", "b", "c"])
    rows, reason = label_cli.validate_relabel(ref, ref.head(2))  # `head -n` copy of the holdout
    assert rows.empty and "labeled_at" in reason


def test_relabel_must_come_later_than_the_first_pass():
    ref = _rows(["a", "b"], ts=["2026-10-10T10:00:00+00:00"] * 2)
    same_day = _rows(["a", "b"], ts=["2026-10-10T11:00:00+00:00"] * 2)
    next_day = _rows(["a", "b"], ts=["2026-10-11T11:00:00+00:00"] * 2)
    assert label_cli.validate_relabel(ref, same_day)[0].empty
    assert len(label_cli.validate_relabel(ref, next_day)[0]) == 2


def test_session_refuses_to_append_to_foreign_file(tmp_path):
    import pytest

    f = tmp_path / "x.csv"
    f.write_text("record_id,gold_event_class\nr1,OTHER\n")
    with pytest.raises(SystemExit):
        label_cli.append_annotation({"record_id": "r2"}, f)
