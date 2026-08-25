from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# Resolve repository-owned defaults from this file rather than from the
# process working directory.  This keeps `uvicorn` and the launcher script
# interchangeable when the checkout lives anywhere on a developer machine or
# on a server.
PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="GAIS_",
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = "local"
    database_url: str = Field(
        # Development-only fallback.  Deployments should always inject the
        # complete GAIS_DATABASE_URL through the environment/secret store.
        default="postgresql+psycopg://postgres:postgres@localhost:5432/global_auto"
    )
    calculation_dsl_path: Path = PROJECT_ROOT / "spec" / "calculation_dsl.schema.json"
    log_level: str = "INFO"
    cors_origins: str = (
        "http://127.0.0.1:3000,http://localhost:3000,"
        "http://127.0.0.1:3001,http://localhost:3001"
    )

    # OpenClaw is an optional gateway-backed assistant.  It stays disabled by
    # default so a missing model/search credential never breaks the existing
    # LangGraph assistant.
    openclaw_enabled: bool = False
    openclaw_base_url: str = "http://127.0.0.1:18789"
    openclaw_gateway_token: str = ""
    openclaw_model: str = "openclaw/default"
    openclaw_upstream_model: str = ""
    # This is an inactivity/read timeout for each Gateway request, not a total
    # agent-turn deadline. Multi-round policy and web-search runs regularly
    # exceed two minutes, so keep it above the browser's rolling idle window.
    openclaw_timeout_seconds: float = 300.0
    openclaw_max_tool_rounds: int = 6
    openclaw_fallback_to_legacy: bool = True
    assistant_upload_dir: Path = PROJECT_ROOT / "storage" / "assistant_uploads"
    assistant_upload_max_bytes: int = 20_000_000
    assistant_upload_max_text_chars: int = 120_000
    # Optional deterministic search bridge.  OpenClaw itself can also use its
    # native web tool; this bridge is kept allowlisted and gives the backend a
    # safe, auditable fallback when the Gateway search provider is not enabled.
    web_search_provider: str = "brave"
    brave_api_key: str = ""
    tavily_api_key: str = ""
    searxng_base_url: str = ""
    web_search_max_results: int = 5

    # Authentication.  Personal accounts are the default first-party login
    # mode for the current product scope; OIDC and local development login
    # remain opt-in compatibility modes.
    auth_personal_enabled: bool = True
    auth_oidc_enabled: bool = False
    auth_oidc_issuer_url: str = ""
    auth_oidc_client_id: str = ""
    auth_oidc_client_secret: str = ""
    auth_oidc_redirect_uri: str = "http://127.0.0.1:8000/api/v1/auth/oidc/callback"
    auth_oidc_success_redirect_uri: str = "http://127.0.0.1:3000/assistant"
    auth_oidc_scopes: str = "openid profile email"
    auth_local_dev_enabled: bool = False
    auth_local_dev_organization_key: str = "LOCAL-DEV"
    auth_local_dev_organization_name: str = "Local development"
    auth_session_cookie_name: str = "gais_session"
    auth_csrf_cookie_name: str = "gais_csrf"
    auth_csrf_header_name: str = "X-CSRF-Token"
    auth_session_max_age_seconds: int = 28_800
    auth_oidc_state_max_age_seconds: int = 600
    auth_cookie_secure: bool = False
    auth_cookie_samesite: str = "lax"
    auth_cookie_domain: str | None = None
    auth_secret_key: str = "change-me-in-production"
    auth_default_organization_key: str = ""
    auth_default_organization_name: str = ""

    @property
    def allowed_cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
