"""Tests for scripts/data/build_manifest.py (idempotent, never keeps stale entries)."""

import importlib.util
import json

from sentinel.config import settings

_spec = importlib.util.spec_from_file_location(
    "build_manifest", settings.base_dir / "scripts" / "data" / "build_manifest.py"
)
build_manifest = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build_manifest)


def _point_at(tmp_path, monkeypatch):
    (tmp_path / "data").mkdir()
    manifest = tmp_path / "data" / "manifest.json"
    manifest.write_text(json.dumps({"manifest_version": "1.0", "datasets": []}))
    monkeypatch.setattr(build_manifest, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(build_manifest, "MANIFEST_PATH", manifest)
    return manifest


def test_register_then_rebuild_drops_missing_files(tmp_path, monkeypatch):
    manifest = _point_at(tmp_path, monkeypatch)
    csv_path = tmp_path / "data" / "sample.csv"
    csv_path.write_text('record_id,text\nr1,"multi\nline"\nr2,b\n')

    entry = build_manifest.register_dataset(
        "data/sample.csv", "test sample", "MIT", is_synthetic=False, source="unit-test"
    )
    assert entry["record_count"] == 2  # quoted newline is one record
    assert len(entry["sha256"]) == 64

    # re-registering the same path replaces rather than duplicates
    build_manifest.register_dataset("data/sample.csv", "again", "MIT", is_synthetic=False)
    assert len(json.loads(manifest.read_text())["datasets"]) == 1

    csv_path.unlink()
    assert build_manifest.update_manifest()
    assert json.loads(manifest.read_text())["datasets"] == []
