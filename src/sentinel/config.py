"""Application configuration and settings."""

from pathlib import Path

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
    database_url: str = f"sqlite:///{base_dir / 'sentinel.db'}"

    # Replay parameters
    default_replay_speed: str = "1x"
    max_queue_size: int = 1000


settings = Settings()
