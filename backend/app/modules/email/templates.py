"""Jinja2 rendering for email bodies.

Each email is a pair of templates: ``<name>.html`` (extends ``base.html``) and a
``<name>.txt`` plain-text sibling. Rendering both keeps the HTML and the
fallback in sync — a missing/plain-only body hurts deliverability.
"""

import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.config import settings

logger = logging.getLogger(__name__)

_TEMPLATE_DIR = Path(__file__).resolve().parents[2] / "templates" / "emails"

# Physical postal address shown in marketing footers (CAN-SPAM / NDPA).
MAILING_ADDRESS = "OluOra · Lagos, Nigeria"

_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
    trim_blocks=True,
    lstrip_blocks=True,
)


def render_email(name: str, **context) -> tuple[str, str]:
    """Render ``name`` as ``(html, text)``.

    ``unsubscribe_url`` defaults to ``None`` (most emails are transactional and
    have no opt-out); pass it to render the unsubscribe footer.
    """
    values = {
        "mailing_address": MAILING_ADDRESS,
        "frontend_url": settings.FRONTEND_URL,
        "logo_url": settings.EMAIL_LOGO_URL,
        "brand_name": settings.EMAIL_FROM_NAME,
        "unsubscribe_url": None,
        **context,
    }
    html = _env.get_template(f"{name}.html").render(**values)
    text = _env.get_template(f"{name}.txt").render(**values)
    return html, text
