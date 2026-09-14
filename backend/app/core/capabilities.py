"""Platform capability lookups derived from runtime configuration."""
from app.core import providers
from app.core.config import settings


def comment_analysis_supported(platform: str) -> bool:
    """Whether comment ingestion is available for a platform right now.

    YouTube uses the official Data API, so it is always available. TikTok exposes
    no comment-read endpoint to commercial apps, so it depends on the third-party
    comment provider being configured.
    """
    if platform == providers.YOUTUBE:
        return True
    if platform == providers.TIKTOK:
        return bool(settings.SCRAPECREATORS_API_KEY)
    return False
