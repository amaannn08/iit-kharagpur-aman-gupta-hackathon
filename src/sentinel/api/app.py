"""FastAPI application factory and middleware configuration."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from sentinel.api.routes.analyze import router as analyze_router
from sentinel.api.routes.datasets import router as datasets_router
from sentinel.api.routes.events import router as events_router
from sentinel.api.routes.exports import router as exports_router
from sentinel.api.routes.health import router as health_router
from sentinel.api.routes.replay import router as replay_router
from sentinel.api.routes.signals import router as signals_router
from sentinel.api.routes.stress import (
    get_portfolio,
    get_stress_run_detail,
    simulate_stress,
)
from sentinel.api.routes.stress import (
    router as stress_router,
)
from sentinel.config import settings
from sentinel.storage.db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events: initialize SQLite database on startup."""
    init_db()
    yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.project_name,
        version=settings.version,
        description=(
            "Offline financial-text risk intelligence and wholesale portfolio stress testing"
        ),
        lifespan=lifespan,
    )

    # Restrict CORS to localhost origins for security
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://127.0.0.1:3000",
            "http://localhost:3000",
            "http://127.0.0.1:5173",
            "http://localhost:5173",
            "http://127.0.0.1:8000",
            "http://localhost:8000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount API routers
    app.include_router(health_router, prefix="/api")
    app.include_router(datasets_router, prefix="/api")
    app.include_router(replay_router, prefix="/api")
    app.include_router(signals_router, prefix="/api")
    app.include_router(stress_router, prefix="/api")
    app.include_router(analyze_router, prefix="/api")
    app.include_router(events_router, prefix="/api")
    app.include_router(exports_router, prefix="/api")

    # Direct aliases conforming to exact PRD Section 12 specifications
    app.add_api_route("/api/portfolio", get_portfolio, methods=["GET"], tags=["Portfolio"])
    app.add_api_route("/api/stress", simulate_stress, methods=["POST"], tags=["Stress"])
    app.add_api_route(
        "/api/stress/{stress_id}", get_stress_run_detail, methods=["GET"], tags=["Stress"]
    )




    # Serve compiled frontend assets if available
    frontend_dist = settings.base_dir / "frontend" / "dist"
    if frontend_dist.exists() and (frontend_dist / "index.html").exists():
        app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")

    return app


app = create_app()
