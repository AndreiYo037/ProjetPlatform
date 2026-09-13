"""Application settings.

Every external dependency is addressed through here so a test can point the
app at a scratch database and a fake Google client without patching imports.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PROJET_", env_file=".env", extra="ignore")

    # Core
    database_url: str = "sqlite+pysqlite:///./projet.db"
    app_base_url: str = "http://localhost:3000"
    api_base_url: str = "http://localhost:8000"
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:3001"]
    environment: str = "development"

    # Content (the markdown seed source of truth)
    content_dir: Path = REPO_ROOT / "content"

    # Storage
    storage_root: Path = REPO_ROOT / ".storage"
    storage_signing_key: str = "dev-insecure-change-me"
    signed_url_ttl_seconds: int = 600

    # Google Workspace. Absent credentials select the fake driver, which is what
    # every test and a fresh clone run against.
    google_driver: str = "auto"  # auto | real | fake
    google_service_account_file: Path | None = None
    google_service_account_json: str | None = None
    google_delegated_subject: str = "programs@projet.sg"

    # Problem-statement drafting (FR-061). Absent, the endpoint reports that
    # drafting is unavailable rather than failing obscurely.
    anthropic_api_key: str | None = None

    # Admin access code — a shared secret that signs in as platform admin with
    # no password. Unset (the default) disables the endpoint entirely; it does
    # not fall back to some default code. Treat a configured code exactly like
    # a shared password: anyone holding it has full admin access, with no
    # per-person identity and no audit trail. This is strictly weaker than the
    # per-account password auth every actor type otherwise uses.
    admin_access_code: str | None = None
    admin_bootstrap_email: str = "admin@projet.sg"
    admin_bootstrap_name: str = "Admin"

    # Outbox
    outbox_max_attempts: int = 5
    outbox_backoff_base_seconds: int = 30

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def use_real_google(self) -> bool:
        if self.google_driver == "real":
            return True
        if self.google_driver == "fake":
            return False
        return bool(self.google_service_account_file or self.google_service_account_json)


@lru_cache
def get_settings() -> Settings:
    return Settings()
