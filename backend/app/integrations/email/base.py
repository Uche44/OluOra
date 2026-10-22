"""Provider-agnostic email sending contract.

Every provider (Resend, Sendbyte, console, …) implements :class:`EmailProvider`
and returns a :class:`SendResult`. Callers build an :class:`OutboundEmail` and
hand it to the active provider resolved by ``factory.get_email_provider`` — no
caller ever talks to a vendor SDK directly.
"""

from dataclasses import dataclass, field
from typing import Literal, Protocol

# "skipped" means the provider deliberately did not deliver (e.g. no API key
# configured in dev). It is not a failure — nothing was attempted.
SendStatus = Literal["sent", "skipped", "failed"]


@dataclass(slots=True)
class OutboundEmail:
    """A fully rendered message ready to hand to a provider."""

    to: str
    subject: str
    html: str
    text: str
    from_email: str
    from_name: str = "OluOra"
    reply_to: str | None = None
    # Extra headers (e.g. List-Unsubscribe) passed through where the provider allows.
    headers: dict[str, str] = field(default_factory=dict)
    # Provider-side label for analytics/segmentation (e.g. "waitlist_broadcast").
    tag: str | None = None

    @property
    def from_header(self) -> str:
        """RFC 5322 From value, e.g. ``OluOra <hello@example.com>``."""
        if self.from_name:
            return f"{self.from_name} <{self.from_email}>"
        return self.from_email


@dataclass(slots=True)
class SendResult:
    status: SendStatus
    provider: str
    provider_message_id: str | None = None
    error: str | None = None


class EmailProvider(Protocol):
    #: Short identifier persisted on each EmailMessage row.
    name: str

    async def send(self, email: OutboundEmail) -> SendResult:
        ...
