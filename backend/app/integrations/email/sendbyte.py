"""Sendbyte Africa provider (https://sendbyte.africa).

``POST {SENDBYTE_BASE_URL}/v1/emails`` with ``Authorization: Bearer <key>``.
Accepts ``from``/``to``/``subject``/``html``/``text``/``reply_to``/``headers``
and ``tags`` (array of strings). Returns HTTP 201 with ``{"id": "em_..."}``.

A domain must be verified in the Sendbyte dashboard before a live key
(``sk_live_``) will deliver; sandbox keys (``sk_test_``) capture mail without
delivering it.
"""

import logging

import httpx

from app.core.config import settings
from app.integrations.email.base import OutboundEmail, SendResult

logger = logging.getLogger(__name__)


class SendbyteProvider:
    name = "sendbyte"

    async def send(self, email: OutboundEmail) -> SendResult:
        api_key = settings.SENDBYTE_API_KEY
        if not api_key:
            logger.info("Sendbyte skipped for %s (no API key configured)", email.to)
            return SendResult(
                status="skipped",
                provider=self.name,
                error="SENDBYTE_API_KEY is not configured",
            )

        payload: dict = {
            "from": email.from_header,
            "to": email.to,
            "subject": email.subject,
            "html": email.html,
            "text": email.text,
        }
        if email.reply_to:
            payload["reply_to"] = email.reply_to
        if email.headers:
            payload["headers"] = email.headers
        if email.tag:
            payload["tags"] = [email.tag]

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        url = f"{settings.SENDBYTE_BASE_URL.rstrip('/')}/v1/emails"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, headers=headers, json=payload)
        except Exception as exc:
            logger.error("Sendbyte request failed for %s: %s", email.to, exc)
            return SendResult(status="failed", provider=self.name, error=str(exc)[:500])

        if response.status_code != 201:
            body = response.text[:500]
            logger.error(
                "Sendbyte rejected email to %s: %s %s", email.to, response.status_code, body
            )
            return SendResult(
                status="failed",
                provider=self.name,
                error=f"{response.status_code}: {body}",
            )

        message_id = None
        try:
            message_id = response.json().get("id")
        except Exception:
            pass

        logger.info("Sendbyte email queued for %s (%s)", email.to, email.subject)
        return SendResult(status="sent", provider=self.name, provider_message_id=message_id)
