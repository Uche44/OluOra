import logging
import uuid

from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.modules.email.services import EmailService
from app.modules.email.tokens import verify_unsubscribe_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/email", tags=["Email"])


def _page(title: str, message: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} · OluOra</title>
<style>
    body {{ font-family: Georgia, 'Times New Roman', serif; background: #FDFCF9; color: #0B3D2E;
           display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; }}
    .card {{ background: #0B3D2E; border-radius: 16px; padding: 40px; max-width: 460px; text-align: center; }}
    h1 {{ color: #FFEFCC; font-size: 22px; margin: 0 0 16px; }}
    p {{ color: #FDFCF9; font-size: 15px; line-height: 1.6; margin: 0; }}
</style>
</head>
<body>
    <div class="card">
        <h1>{title}</h1>
        <p>{message}</p>
    </div>
</body>
</html>"""


@router.get(
    "/unsubscribe",
    response_class=HTMLResponse,
    summary="Unsubscribe from OluOra emails",
)
async def unsubscribe(token: str = Query(...), db: AsyncSession = Depends(get_db)):
    """One-click opt-out. The token is signed, so it can only unsubscribe its own recipient."""
    payload = verify_unsubscribe_token(token)
    if not payload:
        return HTMLResponse(
            _page("Link expired", "This unsubscribe link is no longer valid."),
            status_code=400,
        )

    try:
        object_id = uuid.UUID(payload["sub"])
    except (ValueError, TypeError):
        return HTMLResponse(
            _page("Link expired", "This unsubscribe link is no longer valid."),
            status_code=400,
        )

    removed = await EmailService.unsubscribe(
        db,
        scope=payload.get("scope", ""),
        object_id=object_id,
        email=payload["email"],
    )
    if not removed:
        return HTMLResponse(
            _page("Link expired", "This unsubscribe link is no longer valid."),
            status_code=400,
        )

    return HTMLResponse(_page("You're unsubscribed", "You won't receive these emails again."))
