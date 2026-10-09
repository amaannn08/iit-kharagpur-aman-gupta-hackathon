"""Versioned stress shock catalog and scaling engine (PRD Section 9.2), version shocks_v2.

Systemic shocks at impact 8 are the measured market moves of real historical windows
(scripts/data/calibrate_shocks.py -> data/market/stress_windows.json): S&P 500 move, 10-year
Treasury yield change, implied high-yield spread change from HYG vs IEF, and PD via the credit
triangle (spread ~ PD x LGD). The data showed that credit and geopolitical stress *lower*
Treasury yields (flight to quality); only a tightening macro shock raises them.

Single-name shocks keep the PRD's documented assumptions (the SVB window's +139 bp / +2.3 pp
independently supports the PRD's +150 bp / +2.5 pp credit shock).
Shocks scale linearly with impact / 8, bounded to [0.125, 1.25].
"""

from dataclasses import dataclass
from typing import Dict, Optional

SHOCK_CATALOG_VERSION = "shocks_v2"


@dataclass(frozen=True)
class ShockParameters:
    """Stress shocks calibrated at baseline Impact = 8."""

    bond_spread_shift_bps: float = 0.0
    loan_pd_increment: float = 0.0
    lgd_increment: float = 0.0
    benchmark_yield_shift_bps: float = 0.0
    equity_shock_pct: float = 0.0
    description: str = ""
    anchor: str = "assumption"


# Systemic shocks: measured windows (values copied from data/market/stress_windows.json;
# tests/test_stress_shocks.py keeps them consistent).
MACRO_TIGHTENING = ShockParameters(
    bond_spread_shift_bps=68.2,
    loan_pd_increment=0.0114,
    benchmark_yield_shift_bps=26.3,
    equity_shock_pct=-0.0867,
    description="Fed 75 bp surprise week: S&P -8.7%, 10y +26 bp, HY spread +68 bp",
    anchor="fed_jun_2022",
)
MACRO_EASING = ShockParameters(
    bond_spread_shift_bps=2.6,
    loan_pd_increment=0.0004,
    benchmark_yield_shift_bps=-85.9,
    equity_shock_pct=0.1168,
    description="Fed pivot rally: S&P +11.7%, 10y -86 bp, spreads flat",
    anchor="fed_pivot_2023",
)
CREDIT_SYSTEMIC = ShockParameters(
    bond_spread_shift_bps=139.0,
    loan_pd_increment=0.0232,
    benchmark_yield_shift_bps=-58.1,
    equity_shock_pct=-0.0187,
    description="SVB failure: HY spread +139 bp, PD +2.3 pp, 10y -58 bp (flight to quality)",
    anchor="svb_2023",
)
GEOPOLITICAL_SYSTEMIC = ShockParameters(
    bond_spread_shift_bps=54.4,
    loan_pd_increment=0.0091,
    benchmark_yield_shift_bps=-10.5,
    equity_shock_pct=-0.0135,
    description="Russia-Ukraine invasion: HY spread +54 bp, 10y -11 bp, S&P -1.3%",
    anchor="russia_2022",
)

# Primary (single-name / sector) shocks per class: PRD assumptions.
DEFAULT_SHOCK_CATALOG: Dict[str, ShockParameters] = {
    "CREDIT": ShockParameters(
        bond_spread_shift_bps=150.0,
        loan_pd_increment=0.025,
        lgd_increment=0.05,
        equity_shock_pct=-0.15,
        description="Issuer spread +150 bps, PD +2.5 pp, LGD +5 pp, equity -15%",
    ),
    "MACRO": MACRO_TIGHTENING,
    "GEOPOLITICAL": GEOPOLITICAL_SYSTEMIC,
    "SUPPLY_CHAIN": ShockParameters(
        bond_spread_shift_bps=80.0,
        loan_pd_increment=0.012,
        lgd_increment=0.03,
        equity_shock_pct=-0.06,
        description="Issuer/sector spread +80 bps, PD +1.2 pp, LGD +3 pp, equity -6%",
    ),
    "CYBER": ShockParameters(
        bond_spread_shift_bps=60.0,
        loan_pd_increment=0.008,
        lgd_increment=0.02,
        equity_shock_pct=-0.05,
        description="Issuer spread +60 bps, PD +0.8 pp, equity -5%, plus fraud operational loss",
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
    equity_shock_pct: float = 0.0
    operational_loss_multiplier: float = 0.0  # x observed sector fraud rate (CYBER)
    catalog_entry: str = ""
    target_sector: Optional[str] = None  # sector of the target entity (CYBER operational loss)


# Severe cyber event: operational losses at this multiple of the observed card-fraud rate.
CYBER_FRAUD_MULTIPLIER = 10.0


def select_parameters(event_class: str, target_scope: str, is_easing: bool) -> ShockParameters:
    cls = event_class.upper()
    if cls == "MACRO":
        return MACRO_EASING if is_easing else MACRO_TIGHTENING
    if cls == "CREDIT" and target_scope == "systemic":
        return CREDIT_SYSTEMIC
    return DEFAULT_SHOCK_CATALOG.get(
        cls, ShockParameters(description="No automatic stress mapping")
    )


def build_scaled_shock(
    event_class: str,
    impact_score: int,
    target_entity: Optional[str] = None,
    target_scope: str = "entity",
    is_easing: bool = False,
    target_sector: Optional[str] = None,
) -> ScaledShock:
    """Scale the selected catalog entry proportionally by impact_score / 8.0."""
    baseline = select_parameters(event_class, target_scope, is_easing)
    scale = max(0.125, min(1.25, impact_score / 8.0))
    return ScaledShock(
        bond_spread_shift_bps=round(baseline.bond_spread_shift_bps * scale, 2),
        loan_pd_increment=round(baseline.loan_pd_increment * scale, 4),
        lgd_increment=round(baseline.lgd_increment * scale, 4),
        benchmark_yield_shift_bps=round(baseline.benchmark_yield_shift_bps * scale, 2),
        scale_multiplier=scale,
        target_entity=target_entity,
        target_scope=target_scope,
        equity_shock_pct=round(baseline.equity_shock_pct * scale, 4),
        operational_loss_multiplier=CYBER_FRAUD_MULTIPLIER * scale
        if event_class.upper() == "CYBER"
        else 0.0,
        catalog_entry=f"{SHOCK_CATALOG_VERSION}:{baseline.anchor}",
        target_sector=target_sector,
    )


def shock_from_scenario(scenario: dict) -> ScaledShock:
    """Unscaled shock for a named scenario file (data/scenarios/*.json)."""
    direct = scenario.get("direct_shocks", {})
    macro = scenario.get("macro_shocks", {})
    equity = scenario.get("equity_shocks", {})
    target = scenario.get("target_entity")
    if target and str(target).upper() in ("MACRO", "SYSTEMIC"):
        target = None  # legacy files mark systemic scenarios with target_entity "MACRO"
    scope = scenario.get("target_scope") or ("entity" if target else "systemic")
    return ScaledShock(
        bond_spread_shift_bps=float(direct.get("bond_spread_shift_bps", 0.0)),
        loan_pd_increment=float(direct.get("loan_pd_increment", 0.0)),
        lgd_increment=float(direct.get("lgd_increment", 0.0)),
        benchmark_yield_shift_bps=float(macro.get("benchmark_yield_shift_bps", 0.0)),
        scale_multiplier=1.0,
        target_entity=None if scope == "systemic" else target,
        target_scope=scope,
        equity_shock_pct=float(equity.get("equity_shock_pct", 0.0)),
        catalog_entry=f"scenario:{scenario.get('scenario_id')}",
    )
