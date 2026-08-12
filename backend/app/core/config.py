from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Studio Sunny HQ"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"

    database_url: str = "postgresql+psycopg://sunny:sunny_hq_dev@localhost:5432/studio_sunny_hq"
    redis_url: str = "redis://localhost:6379/0"

    secret_key: str = "dev-only-change-me-studio-sunny-hq-secret"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 14

    cors_origins: str = "http://localhost:3000"
    cookie_secure: bool = False
    cookie_domain: str | None = None
    cookie_samesite: str = "lax"

    access_cookie_name: str = "ss_access"
    refresh_cookie_name: str = "ss_refresh"
    csrf_cookie_name: str = "ss_csrf"
    oauth_state_cookie_name: str = "ss_oauth_state"
    upload_dir: str = "uploads"
    frontend_url: str = "http://localhost:3000"

    # Comma-separated proxy IPs/CIDRs trusted to set X-Forwarded-For.
    # Empty = do not trust XFF (use request.client.host only).
    trusted_proxy_ips: str = "127.0.0.1,::1"

    # SSO / OIDC (optional — disabled when empty)
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/v1/auth/google/callback"
    google_allowed_domain: str = "studiosunny.com"

    # Observability (optional)
    sentry_dsn: str = ""
    otel_exporter_otlp_endpoint: str = ""
    posthog_api_key: str = ""
    posthog_host: str = "https://us.i.posthog.com"

    # Email (optional — logs to console when SMTP empty)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "Studio Sunny HQ <noreply@studiosunny.com>"
    smtp_tls: bool = True

    @property
    def google_oauth_enabled(self) -> bool:
        return bool(self.google_client_id and self.google_client_secret)

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
