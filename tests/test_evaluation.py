"""Evaluation outputs (docs/metrics.json) meet accuracy targets on real held-out data."""

import importlib.util
import json
from pathlib import Path

from sentinel.config import settings

_spec = importlib.util.spec_from_file_location(
    "run_evaluation", settings.base_dir / "scripts" / "run_evaluation.py"
)
run_evaluation = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(run_evaluation)


def _metrics():
    return json.loads((settings.base_dir / "docs" / "metrics.json").read_text())


def test_committed_metrics_meet_targets_on_real_data():
    m = _metrics()
    t = m["targets"]
    assert m["public_real"]["event"]["macro_f1_model"] >= t["event_macro_f1"]
    assert m["public_real"]["event"]["precision_when_fired"] >= 0.88
    assert m["public_real"]["sentiment"]["macro_f1"] >= t["sentiment_macro_f1"]
    assert m["entity_polygon"]["precision"] >= t["entity_precision"]
    assert m["entity_polygon"]["recall_mentioned"] >= t["entity_recall_mentioned"]
    assert m["market_impact"]["learned_oof_spearman_ci95"][0] > 0
    assert m["perf"]["latency_p95_s"] <= t["p95_latency_s"]
    assert m["perf"]["peak_rss_gb"] <= t["peak_rss_gb"]
    assert all(s["reconciled"] for s in m["stress"]["scenarios"].values())
    pl = m["pipeline"]
    assert pl["false_trigger_rate_max_source"] <= t["false_trigger_rate_routine"]
    assert pl["eligible_vs_market"]["lift_vs_base_rate"] > t["trigger_precision_lift"]
    nh = m["news_holdout"]
    assert nh["sha256_matches_frozen"]
    assert nh["false_auto_trigger_rate"] <= t["false_trigger_rate_routine"]


def test_holdout_label_provenance_is_honest():
    nh = _metrics()["news_holdout"]
    assert nh["label_source"] in ("human", "ai_agent")
    if nh["label_source"] != "human":
        assert not nh["human_reviewed"]
    # agreement is only reported from a genuine second labeling pass
    relabel = Path(__file__).resolve().parent.parent / "data" / "eval" / "holdout_v2_news.relabel.csv"
    assert (nh["annotator_agreement_kappa"] is None) == (not relabel.exists())


def test_synthetic_set_is_labeled_regression_only():
    assert "regression check only" in _metrics()["synthetic_regression"]["warning"]


def test_readme_injection_replaces_only_marked_block(tmp_path, monkeypatch):
    readme = tmp_path / "README.md"
    readme.write_text("intro\n<!-- METRICS:START -->\nold\n<!-- METRICS:END -->\noutro\n")
    monkeypatch.setattr(run_evaluation, "REPO_ROOT", tmp_path)
    run_evaluation.inject_readme("| new |")
    assert (
        readme.read_text()
        == "intro\n<!-- METRICS:START -->\n| new |\n<!-- METRICS:END -->\noutro\n"
    )
