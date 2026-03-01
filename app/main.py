# /app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import routers
from app.api.routes_health import router as health_router
from app.api.routes_events import router as events_router
from app.api.routes_agent import router as agent_router
from app.api.routes_rag import router as rag_router
from app.api.routes_dashboard import router as dashboard_router
from app.api.routes_scope import router as scope_router
from app.api.routes_scope_agent import router as scope_agent_router
from app.api.routes_system_status import router as system_status_router



# Optional future routers (uncomment when created)
# from app.api.routes_events import router as events_router
# from app.api.routes_agent import router as agent_router
# from app.api.routes_rag import router as rag_router
from app.api.routes_dashboard import router as dashboard_router
# from app.api.routes_reports import router as reports_router


def create_app() -> FastAPI:
    """
    Application factory function.
    This makes testing and scaling easier.
    """

    app = FastAPI(
        title="Agent-Based Risk Analysis API",
        description="Backend for Agent-based ISO 27001 risk assessment system",
        version="0.1.0",
    )

    # Enable CORS for React frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",  # Vite default
            "http://localhost:3000",  # React default
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routers
    app.include_router(health_router)

    app.include_router(events_router)

    app.include_router(agent_router)

    app.include_router(rag_router)

    app.include_router(dashboard_router)

    app.include_router(scope_router)

    app.include_router(scope_agent_router)

    app.include_router(system_status_router)

    return app


# Create app instance
app = create_app()


# Optional startup hook
@app.on_event("startup")
async def startup_event():
    print("Backend started successfully")


# Optional shutdown hook
@app.on_event("shutdown")
async def shutdown_event():
    print("Backend shutdown complete")
