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
from sentinel.api.routes.index import router as index_router
from sentinel.api.routes.replay import live_tailer
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
    """Lifecycle events: initialize SQLite database on startup, prime demo replay, manage background tasks."""
    init_db()

    # Pre-populate initial demo scenario if queue is empty and DB has no signals
    try:
        from sentinel.api.routes.replay import (
            _load_source,
            emit_signal,
            nlp_engine,
            replay_controller,
        )
        from sentinel.storage.db import SessionLocal
        from sentinel.storage.repository import ReplayRepository

        with SessionLocal() as db:
            repo = ReplayRepository(db)
            if not replay_controller._queue:
                demo_records = _load_source("news_demo") + _load_source("social_demo")
                if demo_records:
                    badges = [
                        settings.replay_sources["news_demo"][2],
                        settings.replay_sources["social_demo"][2],
                    ]
                    replay_controller.load_scenario(
                        "demo",
                        demo_records,
                        sources=["news_demo", "social_demo"],
                        badges=badges,
                    )
            # If database has fewer than 10 signals, advance records so feed is populated on cold start
            existing_count = len(repo.list_signals(limit=10))
            if existing_count < 10 and replay_controller._queue:
                to_step = min(10 - existing_count, len(replay_controller._queue))
                for _ in range(to_step):
                    async def persist_and_process(record, dedup):
                        repo.save_record(record, dedup, run_id=replay_controller.run_id)
                        signals = nlp_engine.process_record_multi(
                            record,
                            run_id=replay_controller.run_id,
                            dedup_decision=dedup,
                        )
                        for sig in signals:
                            await emit_signal(repo, record, sig)
                        return signals

                    await replay_controller.step(processor=persist_and_process)
            repo.upsert_run(replay_controller.get_status())
    except Exception as e:
        import logging
        logging.getLogger("sentinel").warning(f"Startup replay priming notice: {e}")

    if settings.live_tail_enabled:
        live_tailer.start()
    try:
        yield
    finally:
        from sentinel.api.routes.replay import _stop_playback_loop

        _stop_playback_loop()
        if settings.live_tail_enabled:
            live_tailer.stop()


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
    app.include_router(index_router, prefix="/api")

    # Direct aliases for API route compatibility
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
