#!/usr/bin/env python3
"""Idempotent manifest builder for S&P Sentinel datasets.

Reads data/manifest.json, recalculates sha256, byte_size, and record_count
for all listed datasets, and writes the updated manifest.
"""

import csv
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def update_manifest() -> bool:
    manifest_path = REPO_ROOT / "data" / "manifest.json"
    if not manifest_path.exists():
        print(f"Error: Manifest not found at {manifest_path}", file=sys.stderr)
        return False

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    updated_datasets = []
    for ds in manifest.get("datasets", []):
        rel_path = ds["file_path"]
        file_path = REPO_ROOT / rel_path

        if not file_path.exists():
            print(f"Warning: {rel_path} does not exist, keeping existing entry.")
            updated_datasets.append(ds)
            continue

        with open(file_path, "rb") as f:
            content = f.read()

        byte_size = len(content)
        sha256_hash = hashlib.sha256(content).hexdigest()

        # Count records if CSV or JSON
        record_count = ds.get("record_count", 0)
        if file_path.suffix == ".csv":
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    reader = csv.reader(f)
                    _ = next(reader, None)
                    rows = list(reader)
                    record_count = len(rows)
            except Exception as e:
                print(f"Could not count rows in {rel_path}: {e}")
        elif file_path.suffix == ".json":
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        record_count = len(data)
                    elif isinstance(data, dict):
                        # If dict has positions or items
                        record_count = len(data.get("positions", [data]))
            except Exception as e:
                print(f"Could not count records in {rel_path}: {e}")

        ds["byte_size"] = byte_size
        ds["sha256"] = sha256_hash
        ds["record_count"] = record_count
        updated_datasets.append(ds)
        print(
            f"Updated {rel_path}: size={byte_size}, "
            f"sha256={sha256_hash[:8]}..., count={record_count}"
        )

    manifest["datasets"] = updated_datasets
    manifest["updated_at"] = datetime.now(timezone.utc).isoformat()

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")

    print(f"\nManifest successfully updated at {manifest_path}")
    return True


if __name__ == "__main__":
    success = update_manifest()
    sys.exit(0 if success else 1)
