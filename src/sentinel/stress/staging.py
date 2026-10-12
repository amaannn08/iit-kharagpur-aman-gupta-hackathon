"""IFRS 9 Loan Staging, CET1 Capital Impact, and Reverse Stress Testing engine.

Under IFRS 9 (Financial Instruments), banks must recognize Expected Credit Loss (ECL):
  - Stage 1 (Performing): 12-Month ECL = EAD * PD_12m * LGD
  - Stage 2 (Significant Increase in Credit Risk / SICR): Lifetime ECL
      Lifetime ECL ≈ EAD * min(1.0, PD_12m * Tenor) * LGD
    Switching from 12-month to lifetime ECL creates the "staging cliff"—where loan-loss
    provisions jump by 3x–5x for affected loans.
  - Stage 3 (Credit Impaired / Default): ECL = EAD * LGD

Capital impact translates stressed P&L into regulatory Tier 1 capital and CET1 ratio:
  CET1 Ratio = (Tier 1 Capital - Total Stress Loss) / Stressed RWA

Reverse stress testing solves via bisection for the minimum shock multiplier on a
scenario that breaches the regulatory CET1 floor (8.0%) or an internal loss limit.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from sentinel.stress.portfolio import WholesalePortfolio

SYNTHETIC_TIER1_CAPITAL_USD = 85_000_000.0  # Synthetic capital base for $610M book
REGULATORY_MIN_CET1_RATIO = 0.080             # 8.0% Basel III minimum + capital buffer
DEFAULT_LOAN_TENOR_YEARS = 3.5

# Standardized Approach Basel risk weights by credit rating
RISK_WEIGHT_BY_RATING: Dict[str, float] = {
    "AAA": 0.20,
    "AA": 0.20,
    "A": 0.50,
    "BBB": 1.00,
    "BB": 1.50,
    "B": 1.50,
    "CCC": 1.50,
    "DEFAULT": 1.50,
}


def get_risk_weight(rating: str) -> float:
    r = rating.strip().upper()
    for key, weight in RISK_WEIGHT_BY_RATING.items():
        if r.startswith(key):
            return weight
    return 1.00


@dataclass
class StagingMigration:
    """Details of a loan migrating from Stage 1 to Stage 2 or 3."""

    position_id: str
    counterparty_name: str
    entity_id: str
    ead_usd: float
    rating: str
    baseline_pd: float
    stressed_pd: float
    baseline_ecl_usd: float
    lifetime_ecl_usd: float
    staging_cliff_jump_usd: float
    jump_multiple: float
    from_stage: int
    to_stage: int
    trigger_reason: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "position_id": self.position_id,
            "counterparty_name": self.counterparty_name,
            "entity_id": self.entity_id,
            "ead_usd": round(self.ead_usd, 2),
            "rating": self.rating,
            "baseline_pd": round(self.baseline_pd, 4),
            "stressed_pd": round(self.stressed_pd, 4),
            "baseline_ecl_usd": round(self.baseline_ecl_usd, 2),
            "lifetime_ecl_usd": round(self.lifetime_ecl_usd, 2),
            "staging_cliff_jump_usd": round(self.staging_cliff_jump_usd, 2),
            "jump_multiple": round(self.jump_multiple, 2),
            "from_stage": self.from_stage,
            "to_stage": self.to_stage,
            "trigger_reason": self.trigger_reason,
        }


@dataclass
class IFRS9StagingReport:
    """Breakdown of loan portfolio across IFRS 9 stages."""

    stage_1_exposure_usd: float
    stage_1_ecl_usd: float
    stage_1_count: int

    stage_2_exposure_usd: float
    stage_2_ecl_usd: float
    stage_2_count: int

    stage_3_exposure_usd: float
    stage_3_ecl_usd: float
    stage_3_count: int

    total_baseline_ecl_usd: float
    total_stressed_ecl_usd: float
    staging_cliff_total_jump_usd: float
    migrations: List[StagingMigration] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        total_loans = self.stage_1_count + self.stage_2_count + self.stage_3_count
        return {
            "summary": {
                "total_loans": total_loans,
                "stage1_count": self.stage_1_count,
                "stage2_count": self.stage_2_count,
                "stage3_count": self.stage_3_count,
                "stage1_exposure_usd": round(self.stage_1_exposure_usd, 2),
                "stage1_ecl_usd": round(self.stage_1_ecl_usd, 2),
                "stage2_exposure_usd": round(self.stage_2_exposure_usd, 2),
                "stage2_ecl_usd": round(self.stage_2_ecl_usd, 2),
                "stage3_exposure_usd": round(self.stage_3_exposure_usd, 2),
                "stage3_ecl_usd": round(self.stage_3_ecl_usd, 2),
                "total_exposure_usd": round(self.stage_1_exposure_usd + self.stage_2_exposure_usd + self.stage_3_exposure_usd, 2),
                "total_baseline_ecl_usd": round(self.total_baseline_ecl_usd, 2),
                "total_stressed_ecl_usd": round(self.total_stressed_ecl_usd, 2),
                "total_incremental_ecl_usd": round(self.total_stressed_ecl_usd - self.total_baseline_ecl_usd, 2),
            },
            "stage_1": {
                "exposure_usd": round(self.stage_1_exposure_usd, 2),
                "ecl_usd": round(self.stage_1_ecl_usd, 2),
                "count": self.stage_1_count,
            },
            "stage_2": {
                "exposure_usd": round(self.stage_2_exposure_usd, 2),
                "ecl_usd": round(self.stage_2_ecl_usd, 2),
                "count": self.stage_2_count,
            },
            "stage_3": {
                "exposure_usd": round(self.stage_3_exposure_usd, 2),
                "ecl_usd": round(self.stage_3_ecl_usd, 2),
                "count": self.stage_3_count,
            },
            "total_baseline_ecl_usd": round(self.total_baseline_ecl_usd, 2),
            "total_stressed_ecl_usd": round(self.total_stressed_ecl_usd, 2),
            "staging_cliff_jump_usd": round(self.staging_cliff_total_jump_usd, 2),
            "staging_cliff_total_jump_usd": round(self.staging_cliff_total_jump_usd, 2),
            "migrated_loans_count": len(self.migrations),
            "migrations": [m.to_dict() for m in self.migrations],
        }


@dataclass
class CapitalImpactReport:
    """Regulatory capital and CET1 ratio impact before and after stress."""

    tier1_capital_usd: float
    baseline_rwa_usd: float
    stressed_rwa_usd: float
    baseline_cet1_ratio: float
    stressed_cet1_ratio: float
    cet1_delta_bps: int
    regulatory_min_cet1_ratio: float
    capital_surplus_usd: float
    breached_regulatory_floor: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tier1_capital_usd": round(self.tier1_capital_usd, 2),
            "baseline_rwa_usd": round(self.baseline_rwa_usd, 2),
            "stressed_rwa_usd": round(self.stressed_rwa_usd, 2),
            "baseline_cet1_ratio": round(self.baseline_cet1_ratio, 4),
            "stressed_cet1_ratio": round(self.stressed_cet1_ratio, 4),
            "cet1_delta_bps": self.cet1_delta_bps,
            "regulatory_min_cet1_ratio": round(self.regulatory_min_cet1_ratio, 4),
            "capital_surplus_usd": round(self.capital_surplus_usd, 2),
            "breached_regulatory_floor": self.breached_regulatory_floor,
        }


class StagingAndCapitalEngine:
    """Evaluates IFRS 9 staging, capital impact, and reverse stress testing."""

    def __init__(
        self,
        portfolio: WholesalePortfolio,
        tier1_capital_usd: float = SYNTHETIC_TIER1_CAPITAL_USD,
    ) -> None:
        self.portfolio = portfolio
        self.tier1_capital_usd = tier1_capital_usd

    def compute_baseline_rwa(self) -> float:
        """Compute Standardized Approach RWA for all portfolio assets."""
        rwa = 0.0
        for loan in self.portfolio.loans:
            rwa += loan.ead * get_risk_weight(loan.rating)
        for b in self.portfolio.bonds:
            rwa += b.market_value * get_risk_weight(b.rating)
        for eq in self.portfolio.equities:
            rwa += eq.market_value * 1.00  # 100% equity weight
        for c in self.portfolio.cash:
            rwa += c.market_value * 0.00        # 0% cash weight
        return rwa

    def evaluate_staging(
        self,
        stressed_pds: Optional[Dict[str, float]] = None,
        sicr_pd_multiplier: float = 3.0,
    ) -> IFRS9StagingReport:
        """Calculate IFRS 9 3-stage ECL and detect SICR staging cliff migrations."""
        stressed_pds = stressed_pds or {}

        s1_exp = s1_ecl = s1_cnt = 0.0
        s2_exp = s2_ecl = s2_cnt = 0.0
        s3_exp = s3_ecl = s3_cnt = 0.0
        tot_base_ecl = 0.0
        migrations: List[StagingMigration] = []

        for loan in self.portfolio.loans:
            base_pd = loan.baseline_pd
            stress_pd = stressed_pds.get(loan.position_id, base_pd)
            ead = loan.ead
            lgd = loan.lgd

            base_ecl = ead * base_pd * lgd
            tot_base_ecl += base_ecl

            # Stage classification
            if stress_pd >= 0.20:
                # Stage 3: Credit impaired
                s3_exp += ead
                ecl = ead * lgd
                s3_ecl += ecl
                s3_cnt += 1
                if base_pd < 0.20:
                    migrations.append(
                        StagingMigration(
                            position_id=loan.position_id,
                            counterparty_name=loan.counterparty_name,
                            entity_id=loan.entity_id,
                            ead_usd=ead,
                            rating=loan.rating,
                            baseline_pd=base_pd,
                            stressed_pd=stress_pd,
                            baseline_ecl_usd=base_ecl,
                            lifetime_ecl_usd=ecl,
                            staging_cliff_jump_usd=ecl - base_ecl,
                            jump_multiple=ecl / max(1.0, base_ecl),
                            from_stage=1,
                            to_stage=3,
                            trigger_reason="Default / Impairment threshold breached (PD >= 20%)",
                        )
                    )
            elif stress_pd >= base_pd * sicr_pd_multiplier and stress_pd > 0.01:
                # Stage 2: SICR Trigger -> Switch to Lifetime ECL
                s2_exp += ead
                lifetime_pd = min(1.0, stress_pd * DEFAULT_LOAN_TENOR_YEARS)
                ecl = ead * lifetime_pd * lgd
                s2_ecl += ecl
                s2_cnt += 1
                migrations.append(
                    StagingMigration(
                        position_id=loan.position_id,
                        counterparty_name=loan.counterparty_name,
                        entity_id=loan.entity_id,
                        ead_usd=ead,
                        rating=loan.rating,
                        baseline_pd=base_pd,
                        stressed_pd=stress_pd,
                        baseline_ecl_usd=base_ecl,
                        lifetime_ecl_usd=ecl,
                        staging_cliff_jump_usd=ecl - base_ecl,
                        jump_multiple=ecl / max(1.0, base_ecl),
                        from_stage=1,
                        to_stage=2,
                        trigger_reason=f"Significant Increase in Credit Risk (PD surged {stress_pd/base_pd:.1f}x vs origination)",
                    )
                )
            else:
                # Stage 1: Performing -> 12-Month ECL
                s1_exp += ead
                ecl = ead * stress_pd * lgd
                s1_ecl += ecl
                s1_cnt += 1

        tot_stressed_ecl = s1_ecl + s2_ecl + s3_ecl
        staging_cliff_jump = sum(m.staging_cliff_jump_usd for m in migrations)

        return IFRS9StagingReport(
            stage_1_exposure_usd=s1_exp,
            stage_1_ecl_usd=s1_ecl,
            stage_1_count=int(s1_cnt),
            stage_2_exposure_usd=s2_exp,
            stage_2_ecl_usd=s2_ecl,
            stage_2_count=int(s2_cnt),
            stage_3_exposure_usd=s3_exp,
            stage_3_ecl_usd=s3_ecl,
            stage_3_count=int(s3_cnt),
            total_baseline_ecl_usd=tot_base_ecl,
            total_stressed_ecl_usd=tot_stressed_ecl,
            staging_cliff_total_jump_usd=staging_cliff_jump,
            migrations=migrations,
        )

    def compute_capital_impact(
        self,
        total_pnl_usd: float,
        staging_report: Optional[IFRS9StagingReport] = None,
    ) -> CapitalImpactReport:
        """Compute CET1 capital ratio and basis point hit resulting from stress loss."""
        base_rwa = self.compute_baseline_rwa()

        # If staging cliff jumped, incremental provisions also reduce available Tier 1 capital
        additional_provision = (
            staging_report.staging_cliff_total_jump_usd if staging_report else 0.0
        )
        total_loss = abs(total_pnl_usd) + additional_provision

        # Stressed RWA: scales with loss/downgrades only when loss > 0
        rwa_stress_factor = (
            1.0 + (0.05 * min(1.0, total_loss / (0.10 * self.tier1_capital_usd)))
            if total_loss > 0.0
            else 1.0
        )
        stressed_rwa = base_rwa * rwa_stress_factor

        base_cet1 = self.tier1_capital_usd / base_rwa
        stressed_tier1 = max(0.0, self.tier1_capital_usd - total_loss)
        stressed_cet1 = stressed_tier1 / stressed_rwa

        delta_bps = int(round((stressed_cet1 - base_cet1) * 10_000))
        capital_surplus = stressed_tier1 - (REGULATORY_MIN_CET1_RATIO * stressed_rwa)

        return CapitalImpactReport(
            tier1_capital_usd=self.tier1_capital_usd,
            baseline_rwa_usd=base_rwa,
            stressed_rwa_usd=stressed_rwa,
            baseline_cet1_ratio=base_cet1,
            stressed_cet1_ratio=stressed_cet1,
            cet1_delta_bps=delta_bps,
            regulatory_min_cet1_ratio=REGULATORY_MIN_CET1_RATIO,
            capital_surplus_usd=capital_surplus,
            breached_regulatory_floor=stressed_cet1 < REGULATORY_MIN_CET1_RATIO,
        )

    def reverse_stress_test(
        self,
        engine: Any,
        scenario_id: str,
        target_cet1_floor: float = REGULATORY_MIN_CET1_RATIO,
        max_loss_usd: Optional[float] = None,
        max_multiplier: float = 10.0,
        tolerance: float = 0.01,
        max_iter: int = 20,
    ) -> Dict[str, Any]:
        """Solve via bisection for the smallest shock multiplier lambda that causes capital breach."""
        low = 0.1
        high = max_multiplier
        best_multiplier = high

        def evaluate_multiplier(mult: float) -> Tuple[bool, float, float]:
            # Scale shocks by mult and run scenario
            r = engine.run_scenario(scenario_id, scale_factor=mult)
            pnl = r.total_pnl_usd
            cap = self.compute_capital_impact(pnl)
            breached = cap.stressed_cet1_ratio <= target_cet1_floor or (
                max_loss_usd is not None and abs(pnl) >= max_loss_usd
            )
            return breached, pnl, cap.stressed_cet1_ratio

        # Check if high multiplier breaches
        breached_high, _, _ = evaluate_multiplier(high)
        if not breached_high:
            return {
                "scenario_id": scenario_id,
                "breach_found": False,
                "multiplier": high,
                "note": f"Even at {high}x shock multiplier, CET1 does not breach {target_cet1_floor:.1%}",
            }

        # Bisection search
        for i in range(max_iter):
            mid = (low + high) / 2.0
            breached, pnl, cet1 = evaluate_multiplier(mid)
            if breached:
                best_multiplier = mid
                high = mid
            else:
                low = mid
            if (high - low) < tolerance:
                break

        # Final evaluation at best_multiplier
        final_res = engine.run_scenario(scenario_id, scale_factor=best_multiplier)
        final_cap = self.compute_capital_impact(final_res.total_pnl_usd)

        return {
            "scenario_id": scenario_id,
            "breach_found": True,
            "breach_multiplier": round(best_multiplier, 3),
            "breach_loss_usd": round(abs(final_res.total_pnl_usd), 2),
            "breach_cet1_ratio": round(final_cap.stressed_cet1_ratio, 4),
            "target_cet1_floor": round(target_cet1_floor, 4),
            "capital_consumed_usd": round(self.tier1_capital_usd - final_cap.capital_surplus_usd, 2),
            "iterations": i + 1,
            "top_drivers": final_res.attribution.get("top_positions", [])[:3] if final_res.attribution else [],
        }
