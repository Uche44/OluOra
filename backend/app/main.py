from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.router import api_router

# Import all models at startup to register them in SQLAlchemy's class registry
from app.modules.users.models import User, SocialAccount, ApiQuotaUsage, RefreshToken
from app.modules.youtube.models import Channel, Video
from app.modules.comments.models import Comment
from app.modules.analysis.models import Analysis, TopicCluster, Insight, AnalysisJob

app = FastAPI(
    title="OluOra API",
    description="Audience Intelligence API for video creators",
    version="1.0.0",
    debug=settings.DEBUG
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
