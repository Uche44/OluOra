"""Resolve the active email provider from ``EMAIL_PROVIDER``.

The provider is constructed once and cached; configuration is read at process
start, so swapping vendors is an env change plus a restart.
"""

from functools import lru_cache

from app.core.config import settings
from app.integrations.email.base import EmailProvider
from app.integrations.email.console import ConsoleProvider
from app.integrations.email.resend import ResendProvider
from app.integrations.email.sendbyte import SendbyteProvider

_PROVIDERS: dict[str, type] = {
    "resend": ResendProvider,
    "sendbyte": SendbyteProvider,
    "console": ConsoleProvider,
}


@lru_cache(maxsize=1)
def get_email_provider() -> EmailProvider:
    """Return the configured provider instance.

    An unknown ``EMAIL_PROVIDER`` raises at first use rather than silently
    falling back, so a typo surfaces immediately instead of dropping mail.
    """
    name = (settings.EMAIL_PROVIDER or "resend").strip().lower()
    provider_cls = _PROVIDERS.get(name)
    if provider_cls is None:
        raise RuntimeError(
            f"Unknown EMAIL_PROVIDER {name!r}. "
            f"Expected one of: {', '.join(sorted(_PROVIDERS))}."
        )
    return provider_cls()
