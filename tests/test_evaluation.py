"""Evaluation outputs (docs/metrics.json) meet the PRD targets on real held-out data."""

import importlib.util
import json

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
    assert m["market_impact"]["learned_oof_spearman_ci95"][0] > 0
    assert m["perf"]["latency_p95_s"] <= t["p95_latency_s"]
    assert m["perf"]["peak_rss_gb"] <= t["peak_rss_gb"]
    assert all(s["reconciled"] for s in m["stress"]["scenarios"].values())


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
