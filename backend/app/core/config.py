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

    # Resend API
    RESEND_API_KEY: str
    RESEND_FROM_EMAIL: str

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
