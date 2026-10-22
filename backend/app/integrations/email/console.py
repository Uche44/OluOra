"""Console provider — logs the message instead of delivering it.

Used for local development and tests so no API key or network is required and
no emails are actually sent. Selected with ``EMAIL_PROVIDER=console``.
"""

import logging

from app.integrations.email.base import OutboundEmail, SendResult

logger = logging.getLogger(__name__)


class ConsoleProvider:
    name = "console"

    async def send(self, email: OutboundEmail) -> SendResult:
        logger.info(
            "[console-email] to=%s from=%s subject=%r chars=%d",
            email.to,
            email.from_header,
            email.subject,
            len(email.html),
        )
        return SendResult(status="sent", provider=self.name, provider_message_id=None)
