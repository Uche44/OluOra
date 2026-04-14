import httpx
from app.core.config import settings

TIKTOK_TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
TIKTOK_USER_URL = "https://open.tiktokapis.com/v2/user/info/"

async def exchange_code_for_token(code: str):
    """
    Exchanges the TikTok OAuth code for an access token.
    """
    async with httpx.AsyncClient() as client:
        data = {
            "client_key": settings.TIKTOK_CLIENT_KEY,
            "client_secret": settings.TIKTOK_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": settings.TIKTOK_REDIRECT_URI,
        }
        response = await client.post(TIKTOK_TOKEN_URL, data=data)
        return response.json()

async def get_tiktok_user(access_token: str):
    """
    Fetches the TikTok user profile information using the access token.
    """
    async with httpx.AsyncClient() as client:
        # We need these fields: open_id, union_id, avatar_url, display_name, username
        params = {
            "fields": "open_id,display_name,avatar_url,username"
        }
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        response = await client.get(TIKTOK_USER_URL, headers=headers, params=params)
        return response.json()
