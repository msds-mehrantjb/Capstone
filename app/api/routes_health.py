# backend/app/api/routes_health.py

from fastapi import APIRouter
from datetime import datetime
import platform


router = APIRouter(
    prefix="/health",
    tags=["Health"],
)


@router.get("")
async def health_check():
    """
    Basic health check endpoint.
    Used by frontend, monitoring, and dev scripts.
    """
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/detailed")
async def detailed_health_check():
    """
    Detailed system health information.
    Useful for debugging and monitoring.
    """
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "system": {
            "platform": platform.system(),
            "platform_release": platform.release(),
            "python_version": platform.python_version(),
        },
        "services": {
            "api": "running",
            "agent_runtime": "not_initialized",
            "vector_db": "not_initialized",
            "llm": "not_initialized",
        },
    }
