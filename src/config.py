"""Modern configuration management using Pydantic Settings v2."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="GSC_", case_sensitive=False)

    # Database Settings
    database_path: Path = Field(
        default=Path("./data/gsc-data.db"), description="SQLite database path"
    )
    enable_duckdb: bool = Field(default=True)

    # GSC Sync Settings - CRITICAL LIMITATION
    # GSC API does NOT support concurrent access!
    # Tested 2025-07-25: concurrent requests = 0% success rate
    # Sequential requests = 100% success rate
    # Always use sequential processing for GSC operations

    # API Settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = Field(default=4, ge=1, le=16)

    # GSC Settings
    credentials_path: Path = Path("./cred/client_secret.json")
    max_retries: int = Field(default=3, ge=1, le=10)
    rate_limit_per_minute: int = 60

    # Batch Processing Settings
    batch_insert_size: int = Field(
        default=25000, ge=1000, le=50000, description="Number of records per batch insert"
    )
    buffer_flush_size: int = Field(
        default=100000, ge=10000, le=200000, description="Buffer size before auto-flush"
    )
    buffer_flush_interval: float = Field(
        default=30.0, ge=5.0, le=300.0, description="Maximum seconds before buffer auto-flush"
    )
    max_buffer_memory_mb: int = Field(
        default=100, ge=10, le=1000, description="Maximum buffer memory usage in MB"
    )
    use_index_optimization: bool = Field(
        default=True, description="Drop/recreate indexes for large bulk imports"
    )
    bulk_insert_threshold: int = Field(
        default=100000,
        ge=10000,
        le=1000000,
        description="Record count threshold to trigger index optimization",
    )
    enable_fast_mode: bool = Field(
        default=False, description="Enable aggressive optimizations (less safe but faster)"
    )
    standard_cache_size: int = Field(
        default=20000, ge=5000, le=50000, description="Cache size for standard mode"
    )

    # Cache Settings
    enable_cache: bool = (
        False  # Disabled Redis cache to avoid connection errors when Redis server not running
    )
    cache_ttl_seconds: int = 3600
    redis_url: str | None = "redis://localhost:6379"
    query_timeout_seconds: int = 30

    # Monitoring Settings (disabled by default to avoid annoying warnings)
    enable_telemetry: bool = False
    prometheus_port: int = 9090

    # Logging Settings
    log_level: str = "INFO"
    log_file: Path = Path("./logs/gsc_app.log")

    @field_validator("database_path", "credentials_path", "log_file")
    @classmethod
    def ensure_parent_exists(cls, v: Path) -> Path:
        """Ensure parent directory exists for file paths."""
        if v and not v.parent.exists():
            v.parent.mkdir(parents=True, exist_ok=True)
        return v

    @property
    def database_url(self) -> str:
        """Return SQLite database URL."""
        return f"sqlite:///{self.database_path}"

    @property
    def async_database_url(self) -> str:
        """Return async SQLite database URL."""
        return f"sqlite+aiosqlite:///{self.database_path}"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
