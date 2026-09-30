import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.db import SessionLocal
from app.api.router import api_router

# Import all models at startup to register them in SQLAlchemy's class registry
from app.modules.users.models import User, SocialAccount, ApiQuotaUsage, RefreshToken
from app.modules.youtube.models import Channel, Video
from app.modules.comments.models import Comment
from app.modules.analysis.models import Analysis, TopicCluster, Insight, AnalysisJob
from app.modules.admin.services import sync_admin_flags

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Reconcile admin access with the ADMIN_EMAILS allowlist on boot."""
    try:
        async with SessionLocal() as db:
            changed = await sync_admin_flags(db)
            if changed:
                logger.info("Admin flag sync updated %d user(s)", changed)
    except Exception:
        # Never block startup over the admin allowlist (e.g. migration not yet applied).
        logger.exception("Admin flag sync failed at startup")
    yield


app = FastAPI(
    title="OluOra API",
    description="Audience Intelligence API for video creators",
    version="1.0.0",
    debug=settings.DEBUG,
    lifespan=lifespan,
)

# CORS middleware configuration
# Resolves cross-origin requests from the Next.js landing page on localhost:3000
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root endpoints
@app.get("/health", tags=["System"])
async def health_check():
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "database": "connected"
    }

# Register all modular API routes
app.include_router(api_router)
