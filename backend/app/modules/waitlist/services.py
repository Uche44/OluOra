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
        
        # Email HTML layout using the OluOra brand design system (Deep Forest Green, Gold, Cream)
        # Email HTML layout using the OluOra brand design system (Deep Forest Green, Gold, Cream)
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <link rel="preconnect" href="https://fonts.googleapis.com">
            <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
            <link href="https://fonts.googleapis.com/css2?family=Literata:opsz,wght@7..72,300..600&family=Playfair+Display:ital,wght@0,400..700;1,400..700&display=swap" rel="stylesheet">
            <style>
                body {{
                    font-family: 'Literata', Georgia, serif;
                    background-color: #FDFCF9;
                    margin: 0;
                    padding: 40px 20px;
                }}
                .container {{
                    max-width: 580px;
                    margin: 0 auto;
                    background-color: #0B3D2E;
                    border: none;
                    border-radius: 16px;
                    padding: 40px;
                    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
                }}
                .logo-img {{
                    display: block;
                    margin-bottom: 20px;
                    border-radius: 8px;
                }}
                h1 {{
                    font-family: 'Playfair Display', Georgia, serif;
                    font-size: 24px;
                    color: #FFEFCC;
                    line-height: 1.3;
                    margin-top: 0;
                    font-weight: 700;
                }}
                p {{
                    font-family: 'Literata', Georgia, serif;
                    font-size: 15px;
                    line-height: 1.6;
                    color: #FDFCF9;
                    margin-bottom: 24px;
                }}
                .divider {{
                    height: 1px;
                    background-color: #0B3D2E;
                    opacity: 0.15;
                    margin: 30px 0;
                }}
                .footer {{
                    font-family: 'Literata', Georgia, serif;
                    font-size: 12px;
                    color: #FFEFCC;
                    opacity: 0.8;
                    line-height: 1.5;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <img src="https://useoluora.xyz/icons/logo.png" alt="OluOra Logo" width="40" height="40" class="logo-img">
                <h1>Welcome to OluOra's Waitlist!</h1>
                <p>Thank you for requesting early access to OluOra. We are building the future of audience intelligence for professional creators, helping you distill bulky comment sections into actionable content strategies.</p>
                <p>We will notify you as soon as your invite is ready.</p>
                <div class="divider"></div>
                <div class="footer">
                    OluOra &bull; Launching Soon<br>
                    If you did not request this invite, you can safely ignore this email.
                </div>
            </div>
        </body>
        </html>
        """

        payload = {
            "from": f"OluOra <{settings.RESEND_FROM_EMAIL}>",
            "reply_to": settings.RESEND_FROM_EMAIL,
            "to": email,
            "subject": "You're on the list!",
            "html": html_content,
            # Plain-text version is important for spam filters — always keep this in sync with the HTML
            "text": (
                "OluOra — Welcome to the Waitlist!\n\n"
                "Thank you for requesting early access to OluOra.\n\n"
                "We are building the future of audience intelligence for professional creators, "
                "helping you distill bulky comment sections into actionable content strategies.\n\n"
                "We will notify you as soon as your invite is ready.\n\n"
                "—\n"
                "OluOra • Launching Soon\n"
                "If you did not request this invite, you can safely ignore this email."
            ),
            "headers": {
                # Tells email clients this is a legitimate mailing list with a clear unsubscribe signal
                "List-Unsubscribe": f"<mailto:{settings.RESEND_FROM_EMAIL}?subject=unsubscribe>",
                "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
                # Identifies the sending software — some spam filters weight this positively
                "X-Mailer": "OluOra Waitlist Mailer"
            }
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
