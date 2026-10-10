#!/usr/bin/env python3
"""Idempotent manifest builder for S&P Sentinel datasets.

Recomputes sha256, byte_size and record_count for every dataset in data/manifest.json
from the files on disk. Entries whose file no longer exists are dropped (never kept stale).
Converters call ``register_dataset`` to add or update an entry with its provenance.
"""

import csv
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
MANIFEST_PATH = REPO_ROOT / "data" / "manifest.json"


def _count_records(file_path: Path) -> int:
    if file_path.suffix == ".csv":
        csv.field_size_limit(sys.maxsize)
        with open(file_path, "r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            next(reader, None)
            return sum(1 for _ in reader)
    if file_path.suffix == ".json":
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return len(data)
        if isinstance(data, dict):
            return len(data.get("positions", [data]))
    return 1


def _refresh(entry: Dict[str, Any]) -> Dict[str, Any]:
    file_path = REPO_ROOT / entry["file_path"]
    content = file_path.read_bytes()
    entry["byte_size"] = len(content)
    entry["sha256"] = hashlib.sha256(content).hexdigest()
    entry["record_count"] = _count_records(file_path)
    return entry


def _load() -> Dict[str, Any]:
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(manifest: Dict[str, Any]) -> None:
    manifest["updated_at"] = datetime.now(timezone.utc).isoformat()
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")


def register_dataset(
    file_path: str,
    description: str,
    license_name: str,
    is_synthetic: bool,
    source: Optional[str] = None,
    derived_from: Optional[List[str]] = None,
    columns: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Add or update one dataset entry (keyed by repo-relative file_path) and save the manifest."""
    manifest = _load()
    entry: Dict[str, Any] = {
        "file_path": file_path,
        "format": Path(file_path).suffix.lstrip("."),
        "description": description,
        "is_synthetic": is_synthetic,
        "license": license_name,
        "primary_keys": ["record_id"] if file_path.endswith(".csv") else [],
    }
    if source:
        entry["source"] = source
    if derived_from:
        entry["derived_from"] = derived_from
    if columns:
        entry["columns"] = columns
    _refresh(entry)
    others = [d for d in manifest.get("datasets", []) if d["file_path"] != file_path]
    manifest["datasets"] = others + [entry]
    _save(manifest)
    return entry


def update_manifest() -> bool:
    if not MANIFEST_PATH.exists():
        print(f"Error: Manifest not found at {MANIFEST_PATH}", file=sys.stderr)
        return False

    manifest = _load()
    kept = []
    for ds in manifest.get("datasets", []):
        rel_path = ds["file_path"]
        if not (REPO_ROOT / rel_path).exists():
            print(f"Removed stale entry (file missing): {rel_path}")
            continue
        _refresh(ds)
        kept.append(ds)
        print(f"Updated {rel_path}: size={ds['byte_size']}, count={ds['record_count']}")

    manifest["datasets"] = kept
    _save(manifest)
    print(f"\nManifest successfully updated at {MANIFEST_PATH}")
    return True


if __name__ == "__main__":
    sys.exit(0 if update_manifest() else 1)
