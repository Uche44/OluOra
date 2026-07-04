import httpx
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.core.config import settings
from app.modules.waitlist.models import WaitlistEntry

logger = logging.getLogger(__name__)

class WaitlistService:
    @staticmethod
    async def get_count(db: AsyncSession) -> int:
        # Fetch the total number of waitlist entries
        result = await db.execute(select(WaitlistEntry))
        return len(result.scalars().all())

    @staticmethod
    async def create_entry(db: AsyncSession, email: str, ip_address: str | None = None) -> WaitlistEntry:
        # Check if email is already on the list
        query = select(WaitlistEntry).where(WaitlistEntry.email == email)
        result = await db.execute(query)
        existing = result.scalar_one_or_none()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This email is already registered on the waitlist."
            )

        # Create new database entry
        entry = WaitlistEntry(
            email=email,
            ip_address=ip_address,
            source="landing_page"
        )
        db.add(entry)
        await db.commit()
        await db.refresh(entry)

        # Trigger welcome email via Resend API
        await WaitlistService.send_welcome_email(email)

        return entry

    @staticmethod
    async def send_welcome_email(email: str) -> None:
        # If API key is not set or placeholder, skip email delivery (useful for testing/dev fallback)
        if not settings.RESEND_API_KEY or settings.RESEND_API_KEY == "re_placeholder_key":
            logger.info(f"Skipping Resend email for {email} (placeholder key or empty)")
            return

        url = "https://api.resend.com/emails"
        headers = {
            "Authorization": f"Bearer {settings.RESEND_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # Email HTML layout using the OluOra brand design system (Deep Forest Green, editorial font literals)
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{
                    font-family: Georgia, serif;
                    background-color: #fcf9f8;
                    color: #1b1c1c;
                    margin: 0;
                    padding: 40px 20px;
                }}
                .container {{
                    max-width: 580px;
                    margin: 0 auto;
                    background-color: #ffffff;
                    border: 1px solid #eae7e7;
                    border-radius: 16px;
                    padding: 40px;
                    box-shadow: 0 4px 12px rgba(0, 38, 27, 0.03);
                }}
                .logo {{
                    font-family: Georgia, serif;
                    font-size: 24px;
                    font-weight: bold;
                    color: #00261b;
                    margin-bottom: 30px;
                    letter-spacing: -0.02em;
                }}
                h1 {{
                    font-family: Georgia, serif;
                    font-size: 22px;
                    color: #00261b;
                    line-height: 1.3;
                    margin-top: 0;
                }}
                p {{
                    font-size: 15px;
                    line-height: 1.6;
                    color: #414944;
                    margin-bottom: 24px;
                }}
                .divider {{
                    height: 1px;
                    background-color: #eae7e7;
                    margin: 30px 0;
                }}
                .footer {{
                    font-size: 12px;
                    color: #717974;
                    line-height: 1.5;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="logo">OluOra</div>
                <h1>You're on the list.</h1>
                <p>Thank you for requesting early access to OluOra. We are building the future of audience intelligence for professional creators, helping you distill complex comment sections into actionable content strategies.</p>
                <p>We will notify you as soon as your invite is ready.</p>
                <div class="divider"></div>
                <div class="footer">
                    OluOra Intelligence &bull; Private Beta<br>
                    If you did not request this invite, you can safely ignore this email.
                </div>
            </div>
        </body>
        </html>
        """

        payload = {
            "from": settings.RESEND_FROM_EMAIL,
            "to": email,
            "subject": "Welcome to the OluOra Waitlist",
            "html": html_content,
            "text": "Thank you for joining the OluOra waitlist. We will notify you as soon as your invite is ready."
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.post(url, headers=headers, json=payload)
                if response.status_code not in (200, 201):
                    logger.error(
                        f"Failed to send Resend email. Status: {response.status_code}, Body: {response.text}"
                    )
                else:
                    logger.info(f"Resend welcome email sent successfully to {email}")
            except Exception as e:
                logger.error(f"Error calling Resend API: {e}")
