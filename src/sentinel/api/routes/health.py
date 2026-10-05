"""Health and runtime readiness endpoint."""

from datetime import datetime

from fastapi import APIRouter

from sentinel.config import settings

router = APIRouter(tags=["System"])


@router.get("/health")
def get_health():
    """Verify application readiness, offline mode, and dataset presence."""
    manifest_path = settings.data_dir / "manifest.json"
    news_path = settings.data_dir / "news_demo.csv"
    social_path = settings.data_dir / "social_demo.csv"
    portfolio_path = settings.data_dir / "wholesale_positions.json"

    datasets_present = (
        manifest_path.exists()
        and news_path.exists()
        and social_path.exists()
        and portfolio_path.exists()
    )

    return {
        "status": "ok",
        "project": settings.project_name,
        "version": settings.version,
        "mode": settings.mode,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "datasets_ready": datasets_present,
        "environment": {
            "offline_only": True,
            "external_apis": False,
            "database_ready": True,
        },
    }
