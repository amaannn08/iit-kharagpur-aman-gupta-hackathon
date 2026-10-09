"""Module A API: sentiment-driven mock index weights (PS Section 3, PRD Section 10)."""

from dataclasses import asdict
from typing import Any, Dict, List

from fastapi import APIRouter, Query

from sentinel.rebalance import IndexRebalancer

router = APIRouter(prefix="/index", tags=["Module A: Index Rebalancer"])

# Shared singleton fed by every emitted signal (see routes/replay.py emit_signal)
rebalancer = IndexRebalancer()


@router.get("/current")
def get_current_index() -> Dict[str, Any]:
    """Current weights, sentiment EMAs, sectors and constraints of the mock index."""
    last = rebalancer.history[-1]
    return {
        "label": "Mock index (20 S&P 100 names), not an S&P product",
        "weights": rebalancer.weights,
        "base_weights": rebalancer.base,
        "sentiment_ema": last.sentiment_ema,
        "sectors": rebalancer.universe,
        "reasons": last.reasons,
        "constraints": {
            "name_cap": rebalancer.name_cap,
            "sector_cap": rebalancer.sector_cap,
            "k": rebalancer.k,
            "halflife_days": rebalancer.halflife_days,
            "long_only": True,
        },
        "rebalances": len(rebalancer.history) - 1,
    }


@router.get("/history")
def get_index_history(limit: int = Query(default=500, ge=1, le=5000)) -> List[Dict[str, Any]]:
    """Weights over time (for the PS weights-over-time dashboard), oldest first."""
    return [asdict(r) for r in rebalancer.history[-limit:]]


@router.post("/reset")
def reset_index() -> Dict[str, Any]:
    rebalancer.reset()
    return get_current_index()
