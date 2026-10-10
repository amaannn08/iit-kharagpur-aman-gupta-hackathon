"""Wholesale banking stress testing API routes."""

import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from sentinel.contracts.stress import StressRunResult
from sentinel.nlp.entities import EntityLinker
from sentinel.storage.db import get_db
from sentinel.storage.repository import ReplayRepository
from sentinel.stress.engine import StressEngine
from sentinel.stress.sectors import normalize_sector
from sentinel.stress.shocks import DEFAULT_SHOCK_CATALOG

router = APIRouter(prefix="/stress", tags=["Stress Testing Engine"])

# Shared singleton stress engine instance for backend runtime
stress_engine = StressEngine()
_linker = EntityLinker()


class ManualStressRequest(BaseModel):
    event_class: str = Field(..., description="CREDIT, MACRO, GEOPOLITICAL, SUPPLY_CHAIN, or CYBER")

    @field_validator("event_class")
    @classmethod
    def known_event_class(cls, v: str) -> str:
        # Unknown classes used to run silently as a zero shock (a $0 'stress test')
        v = v.strip().upper()
        if v not in DEFAULT_SHOCK_CATALOG:
            raise ValueError(f"event_class must be one of {sorted(DEFAULT_SHOCK_CATALOG)}")
        return v

    @field_validator("target_scope")
    @classmethod
    def known_scope(cls, v: str) -> str:
        if v not in ("entity", "sector", "systemic"):
            raise ValueError("target_scope must be entity, sector or systemic")
        return v

    impact_score: int = Field(8, ge=1, le=10, description="Severity score 1 to 10")
    target_entity: Optional[str] = Field(None, description="Ticker or entity identifier, e.g. APEX")
    target_scope: str = Field("entity", description="entity, sector, or systemic")
    is_easing: bool = Field(False, description="True for interest rate cut / easing scenario")
    run_id: str = Field("manual-sandbox", description="Associated run identifier")
    profile: Optional[str] = Field(None, description="Portfolio profile: real_issuers or synthetic_demo")


def _resolve_target(target: Optional[str]) -> Optional[str]:
    """Accept a ticker ('APEX') or a company name ('Apex Industrial Holdings')."""
    if not target:
        return None
    held = set()
    for prof in stress_engine.profiles.values():
        held |= prof.held_tickers
    if target.upper() in held or target.upper() in _linker.entities:
        return target.upper()
    companies = list(_linker.find_companies(target))
    return companies[0] if companies else None


def _sector_of(target: Optional[str]) -> Optional[str]:
    if not target:
        return None
    ent = _linker.entities.get(target.upper())
    if ent and ent.sector:
        return normalize_sector(ent.sector)
    for prof in stress_engine.profiles.values():
        for p in prof.all_positions():
            if p.entity_id.upper() == target.upper():
                return normalize_sector(p.sector)
    return None


class CustomStressRequest(BaseModel):
    """Explicit systemic shock set (PS Module B example: equities -10%, rates +2%)."""

    equity_shock_pct: float = Field(0.0, ge=-1.0, le=1.0, description="e.g. -0.10 for -10%")
    benchmark_yield_shift_bps: float = Field(0.0, ge=-1000, le=1000)
    bond_spread_shift_bps: float = Field(0.0, ge=-1000, le=3000)
    loan_pd_increment: float = Field(0.0, ge=-1.0, le=1.0)
    lgd_increment: float = Field(0.0, ge=-1.0, le=1.0)
    pd_from_spread: bool = False
    run_id: str = "custom-sandbox"
    profile: Optional[str] = Field(None, description="Portfolio profile: real_issuers or synthetic_demo")


class PersistedStressSummary(BaseModel):
    stress_id: str
    run_id: str
    scenario_id: Optional[str]
    trigger_signal_id: Optional[str]
    baseline_value_usd: float
    stressed_value_usd: float
    total_loss_usd: float
    executed_at: str


@router.get("/portfolio")
def get_portfolio(profile: Optional[str] = None) -> Dict[str, Any]:
    """Return synthetic wholesale baseline portfolio with funded and derivative segregation."""
    prof_name = profile or "synthetic_demo"
    prof = stress_engine.profiles.get(prof_name, stress_engine.portfolio)
    return prof.to_dict()


@router.post("/simulate", response_model=StressRunResult)
def simulate_stress(
    req: ManualStressRequest,
    db: Session = Depends(get_db),
) -> StressRunResult:
    """Execute a user-triggered / sandbox multi-asset stress simulation."""
    target = req.target_entity
    if req.target_scope == "entity":
        target = _resolve_target(target)
        if target is None:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown target entity '{req.target_entity}' for entity scope",
            )
    sector = (
        _sector_of(target)
        if req.target_scope == "entity"
        else normalize_sector(req.target_entity)
        if req.target_scope == "sector"
        else None
    )
    prof = req.profile
    if not prof:
        demo_port = stress_engine.profiles.get("synthetic_demo", stress_engine.portfolio)
        real_port = stress_engine.profiles.get("real_issuers", stress_engine.portfolio)
        if target and target.upper() in demo_port.held_tickers and target.upper() not in real_port.held_tickers:
            prof = "synthetic_demo"
        else:
            prof = "real_issuers"

    result = stress_engine.run_manual_stress(
        event_class=req.event_class,
        impact_score=req.impact_score,
        target_entity=target,
        target_scope=req.target_scope,
        is_easing=req.is_easing,
        run_id=req.run_id,
        target_sector=sector,
        profile=prof,
    )

    repo = ReplayRepository(db)
    repo.save_stress_run(result)
    return result


@router.get("/scenarios")
def list_stress_scenarios() -> Dict[str, Any]:
    """Runnable named scenarios, including five measured historical stress windows."""
    return {"scenarios": stress_engine.list_scenarios()}


@router.post("/scenario/{scenario_id}", response_model=StressRunResult)
def run_stress_scenario(
    scenario_id: str,
    profile: Optional[str] = "real_issuers",
    db: Session = Depends(get_db),
) -> StressRunResult:
    """Run a named scenario file against the full portfolio and persist the result."""
    try:
        result = stress_engine.run_scenario(
            scenario_id,
            run_id=f"scenario-{scenario_id}",
            profile=profile or "real_issuers",
        )
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Scenario '{scenario_id}' not found.")
    ReplayRepository(db).save_stress_run(result)
    return result


@router.post("/custom", response_model=StressRunResult)
def run_custom_stress(req: CustomStressRequest, db: Session = Depends(get_db)) -> StressRunResult:
    """Run an explicit systemic shock set and persist the result."""
    result = stress_engine.run_custom_stress(**req.model_dump())
    ReplayRepository(db).save_stress_run(result)
    return result


@router.get("/runs", response_model=List[PersistedStressSummary])
def list_stress_runs(
    run_id: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
) -> List[PersistedStressSummary]:
    """List historical stress testing runs with financial loss summaries."""
    repo = ReplayRepository(db)
    models = repo.list_stress_runs(run_id=run_id, limit=limit)
    return [
        PersistedStressSummary(
            stress_id=m.stress_id,
            run_id=m.run_id,
            scenario_id=m.scenario_id,
            trigger_signal_id=m.trigger_signal_id,
            baseline_value_usd=m.baseline_value_usd,
            stressed_value_usd=m.stressed_value_usd,
            total_loss_usd=m.total_loss_usd,
            executed_at=m.executed_at.isoformat() if m.executed_at else "",
        )
        for m in models
    ]


@router.get("/{stress_id}", response_model=StressRunResult)
def get_stress_run_detail(
    stress_id: str,
    db: Session = Depends(get_db),
) -> StressRunResult:
    """Retrieve full breakdown, position deltas, and audit record for a stress test."""
    repo = ReplayRepository(db)
    model = repo.get_stress_run(stress_id)
    if not model or not model.raw_json:
        raise HTTPException(
            status_code=404,
            detail=f"Stress run with ID '{stress_id}' not found.",
        )

    data = json.loads(model.raw_json)
    return StressRunResult.model_validate(data)
