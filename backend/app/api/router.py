from fastapi import APIRouter
from app.modules.waitlist.router import router as waitlist_router

api_router = APIRouter(prefix="/api/v1")

# Include all modular routers here
api_router.include_router(waitlist_router)
