"""Wholesale banking stress testing API routes conforming to PRD Section 9 & 12."""

import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from sentinel.contracts.stress import StressRunResult
from sentinel.storage.db import get_db
from sentinel.storage.repository import ReplayRepository
from sentinel.stress.engine import StressEngine

router = APIRouter(prefix="/stress", tags=["Stress Testing Engine"])

# Shared singleton stress engine instance for backend runtime
stress_engine = StressEngine()


class ManualStressRequest(BaseModel):
    event_class: str = Field(..., description="CREDIT, MACRO, GEOPOLITICAL, SUPPLY_CHAIN, or CYBER")
    impact_score: int = Field(8, ge=1, le=10, description="Severity score 1 to 10")
    target_entity: Optional[str] = Field(None, description="Ticker or entity identifier, e.g. APEX")
    target_scope: str = Field("entity", description="entity, sector, or systemic")
    is_easing: bool = Field(False, description="True for interest rate cut / easing scenario")
    run_id: str = Field("manual-sandbox", description="Associated run identifier")


class CustomStressRequest(BaseModel):
    """Explicit systemic shock set (PS Module B example: equities -10%, rates +2%)."""

    equity_shock_pct: float = Field(0.0, ge=-1.0, le=1.0, description="e.g. -0.10 for -10%")
    benchmark_yield_shift_bps: float = Field(0.0, ge=-1000, le=1000)
    bond_spread_shift_bps: float = Field(0.0, ge=-1000, le=3000)
    loan_pd_increment: float = Field(0.0, ge=-1.0, le=1.0)
    lgd_increment: float = Field(0.0, ge=-1.0, le=1.0)
    run_id: str = "custom-sandbox"


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
def get_portfolio() -> Dict[str, Any]:
    """Return synthetic wholesale baseline portfolio with funded and derivative segregation."""
    return stress_engine.portfolio.to_dict()


@router.post("/simulate", response_model=StressRunResult)
def simulate_stress(
    req: ManualStressRequest,
    db: Session = Depends(get_db),
) -> StressRunResult:
    """Execute a user-triggered / sandbox multi-asset stress simulation (PRD 9.3)."""
    result = stress_engine.run_manual_stress(
        event_class=req.event_class,
        impact_score=req.impact_score,
        target_entity=req.target_entity,
        target_scope=req.target_scope,
        is_easing=req.is_easing,
        run_id=req.run_id,
    )

    repo = ReplayRepository(db)
    repo.save_stress_run(result)
    return result


@router.get("/scenarios")
def list_stress_scenarios() -> Dict[str, Any]:
    """Runnable named scenarios, including five measured historical stress windows."""
    return {"scenarios": stress_engine.list_scenarios()}


@router.post("/scenario/{scenario_id}", response_model=StressRunResult)
def run_stress_scenario(scenario_id: str, db: Session = Depends(get_db)) -> StressRunResult:
    """Run a named scenario file against the full portfolio and persist the result."""
    try:
        result = stress_engine.run_scenario(scenario_id, run_id=f"scenario-{scenario_id}")
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
