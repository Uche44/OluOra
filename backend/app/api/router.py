from fastapi import APIRouter
from app.modules.waitlist.router import router as waitlist_router
from app.modules.users.router import router as users_router
from app.modules.users.auth_router import router as auth_router
from app.modules.youtube.router import router as youtube_router
from app.modules.comments.router import router as comments_router
from app.modules.analysis.router import router as analysis_router

api_router = APIRouter(prefix="/api/v1")

# Include all modular routers here
api_router.include_router(waitlist_router)
api_router.include_router(users_router)
api_router.include_router(auth_router)
api_router.include_router(youtube_router)
api_router.include_router(comments_router)
api_router.include_router(analysis_router)
