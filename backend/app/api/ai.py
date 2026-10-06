from fastapi import APIRouter

from app.ai.router import ai_router

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.get("/status")
def ai_status():
    """Which providers are configured and whether any is paused. Never shows keys."""
    return ai_router.status()
