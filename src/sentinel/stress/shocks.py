"""Versioned stress shock catalog and scaling engine conforming to PRD Section 9.2."""

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class ShockParameters:
    """Stress shocks calibrated at baseline Impact = 8."""

    bond_spread_shift_bps: float = 0.0
    loan_pd_increment: float = 0.0
    lgd_increment: float = 0.0
    benchmark_yield_shift_bps: float = 0.0
    description: str = ""


# Versioned default shock configurations at Impact = 8 (PRD Section 9.2)
DEFAULT_SHOCK_CATALOG: Dict[str, ShockParameters] = {
    "CREDIT": ShockParameters(
        bond_spread_shift_bps=150.0,
        loan_pd_increment=0.025,
        lgd_increment=0.05,
        benchmark_yield_shift_bps=0.0,
        description="Spread widening +150 bps, PD +2.5 pp, LGD +5 pp",
    ),
    "MACRO": ShockParameters(
        bond_spread_shift_bps=25.0,
        loan_pd_increment=0.005,
        lgd_increment=0.0,
        benchmark_yield_shift_bps=100.0,
        description="Parallel benchmark yield shift +100 bps, modest spread widening",
    ),
    "GEOPOLITICAL": ShockParameters(
        bond_spread_shift_bps=75.0,
        loan_pd_increment=0.010,
        lgd_increment=0.02,
        benchmark_yield_shift_bps=25.0,
        description="Cross-market spread widening +75 bps, yield shift +25 bps",
    ),
    "SUPPLY_CHAIN": ShockParameters(
        bond_spread_shift_bps=80.0,
        loan_pd_increment=0.012,
        lgd_increment=0.03,
        benchmark_yield_shift_bps=0.0,
        description="Sector disruption spread widening +80 bps, PD +1.2 pp",
    ),
    "CYBER": ShockParameters(
        bond_spread_shift_bps=60.0,
        loan_pd_increment=0.008,
        lgd_increment=0.02,
        benchmark_yield_shift_bps=0.0,
        description="Operational breach spread widening +60 bps, PD +0.8 pp",
    ),
}


@dataclass(frozen=True)
class ScaledShock:
    """Applied shock scaled by impact / 8 and directed by sentiment/context."""

    bond_spread_shift_bps: float
    loan_pd_increment: float
    lgd_increment: float
    benchmark_yield_shift_bps: float
    scale_multiplier: float
    target_entity: Optional[str]
    target_scope: str  # "entity", "sector", "systemic"


def build_scaled_shock(
    event_class: str,
    impact_score: int,
    target_entity: Optional[str] = None,
    target_scope: str = "entity",
    is_easing: bool = False,
) -> ScaledShock:
    """Scale baseline shock parameters proportionally by impact_score / 8.0."""
    baseline = DEFAULT_SHOCK_CATALOG.get(
        event_class.upper(),
        ShockParameters(description="No automatic stress mapping"),
    )

    scale = max(0.125, min(1.25, impact_score / 8.0))

    # Yield shift direction: rate cut/easing shifts yields downwards
    yield_direction = -1.0 if is_easing else 1.0
    spread_shift = 0.0 if is_easing else baseline.bond_spread_shift_bps * scale
    pd_inc = 0.0 if is_easing else baseline.loan_pd_increment * scale
    lgd_inc = 0.0 if is_easing else baseline.lgd_increment * scale

    return ScaledShock(
        bond_spread_shift_bps=round(spread_shift, 2),
        loan_pd_increment=round(pd_inc, 4),
        lgd_increment=round(lgd_inc, 4),
        benchmark_yield_shift_bps=round(
            baseline.benchmark_yield_shift_bps * scale * yield_direction, 2
        ),
        scale_multiplier=scale,
        target_entity=target_entity,
        target_scope=target_scope,
    )
