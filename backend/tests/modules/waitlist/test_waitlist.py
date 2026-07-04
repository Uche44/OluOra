import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

async def test_health_check(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"

async def test_join_waitlist_success(client: AsyncClient):
    # Setup test payload
    email = "test_user_waitlist@oluora.com"
    payload = {"email": email}

    # First signup
    response = await client.post("/api/v1/waitlist", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == email
    assert "id" in data
    assert data["source"] == "landing_page"

    # Verify count increments
    count_response = await client.get("/api/v1/waitlist/count")
    assert count_response.status_code == 200
    count_data = count_response.json()
    assert count_data["count"] >= 1

async def test_join_waitlist_duplicate(client: AsyncClient):
    email = "duplicate_waitlist@oluora.com"
    payload = {"email": email}

    # First request
    response1 = await client.post("/api/v1/waitlist", json=payload)
    assert response1.status_code == 201

    # Second request with same email
    response2 = await client.post("/api/v1/waitlist", json=payload)
    assert response2.status_code == 409
    data = response2.json()
    assert "detail" in data
    assert "already registered" in data["detail"].lower()

async def test_join_waitlist_invalid_email(client: AsyncClient):
    invalid_payloads = [
        {"email": "not-an-email"},
        {"email": "plainaddress"},
        {"email": "@missing-local.com"},
        {"email": "missing-domain@"},
        {"email": ""},
    ]

    for payload in invalid_payloads:
        response = await client.post("/api/v1/waitlist", json=payload)
        assert response.status_code == 422
