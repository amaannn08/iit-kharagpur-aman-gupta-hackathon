"""Application configuration and settings."""

from pathlib import Path
from typing import Dict, List, Tuple

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
        "portfolio/equity_sleeve.json",
    ]

    # Replay sources: name -> (path relative to data_dir, adapter kind, badge).
    # Badges follow AGENTS.md: replay data is labeled Synthetic Scenario or Historical Replay;
    # LIVE CAPTURE files are written by scripts/live/record_live.py (the app itself stays offline).
    replay_sources: Dict[str, Tuple[str, str, str]] = {
        "news_demo": ("news_demo.csv", "news", "SYNTHETIC SCENARIO"),
        "social_demo": ("social_demo.csv", "social", "SYNTHETIC SCENARIO"),
        "polygon_2023": ("real/polygon_news/polygon_news.csv", "news", "HISTORICAL REPLAY"),
        "stock_tweets": ("real/stock_tweets/sample.csv", "social", "HISTORICAL REPLAY"),
        "gdelt_snapshot": ("real/gdelt/snapshot.csv", "news", "HISTORICAL REPLAY"),
        "gdelt_live": ("live/gdelt_live.csv", "news", "LIVE CAPTURE"),
        "sec_8k_live": ("live/sec_8k_live.csv", "news", "LIVE CAPTURE"),
    }

    # Decision gating thresholds
    action_impact_threshold: int = 7  # signals with score > 7 trigger portfolio action
    action_confidence_threshold: float = 0.50  # minimum model confidence for action eligibility


settings = Settings()
