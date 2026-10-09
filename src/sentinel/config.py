"""Application configuration and settings."""

from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for S&P Sentinel."""

    model_config = SettingsConfigDict(
        env_prefix="SENTINEL_",
        env_file=".env",
        extra="ignore",
    )

    project_name: str = "S&P Sentinel"
    version: str = "0.1.0"
    mode: str = "offline-replay"
    debug: bool = False

    # Host & Port
    host: str = "127.0.0.1"
    port: int = 8000

    # Paths
    base_dir: Path = Path(__file__).resolve().parent.parent.parent
    data_dir: Path = base_dir / "data"
    runtime_dir: Path = base_dir / ".runtime"
    database_url: str = f"sqlite:///{base_dir / '.runtime' / 'sentinel.db'}"

    # Replay parameters
    default_replay_speed: str = "1x"
    max_queue_size: int = 1000

    # Module B portfolio: wholesale book first, then sleeves (relative to data_dir)
    portfolio_files: List[str] = [
        "wholesale_positions.json",
        "portfolio/credit_sleeve.json",
    ]

    # Decision gating thresholds
    action_impact_threshold: int = 7  # signals with score > 7 trigger portfolio action
    action_confidence_threshold: float = 0.50  # minimum model confidence for action eligibility


settings = Settings()
