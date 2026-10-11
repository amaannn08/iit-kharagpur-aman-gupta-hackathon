import asyncio
import logging
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from sentinel.api.events import broadcaster
from sentinel.api.routes.index import rebalancer
from sentinel.api.routes.stress import stress_engine
from sentinel.config import settings
from sentinel.contracts.records import InputRecord
from sentinel.contracts.signals import RiskSignal
from sentinel.contracts.stress import StressRunResult
from sentinel.ingestion.adapters import NewsAdapter, SocialAdapter
from sentinel.nlp.engine import NLPEngine
from sentinel.replay.controller import (
    ReplayController,
    ReplayStatus,
    ReplayStepResult,
    RunState,
)
from sentinel.replay.live_tail import LiveTailer
from sentinel.storage.db import SessionLocal, get_db
from sentinel.storage.repository import ReplayRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/replay", tags=["Replay Controller"])

# Singleton controller and NLP engine instances for backend runtime
replay_controller = ReplayController()
nlp_engine = NLPEngine()
live_tailer = LiveTailer(
    replay_controller, settings.data_dir / "live", poll_interval=settings.live_poll_seconds
)


class LoadScenarioRequest(BaseModel):
    scenario_id: str
    sources: List[str] = ["news_demo", "social_demo"]


class SetSpeedRequest(BaseModel):
    speed: float


class PersistedRunResponse(BaseModel):
    run_id: str
    scenario_id: Optional[str]
    status: str
    speed: float
    total_records: int
    processed_records: int
    duplicate_count: int
    error_count: int


class PersistedRecordResponse(BaseModel):
    record_id: str
    source_id: str
    source_type: str
    text: str
    is_duplicate: bool
    duplicate_group_id: Optional[str]
    canonical_record_id: Optional[str]
    sequence_number: Optional[int]


SIGNAL_SINK = Path("data/signals.jsonl")


async def emit_signal(
    repo: ReplayRepository, record: InputRecord, sig: RiskSignal
) -> Optional[StressRunResult]:
    """Persist a signal, append it to the JSONL sink, run the Module B trigger, broadcast."""
    repo.save_signal(sig)

    # PS R3 literal compliance: append emitted signal JSON line to file sink
    try:
        SIGNAL_SINK.parent.mkdir(parents=True, exist_ok=True)
        with open(SIGNAL_SINK, "a", encoding="utf-8") as f:
            f.write(sig.model_dump_json() + "\n")
    except Exception as exc:
        logger.warning("Failed writing to signals.jsonl sink: %s", exc)

    # Module A: every signal updates the mock index sentiment (blocked/duplicate ones are ignored)
    rebalancer.on_signal(sig)

    # Module B automated stress test trigger on eligible high-impact signals
    stress_result = None
    if stress_engine.should_trigger(sig):
        source_meta = settings.replay_sources.get(record.source_id)
        if source_meta:
            badge = source_meta[2]
            profile = "synthetic_demo" if badge == "SYNTHETIC SCENARIO" else "real_issuers"
        else:
            demo_engine = stress_engine.profiles.get("synthetic_demo", stress_engine.portfolio)
            real_engine = stress_engine.profiles.get("real_issuers", stress_engine.portfolio)
            if (
                sig.entity.ticker
                and sig.entity.ticker.upper() in demo_engine.held_tickers
                and sig.entity.ticker.upper() not in real_engine.held_tickers
            ):
                profile = "synthetic_demo"
            else:
                profile = "synthetic_demo" if record.is_synthetic else "real_issuers"
        stress_result = stress_engine.trigger_from_signal(sig, profile=profile)
        if stress_result:
            repo.save_stress_run(stress_result)

    await broadcaster.broadcast(
        event_type="signal_emitted",
        data={
            "signal": sig.model_dump(mode="json"),
            "record": record.model_dump(mode="json"),
            "stress_run": stress_result.model_dump(mode="json") if stress_result else None,
        },
    )
    await broadcaster.broadcast(
        event_type="signal",
        data=sig.model_dump(mode="json"),
    )
    if stress_result:
        await broadcaster.broadcast(
            event_type="stress_run",
            data=stress_result.model_dump(mode="json"),
        )
    return stress_result


@router.get("/status", response_model=ReplayStatus)
def get_replay_status() -> ReplayStatus:
    """Return live status of the logical replay clock and run queue."""
    if replay_controller.scenario_id is None and not replay_controller._queue:
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
    return replay_controller.get_status()


@router.get("/live_status")
def get_live_status() -> dict:
    """Return live capture ingestion status, lag seconds, and recorder process liveness."""
    return live_tailer.get_live_status()


@router.get("/presets")
def get_replay_presets() -> dict:
    """Return available replay scenario presets."""
    return {
        "presets": [
            {
                "id": "demo",
                "label": "Synthetic demo scenario (news + social)",
                "sources": ["news_demo", "social_demo"],
                "badge": "SYNTHETIC SCENARIO",
            },
            {
                "id": "polygon_news",
                "label": "Real news: Polygon 2023 (5,548 articles)",
                "sources": ["polygon_2023"],
                "badge": "HISTORICAL REPLAY",
            },
            {
                "id": "stock_tweets",
                "label": "Real stock tweets (5,000 held-out)",
                "sources": ["stock_tweets"],
                "badge": "HISTORICAL REPLAY",
            },
            {
                "id": "gdelt_svb",
                "label": "GDELT: SVB failure weekend (March 2023)",
                "sources": ["gdelt_svb_2023"],
                "badge": "HISTORICAL REPLAY",
            },
            {
                "id": "live_recorder",
                "label": "Live capture (GDELT + SEC 8-K)",
                "sources": ["gdelt_live", "sec_8k_live"],
                "badge": "LIVE CAPTURE",
            },
        ]
    }


def _load_source(name: str) -> List[InputRecord]:
    rel, kind, _ = settings.replay_sources[name]
    path = settings.data_dir / rel
    if not path.exists():
        return []
    adapter = NewsAdapter if kind == "news" else SocialAdapter
    return adapter.load_from_csv(path)


@router.get("/sources")
def list_replay_sources() -> List[dict]:
    """Registered replay sources with badge and availability (live files appear when recorded)."""
    out = []
    for name, (rel, kind, badge) in settings.replay_sources.items():
        path = settings.data_dir / rel
        out.append({"source": name, "kind": kind, "badge": badge, "path": f"data/{rel}",
                    "available": path.exists()})  # fmt: skip
    return out


@router.post("/load", response_model=ReplayStatus)
def load_replay_scenario(
    req: LoadScenarioRequest,
    db: Session = Depends(get_db),
) -> ReplayStatus:
    """Load records from one or more registered sources into the bounded replay queue."""
    unknown = [s for s in req.sources if s not in settings.replay_sources]
    if unknown:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown sources {unknown}; valid: {sorted(settings.replay_sources)}",
        )
    repo = ReplayRepository(db)
    all_records: List[InputRecord] = []
    for name in req.sources:
        all_records.extend(_load_source(name))
    if not all_records:
        raise HTTPException(status_code=400, detail="No records found for the requested sources.")
    if len(all_records) > replay_controller.max_queue_size:
        raise HTTPException(
            status_code=400,
            detail=f"{len(all_records)} records exceed the bounded queue ({replay_controller.max_queue_size}).",
        )

    _stop_playback_loop()
    badges = [settings.replay_sources[n][2] for n in req.sources]
    replay_controller.load_scenario(
        req.scenario_id, all_records, sources=req.sources, badges=badges
    )
    status = replay_controller.get_status()
    repo.upsert_run(status)
    return status


class AppendRequest(BaseModel):
    source: str


@router.post("/append", response_model=ReplayStatus)
def append_new_records(req: AppendRequest, db: Session = Depends(get_db)) -> ReplayStatus:
    """Queue records that appeared in a (live capture) source file since the run was loaded."""
    if req.source not in settings.replay_sources:
        raise HTTPException(status_code=400, detail=f"Unknown source {req.source}")
    replay_controller.append_records(_load_source(req.source))
    status = replay_controller.get_status()
    ReplayRepository(db).upsert_run(status)
    return status


_playback_task: Optional[asyncio.Task] = None


async def _run_playback_loop() -> None:
    logger.info("Starting background replay playback loop.")
    try:
        while replay_controller.state == RunState.RUNNING:
            if not replay_controller._queue:
                replay_controller._state = RunState.COMPLETED
                with SessionLocal() as db:
                    ReplayRepository(db).upsert_run(replay_controller.get_status())
                await broadcaster.broadcast(
                    event_type="replay_status",
                    data=replay_controller.get_status().model_dump(mode="json"),
                )
                break

            with SessionLocal() as db:
                repo = ReplayRepository(db)

                async def persist_and_process(record: InputRecord, dedup) -> List[RiskSignal]:
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
                st = replay_controller.get_status()
                repo.upsert_run(st)

            await broadcaster.broadcast(
                event_type="replay_status",
                data=st.model_dump(mode="json"),
            )

            speed = replay_controller.clock.speed
            delay = max(0.05, 1.0 / max(0.1, speed))
            await asyncio.sleep(delay)
    except asyncio.CancelledError:
        logger.info("Replay playback task cancelled.")
    except Exception as exc:
        logger.error("Error in replay playback loop: %s", exc, exc_info=True)


def _start_playback_loop() -> None:
    global _playback_task
    if _playback_task is None or _playback_task.done():
        try:
            loop = asyncio.get_running_loop()
            _playback_task = loop.create_task(_run_playback_loop())
        except RuntimeError:
            pass


def _stop_playback_loop() -> None:
    global _playback_task
    if _playback_task and not _playback_task.done():
        _playback_task.cancel()
        _playback_task = None


@router.post("/step", response_model=Optional[ReplayStepResult])
async def step_replay(
    db: Session = Depends(get_db),
) -> Optional[ReplayStepResult]:
    """Deterministically advance one record from the replay queue and emit RiskSignal."""
    repo = ReplayRepository(db)

    async def persist_and_process(record: InputRecord, dedup) -> List[RiskSignal]:
        repo.save_record(record, dedup, run_id=replay_controller.run_id)
        signals = nlp_engine.process_record_multi(
            record,
            run_id=replay_controller.run_id,
            dedup_decision=dedup,
        )
        for sig in signals:
            await emit_signal(repo, record, sig)
        return signals

    step_result = await replay_controller.step(processor=persist_and_process)
    status = replay_controller.get_status()
    repo.upsert_run(status)
    await broadcaster.broadcast(
        event_type="replay_status",
        data=status.model_dump(mode="json"),
    )
    return step_result


@router.post("/pause", response_model=ReplayStatus)
async def pause_replay(db: Session = Depends(get_db)) -> ReplayStatus:
    """Pause replay execution."""
    _stop_playback_loop()
    replay_controller.pause()
    status = replay_controller.get_status()
    ReplayRepository(db).upsert_run(status)
    await broadcaster.broadcast(
        event_type="replay_status",
        data=status.model_dump(mode="json"),
    )
    return status


@router.post("/resume", response_model=ReplayStatus)
async def resume_replay(db: Session = Depends(get_db)) -> ReplayStatus:
    """Resume replay execution and start continuous background playback."""
    replay_controller.resume()
    status = replay_controller.get_status()
    ReplayRepository(db).upsert_run(status)
    _start_playback_loop()
    await broadcaster.broadcast(
        event_type="replay_status",
        data=status.model_dump(mode="json"),
    )
    return status


@router.post("/reset", response_model=ReplayStatus)
async def reset_replay(db: Session = Depends(get_db)) -> ReplayStatus:
    """Reset replay controller, clear queue, and assign a clean run ID."""
    _stop_playback_loop()
    replay_controller.reset()
    stress_engine.reset_triggers()
    rebalancer.reset()
    status = replay_controller.get_status()
    ReplayRepository(db).upsert_run(status)
    await broadcaster.broadcast(
        event_type="replay_status",
        data=status.model_dump(mode="json"),
    )
    return status


@router.post("/speed", response_model=ReplayStatus)
def set_replay_speed(
    req: SetSpeedRequest,
    db: Session = Depends(get_db),
) -> ReplayStatus:
    """Configure logical clock replay speed (e.g. 1.0, 5.0, 20.0)."""
    if req.speed <= 0:
        raise HTTPException(status_code=400, detail="Speed must be positive")
    replay_controller.set_speed(req.speed)
    status = replay_controller.get_status()
    ReplayRepository(db).upsert_run(status)
    return status


@router.get("/runs", response_model=List[PersistedRunResponse])
def list_persisted_runs(db: Session = Depends(get_db)) -> List[PersistedRunResponse]:
    """List historical replay runs persisted in SQLite."""
    runs = ReplayRepository(db).list_runs()
    return [
        PersistedRunResponse(
            run_id=r.run_id,
            scenario_id=r.scenario_id,
            status=r.status,
            speed=r.speed,
            total_records=r.total_records,
            processed_records=r.processed_records,
            duplicate_count=r.duplicate_count,
            error_count=r.error_count,
        )
        for r in runs
    ]


@router.get("/runs/{run_id}/records", response_model=List[PersistedRecordResponse])
def get_run_records(
    run_id: str,
    db: Session = Depends(get_db),
) -> List[PersistedRecordResponse]:
    """Retrieve audit trail of records processed in a run including deduplication."""
    recs = ReplayRepository(db).get_records_for_run(run_id)
    return [
        PersistedRecordResponse(
            record_id=r.record_id,
            source_id=r.source_id,
            source_type=r.source_type,
            text=r.text,
            is_duplicate=r.is_duplicate,
            duplicate_group_id=r.duplicate_group_id,
            canonical_record_id=r.canonical_record_id,
            sequence_number=r.sequence_number,
        )
        for r in recs
    ]
