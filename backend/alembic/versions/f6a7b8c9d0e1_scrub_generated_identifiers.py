"""scrub generated identifiers from content text

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-11-05 05:00:00.000000

Early opportunity prompts exposed raw UUIDs, so the model sometimes copied them
into titles/rationales/angles. New generation uses short references and strips
identifiers, but existing rows need a one-time cleanup.
"""

import json
import re
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, Sequence[str], None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_UUID_RE = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
)
_ALIAS_CITATION_RE = re.compile(r"[\(\[]\s*(?:[ICM]\d+\s*[,;]?\s*)+\s*[\)\]]")
_EMPTY_BRACKETS_RE = re.compile(r"[\(\[]\s*[\)\]]")
_ID_LABEL_RE = re.compile(
    r"\b(?:insight|cluster|comment)_(?:id|ref)\s*[:=]\s*", re.IGNORECASE
)


def _clean(value) -> str:
    if value is None:
        return ""
    text = str(value)
    text = _UUID_RE.sub("", text)
    text = _ALIAS_CITATION_RE.sub("", text)
    text = _ID_LABEL_RE.sub("", text)
    text = _EMPTY_BRACKETS_RE.sub("", text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+([.,;:!?])", r"\1", text)
    return text.strip()


def _clean_list(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except Exception:
            return []
    if not isinstance(value, list):
        return []
    cleaned = [_clean(item) for item in value]
    return [item for item in cleaned if item]


def upgrade() -> None:
    conn = op.get_bind()

    opportunities = conn.execute(
        sa.text(
            "SELECT id, title, rationale, suggested_angle FROM content_opportunities"
        )
    ).mappings().all()
    for row in opportunities:
        conn.execute(
            sa.text(
                """
                UPDATE content_opportunities
                SET title = :title,
                    rationale = :rationale,
                    suggested_angle = :suggested_angle
                WHERE id = CAST(:id AS uuid)
                """
            ),
            {
                "id": str(row["id"]),
                "title": _clean(row["title"]),
                "rationale": _clean(row["rationale"]),
                "suggested_angle": _clean(row["suggested_angle"]),
            },
        )

    calendar_items = conn.execute(
        sa.text("SELECT id, title, angle, notes FROM content_calendar_items")
    ).mappings().all()
    for row in calendar_items:
        conn.execute(
            sa.text(
                """
                UPDATE content_calendar_items
                SET title = :title,
                    angle = :angle,
                    notes = :notes
                WHERE id = CAST(:id AS uuid)
                """
            ),
            {
                "id": str(row["id"]),
                "title": _clean(row["title"]),
                "angle": _clean(row["angle"]),
                "notes": _clean(row["notes"]),
            },
        )

    scripts = conn.execute(
        sa.text(
            """
            SELECT id, working_title, hook, body, cta, caption, description,
                   talking_points, examples, alt_titles
            FROM content_scripts
            """
        )
    ).mappings().all()
    for row in scripts:
        conn.execute(
            sa.text(
                """
                UPDATE content_scripts
                SET working_title = :working_title,
                    hook = :hook,
                    body = :body,
                    cta = :cta,
                    caption = :caption,
                    description = :description,
                    talking_points = CAST(:talking_points AS json),
                    examples = CAST(:examples AS json),
                    alt_titles = CAST(:alt_titles AS json)
                WHERE id = CAST(:id AS uuid)
                """
            ),
            {
                "id": str(row["id"]),
                "working_title": _clean(row["working_title"]),
                "hook": _clean(row["hook"]),
                "body": _clean(row["body"]),
                "cta": _clean(row["cta"]),
                "caption": _clean(row["caption"]),
                "description": _clean(row["description"]),
                "talking_points": json.dumps(
                    _clean_list(row["talking_points"]), ensure_ascii=False
                ),
                "examples": json.dumps(
                    _clean_list(row["examples"]), ensure_ascii=False
                ),
                "alt_titles": json.dumps(
                    _clean_list(row["alt_titles"]), ensure_ascii=False
                ),
            },
        )


def downgrade() -> None:
    # Data cleanup is not reversible; the removed identifiers were invalid.
    pass
