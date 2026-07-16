import asyncio
import httpx
from sqlalchemy import text
from app.core.db import engine

# Import app.main to register all SQLAlchemy mappers
import app.main

async def debug_token():
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT user_id, provider, access_token, token_expires_at FROM social_accounts ORDER BY id DESC LIMIT 1"))
        social = result.fetchone()
        
        if not social:
            print("No social account found in database.")
            return
            
        user_id, provider, access_token, token_expires_at = social
        print(f"User ID: {user_id}")
        print(f"Provider: {provider}")
        print(f"Access Token (prefix): {access_token[:15]}...")
        print(f"Token Expires At: {token_expires_at}")
        
        # Verify with Google tokeninfo endpoint
        url = f"https://oauth2.googleapis.com/tokeninfo?access_token={access_token}"
        async with httpx.AsyncClient() as client:
            res = await client.get(url)
            print(f"Tokeninfo status: {res.status_code}")
            if res.status_code == 200:
                data = res.json()
                print("Scopes present on token:")
                print(data.get("scope"))
                print("Expires in:", data.get("expires_in"))
            else:
                print("Failed to get token info:", res.text)

if __name__ == "__main__":
    asyncio.run(debug_token())
