import pytest

from app.core.config import settings
from app.integrations.email.base import SendResult


class RecordingProvider:
    """Captures outbound emails in memory so tests never touch the network."""

    name = "recording"

    def __init__(self) -> None:
        self.sent = []

    async def send(self, email) -> SendResult:
        self.sent.append(email)
        return SendResult(
            status="sent",
            provider=self.name,
            provider_message_id=f"test-{len(self.sent)}",
        )


@pytest.fixture(autouse=True)
def recording_email_provider(monkeypatch):
    """Swap the active provider for a recording fake for every email test."""
    provider = RecordingProvider()
    # services.py resolves the provider through this module global at call time.
    monkeypatch.setattr(
        "app.modules.email.services.get_email_provider", lambda: provider
    )
    monkeypatch.setattr(settings, "EMAIL_PROVIDER", "console")
    return provider
