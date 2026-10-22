import pytest

from app.core.config import settings
from app.integrations.email import OutboundEmail
from app.integrations.email.console import ConsoleProvider
from app.integrations.email.factory import get_email_provider
from app.integrations.email.resend import ResendProvider
from app.integrations.email.sendbyte import SendbyteProvider


def _resolve(name, monkeypatch):
    monkeypatch.setattr(settings, "EMAIL_PROVIDER", name)
    get_email_provider.cache_clear()
    try:
        return get_email_provider()
    finally:
        get_email_provider.cache_clear()


def _email() -> OutboundEmail:
    return OutboundEmail(
        to="creator@oluora.com",
        subject="Hello",
        html="<p>Hello</p>",
        text="Hello",
        from_email="hello@useoluora.xyz",
    )


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("resend", ResendProvider),
        ("sendbyte", SendbyteProvider),
        ("console", ConsoleProvider),
        ("RESEND", ResendProvider),
    ],
)
def test_known_providers_resolve(name, expected, monkeypatch):
    assert isinstance(_resolve(name, monkeypatch), expected)


def test_unknown_provider_raises(monkeypatch):
    with pytest.raises(RuntimeError, match="Unknown EMAIL_PROVIDER"):
        _resolve("mailgun", monkeypatch)


async def test_console_provider_reports_sent():
    result = await ConsoleProvider().send(_email())
    assert result.status == "sent"
    assert result.provider == "console"


async def test_resend_skips_without_api_key(monkeypatch):
    monkeypatch.setattr(settings, "RESEND_API_KEY", "re_placeholder_key")
    result = await ResendProvider().send(_email())
    assert result.status == "skipped"
    assert result.provider == "resend"


async def test_sendbyte_skips_without_api_key(monkeypatch):
    monkeypatch.setattr(settings, "SENDBYTE_API_KEY", "")
    result = await SendbyteProvider().send(_email())
    assert result.status == "skipped"
    assert result.provider == "sendbyte"


def test_from_header_uses_display_name():
    assert _email().from_header == "OluOra <hello@useoluora.xyz>"
