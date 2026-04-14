from fastapi import APIRouter
from app.api.v1.endpoints import auth

api_router = APIRouter()

# Register auth routes
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])

# Example placeholder route
@api_router.get("/health")
def health_check():
    return {"status": "ok"}



