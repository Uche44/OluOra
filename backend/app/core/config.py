from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

# Sentinel used only as a code-level default. Never acceptable as a real signing key.
_INSECURE_JWT_SECRET_DEFAULT = "secret-key-change-in-production-32chars"

# Public example value shipped in .env.example; also treated as insecure.
_INSECURE_JWT_SECRETS = {
    _INSECURE_JWT_SECRET_DEFAULT,
    "super_secret_cryptographically_secure_random_string_here",
    "",
}

# Require at least this many characters for a signing key.
_MIN_JWT_SECRET_LENGTH = 32

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    ENVIRONMENT: str = "dev"
    # Fail toward safety: default to False unless explicitly enabled in dev.
    DEBUG: bool = False

    # Database
    DATABASE_URL: str

    # ---------------------------------------------------------------------
    # Email
    # ---------------------------------------------------------------------
    # Active email provider. Swappable so the app is not locked to a vendor:
    #   "resend"   -> Resend HTTP API (default)
    #   "sendbyte" -> Sendbyte Africa
    #   "console"  -> log-only, no network (dev/tests)
    EMAIL_PROVIDER: str = "resend"
    # Display name used in the From header ("OluOra <hello@...>").
    EMAIL_FROM_NAME: str = "OluOra"
    # Absolute https URL of the brand mark shown in email headers. Email clients
    # fetch images server-side, so this must be publicly reachable — a localhost
    # or relative URL renders as a broken image.
    EMAIL_LOGO_URL: str = "https://www.useoluora.xyz/icons/logo.png"
    # Sender address. Falls back to RESEND_FROM_EMAIL for backwards compatibility.
    EMAIL_FROM_EMAIL: str = ""
    # Where replies should go. Defaults to the sender address when empty.
    EMAIL_REPLY_TO: str = ""
    # Public origin of the creator app, used to build links inside emails.
    FRONTEND_URL: str = "http://localhost:3000"
    # Public origin of this API, used to build links that hit backend routes
    # directly (e.g. one-click unsubscribe).
    API_PUBLIC_URL: str = "http://localhost:8000"

    # Resend API (optional: only required when EMAIL_PROVIDER=resend)
    RESEND_API_KEY: str = ""
    RESEND_FROM_EMAIL: str = ""

    # Sendbyte Africa (https://sendbyte.africa) — only used when EMAIL_PROVIDER=sendbyte
    SENDBYTE_API_KEY: str = ""
    SENDBYTE_BASE_URL: str = "https://api.sendbyte.africa"

    # Shared secret guarding the internal cron endpoint. Empty disables it.
    INTERNAL_CRON_SECRET: str = ""

    # Bulk-send behaviour. Caps exist to respect provider rate limits and daily quotas.
    EMAIL_MAX_PER_SECOND: float = 2.0
    EMAIL_BULK_MAX_PER_RUN: int = 200

    # Feedback reminders: minimum account age before a reminder is eligible, and
    # how long before the same user can be reminded again.
    FEEDBACK_REMINDER_MIN_AGE_DAYS: int = 3
    FEEDBACK_REMINDER_COOLDOWN_DAYS: int = 30

    # Google OAuth
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    GOOGLE_REDIRECT_URI: str
    # Separate redirect for the "connect YouTube" consent flow.
    GOOGLE_YOUTUBE_REDIRECT_URI: str = "http://localhost:3000/auth/youtube/callback"
    # Callback for the isolated admin app's Google sign-in (register it as an
    # additional authorized redirect URI in Google Cloud Console).
    GOOGLE_ADMIN_REDIRECT_URI: str = "http://localhost:3001/auth/callback"

    # TikTok OAuth (Login Kit)
    TIKTOK_CLIENT_KEY: str = ""
    TIKTOK_CLIENT_SECRET: str = ""
    # Must be an HTTPS, registered redirect URI (no query params/fragments).
    TIKTOK_REDIRECT_URI: str = ""
    # Emails allowed to connect TikTok while the integration is in beta.
    # Comma-separated; empty means nobody can connect TikTok (hidden for all).
    TIKTOK_BETA_EMAILS: str = ""

    # TikTok comment ingestion (ScrapeCreators)
    # TikTok's Display API exposes no comment-read endpoint to commercial apps, so
    # public comments are sourced from a third-party provider. Leaving this key
    # empty keeps TikTok videos metadata-only.
    SCRAPECREATORS_API_KEY: str = ""
    SCRAPECREATORS_BASE_URL: str = "https://api.scrapecreators.com"

    # JWT Authentication
    JWT_SECRET: str = _INSECURE_JWT_SECRET_DEFAULT
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # AI Integrations
    GROQ_API_KEY: str = ""
    GROQ_LLM_MODEL: str = "openai/gpt-oss-120b"
    HF_API_KEY: str = ""
    HF_EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"

    # Analysis sampling. Each cluster sends up to this many diverse comments to
    # the LLM (previously only 5 centroid-nearest comments were used).
    ANALYSIS_SAMPLES_PER_CLUSTER: int = 20
    # Large clusters are split into this many sub-groups before sampling so
    # internal sub-themes are represented, not just the cluster centroid.
    ANALYSIS_SUBCLUSTERS: int = 6

    # CORS Origins (comma-separated string in env)
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001"

    # Internal admin allowlist (comma-separated emails). Users whose email is
    # listed here are promoted to admin; users removed from the list are demoted.
    ADMIN_EMAILS: str = ""

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"

    @property
    def cors_origins_list(self) -> List[str]:
        # Strip trailing slashes and whitespace to avoid strict origin mismatch errors
        return [i.strip().rstrip("/") for i in self.CORS_ORIGINS.split(",") if i.strip()]

    @property
    def admin_emails_list(self) -> List[str]:
        # Normalized lowercase for case-insensitive email matching.
        return [i.strip().lower() for i in self.ADMIN_EMAILS.split(",") if i.strip()]

    @property
    def tiktok_beta_emails_list(self) -> List[str]:
        # Normalized lowercase for case-insensitive email matching.
        return [i.strip().lower() for i in self.TIKTOK_BETA_EMAILS.split(",") if i.strip()]

    @property
    def email_from_address(self) -> str:
        # EMAIL_FROM_EMAIL is the new field; fall back to the legacy RESEND_FROM_EMAIL
        # so existing deployments keep working without renaming the env var.
        return self.EMAIL_FROM_EMAIL or self.RESEND_FROM_EMAIL

    @property
    def email_reply_to_address(self) -> str:
        return self.EMAIL_REPLY_TO or self.email_from_address

settings = Settings()

# ---------------------------------------------------------------------------
# Boot-time security guard: refuse to start with an unsafe JWT signing secret.
# A leaked/weak JWT_SECRET lets anyone forge access and refresh tokens, which
# would be a full account-takeover vector in production.
# ---------------------------------------------------------------------------
if (
    settings.ENVIRONMENT.lower() == "production"
    and (
        len(settings.JWT_SECRET) < _MIN_JWT_SECRET_LENGTH
        or settings.JWT_SECRET in _INSECURE_JWT_SECRETS
    )
):
    raise RuntimeError(
        "Refusing to start in production: JWT_SECRET is missing or too weak. "
        f"Set a unique, random JWT_SECRET of at least {_MIN_JWT_SECRET_LENGTH} "
        "characters (e.g. `python -c \"import secrets; print(secrets.token_urlsafe(64))\"`)."
    )
