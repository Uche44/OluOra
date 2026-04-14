from fastapi import FastAPI
from app.api.v1.router import api_router
from app.core.config import settings

app = FastAPI(title=settings.PROJECT_NAME)

# Include API routes
app.include_router(api_router, prefix="/api")

@app.get("/")
async def read_root():
    return {"message": f"Welcome to {settings.PROJECT_NAME} API"}