"""Resend provider (https://resend.com) — the default.

Talks to the REST API directly over httpx (no vendor SDK) so the dependency
footprint stays small. A missing or placeholder API key short-circuits to a
``skipped`` result instead of erroring, which keeps local dev quiet.
"""

import logging

import httpx

from app.core.config import settings
from app.integrations.email.base import OutboundEmail, SendResult

logger = logging.getLogger(__name__)

_API_URL = "https://api.resend.com/emails"
_PLACEHOLDER_KEYS = {"", "re_placeholder_key"}


class ResendProvider:
    name = "resend"

    async def send(self, email: OutboundEmail) -> SendResult:
        api_key = settings.RESEND_API_KEY
        if api_key in _PLACEHOLDER_KEYS:
            logger.info("Resend skipped for %s (no API key configured)", email.to)
            return SendResult(
                status="skipped",
                provider=self.name,
                error="RESEND_API_KEY is not configured",
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
            payload["tags"] = [{"name": "category", "value": email.tag}]

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(_API_URL, headers=headers, json=payload)
        except Exception as exc:  # network/timeout — never raise into the caller
            logger.error("Resend request failed for %s: %s", email.to, exc)
            return SendResult(status="failed", provider=self.name, error=str(exc)[:500])

        if response.status_code not in (200, 201):
            body = response.text[:500]
            logger.error(
                "Resend rejected email to %s: %s %s", email.to, response.status_code, body
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

        logger.info("Resend email sent to %s (%s)", email.to, email.subject)
        return SendResult(status="sent", provider=self.name, provider_message_id=message_id)
