"""Datasets and scenario catalog endpoints."""

import json

from fastapi import APIRouter, HTTPException

from sentinel.config import settings

router = APIRouter(prefix="/datasets", tags=["Datasets"])


@router.get("")
def list_datasets():
    """Return manifest summary of registered offline datasets."""
    manifest_path = settings.data_dir / "manifest.json"
    if not manifest_path.exists():
        raise HTTPException(status_code=500, detail="Data manifest not found")

    with open(manifest_path, mode="r", encoding="utf-8") as f:
        manifest = json.load(f)

    return manifest


@router.get("/scenarios")
def list_scenarios():
    """List available crisis stress scenarios."""
    scenarios_dir = settings.data_dir / "scenarios"
    if not scenarios_dir.exists():
        return {"scenarios": []}

    scenarios = []
    for file_path in scenarios_dir.glob("*.json"):
        with open(file_path, mode="r", encoding="utf-8") as f:
            scenarios.append(json.load(f))

    return {"scenarios": scenarios}
