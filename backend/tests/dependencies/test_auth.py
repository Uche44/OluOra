import pytest
import uuid
from fastapi import APIRouter, Depends
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies.auth import get_current_user
from app.modules.users.models import User
from app.core.security import create_access_token
from app.main import app

pytestmark = pytest.mark.asyncio

# Register a temporary test endpoint on the FastAPI app
auth_test_router = APIRouter()

@auth_test_router.get("/test-protected-route")
def mock_protected_endpoint(current_user: User = Depends(get_current_user)):
    return {
        "status": "success",
        "user_id": str(current_user.id),
        "email": current_user.email
    }

# Include the temporary router
app.include_router(auth_test_router)

async def test_protected_route_no_token(client: AsyncClient):
    response = await client.get("/test-protected-route")
    # FastAPI HTTPBearer scheme raises 401 Unauthorized or 403 Forbidden if Authorization header is missing
    assert response.status_code in (401, 403)
    assert "not authenticated" in response.json()["detail"].lower()

async def test_protected_route_invalid_token(client: AsyncClient):
    headers = {"Authorization": "Bearer invalid.token.payload"}
    response = await client.get("/test-protected-route", headers=headers)
    assert response.status_code == 401
    assert "could not validate credentials" in response.json()["detail"].lower()

async def test_protected_route_valid_token(client: AsyncClient, db: AsyncSession):
    # 1. Create a user in the test database
    user = User(
        email="auth_test_user@oluora.com",
        full_name="Auth Tester",
        is_active=True
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # 2. Generate a valid access token for the user
    token = create_access_token({"sub": str(user.id)})
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Call the protected test route
    response = await client.get("/test-protected-route", headers=headers)
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "success"
    assert data["user_id"] == str(user.id)
    assert data["email"] == "auth_test_user@oluora.com"

async def test_protected_route_inactive_user(client: AsyncClient, db: AsyncSession):
    # 1. Create an inactive user in the database
    user = User(
        email="inactive_user@oluora.com",
        full_name="Inactive Tester",
        is_active=False
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # 2. Generate a valid token
    token = create_access_token({"sub": str(user.id)})
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Requesting should return 400 Bad Request
    response = await client.get("/test-protected-route", headers=headers)
    assert response.status_code == 400
    assert "inactive user account" in response.json()["detail"].lower()
