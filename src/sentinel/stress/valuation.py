"""Multi-asset wholesale banking valuation engine conforming to PRD Section 9.4 and 13.3."""

import uuid
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from sentinel.contracts.stress import (
    AssetClass,
    AssetClassStressSummary,
    BondPosition,
    CashPosition,
    LoanPosition,
    PositionStressDelta,
    SectorStressSummary,
    SleeveStressSummary,
    StressRunResult,
    SwapPosition,
)
from sentinel.stress.contagion import ContagionGraph
from sentinel.stress.portfolio import WholesalePortfolio
from sentinel.stress.shocks import ScaledShock


class ValuationEngine:
    """Executes multi-asset revaluation under scaled shocks with strict unit segregation."""

    MODEL_VERSION = "v1.0.0-multiasset"

    def __init__(
        self,
        portfolio: WholesalePortfolio,
        contagion_graph: Optional[ContagionGraph] = None,
    ) -> None:
        self.portfolio = portfolio
        self.contagion_graph = contagion_graph or ContagionGraph()

    def _is_position_in_scope(
        self,
        position_entity_id: str,
        position_sector: str,
        asset_class: AssetClass,
        shock: ScaledShock,
    ) -> bool:
        # Swaps are pure rates instruments (entity_id="MACRO");
        # they only respond to benchmark yield shifts
        if asset_class == AssetClass.SWAP:
            return abs(shock.benchmark_yield_shift_bps) > 1e-6

        # Cash never receives credit or duration shocks
        if asset_class == AssetClass.CASH:
            return False

        if shock.target_scope == "systemic":
            return True

        if shock.target_scope == "sector":
            if not shock.target_entity:
                return True
            return shock.target_entity.lower() in position_sector.lower()

        if shock.target_scope == "entity":
            if not shock.target_entity:
                return False
            return position_entity_id.upper() == shock.target_entity.upper()

        return False

    def value_bond(
        self,
        bond: BondPosition,
        shock: ScaledShock,
        transmission_factor: float = 1.0,
        is_contagion: bool = False,
        contagion_hops: int = 0,
        contagion_source: Optional[str] = None,
    ) -> PositionStressDelta:
        """Bond valuation: delta = -modified_duration * value * (yield_shift + spread_shift)."""

        in_scope = is_contagion or self._is_position_in_scope(
            bond.entity_id, bond.sector, AssetClass.BOND, shock
        )

        baseline_val = bond.market_value

        if in_scope:
            effective_spread_shift = shock.bond_spread_shift_bps * transmission_factor
            effective_yield_shift = shock.benchmark_yield_shift_bps * (
                transmission_factor if is_contagion else 1.0
            )
            yield_shift = effective_yield_shift / 10000.0
            spread_shift = effective_spread_shift / 10000.0
            total_shift = yield_shift + spread_shift
            delta_val = -bond.modified_duration * baseline_val * total_shift
            stressed_val = max(0.0, baseline_val + delta_val)
            # Recompute exact delta if clamped at zero
            delta_val = stressed_val - baseline_val
            if is_contagion:
                shock_summary = (
                    f"Contagion from {contagion_source} (hop {contagion_hops}, "
                    f"factor {transmission_factor:.2f}): Spread {effective_spread_shift:+.1f} bps"
                )
            else:
                shock_summary = (
                    f"Spread {shock.bond_spread_shift_bps:+.1f} bps, "
                    f"Yield {shock.benchmark_yield_shift_bps:+.1f} bps"
                )
        else:
            delta_val = 0.0
            stressed_val = baseline_val
            shock_summary = "Unimpacted"

        pct_change = (delta_val / baseline_val) if baseline_val > 0 else 0.0

        return PositionStressDelta(
            position_id=bond.position_id,
            asset_class=AssetClass.BOND,
            entity_id=bond.entity_id,
            counterparty_name=bond.counterparty_name,
            sector=bond.sector,
            baseline_value_usd=round(baseline_val, 2),
            stressed_value_usd=round(stressed_val, 2),
            pnl_usd=round(delta_val, 2),
            pct_change=round(pct_change, 6),
            market_risk_pnl_usd=round(delta_val, 2),
            applied_shock_summary=shock_summary,
            is_contagion=is_contagion,
            contagion_hops=contagion_hops,
            contagion_source=contagion_source,
            transmission_factor=round(transmission_factor, 4),
            sleeve=bond.sleeve,
        )

    def value_loan(
        self,
        loan: LoanPosition,
        shock: ScaledShock,
        transmission_factor: float = 1.0,
        is_contagion: bool = False,
        contagion_hops: int = 0,
        contagion_source: Optional[str] = None,
    ) -> PositionStressDelta:
        """Loan valuation: Incremental ECL = EAD * (stressed_PD - baseline_PD) * LGD."""
        in_scope = is_contagion or self._is_position_in_scope(
            loan.entity_id, loan.sector, AssetClass.LOAN, shock
        )

        baseline_val = loan.market_value
        baseline_ecl = loan.ead * loan.baseline_pd * loan.lgd

        if in_scope:
            effective_pd_inc = shock.loan_pd_increment * transmission_factor
            effective_lgd_inc = shock.lgd_increment * transmission_factor
            stressed_pd = min(1.0, max(0.0, loan.baseline_pd + effective_pd_inc))
            stressed_lgd = min(1.0, max(0.0, loan.lgd + effective_lgd_inc))
            stressed_ecl = loan.ead * stressed_pd * stressed_lgd
            incremental_ecl = stressed_ecl - baseline_ecl

            # Loan carrying value is marked down by incremental credit loss
            delta_val = -incremental_ecl
            stressed_val = max(0.0, baseline_val + delta_val)
            delta_val = stressed_val - baseline_val
            if is_contagion:
                shock_summary = (
                    f"Contagion from {contagion_source} (hop {contagion_hops}, "
                    f"factor {transmission_factor:.2f}): PD {effective_pd_inc * 100:+.2f} pp"
                )
            else:
                shock_summary = (
                    f"PD {shock.loan_pd_increment * 100:+.2f} pp, "
                    f"LGD {shock.lgd_increment * 100:+.2f} pp"
                )
        else:
            stressed_ecl = baseline_ecl
            incremental_ecl = 0.0
            delta_val = 0.0
            stressed_val = baseline_val
            shock_summary = "Unimpacted"

        pct_change = (delta_val / baseline_val) if baseline_val > 0 else 0.0

        return PositionStressDelta(
            position_id=loan.position_id,
            asset_class=AssetClass.LOAN,
            entity_id=loan.entity_id,
            counterparty_name=loan.counterparty_name,
            sector=loan.sector,
            baseline_value_usd=round(baseline_val, 2),
            stressed_value_usd=round(stressed_val, 2),
            pnl_usd=round(delta_val, 2),
            pct_change=round(pct_change, 6),
            ecl_baseline_usd=round(baseline_ecl, 2),
            ecl_stressed_usd=round(stressed_ecl, 2),
            incremental_ecl_usd=round(incremental_ecl, 2),
            applied_shock_summary=shock_summary,
            is_contagion=is_contagion,
            contagion_hops=contagion_hops,
            contagion_source=contagion_source,
            transmission_factor=round(transmission_factor, 4),
            sleeve=loan.sleeve,
        )

    def value_swap(self, swap: SwapPosition, shock: ScaledShock) -> PositionStressDelta:
        """Swap valuation: delta_value = signed_DV01 * yield_shift_bps."""
        in_scope = self._is_position_in_scope(swap.entity_id, swap.sector, AssetClass.SWAP, shock)

        baseline_val = swap.market_value

        if in_scope:
            # Pay-fixed has negative signed_dv01, so yield increase (+bps) produces negative delta
            delta_val = swap.signed_dv01 * shock.benchmark_yield_shift_bps
            stressed_val = baseline_val + delta_val
            shock_summary = (
                f"Yield shift {shock.benchmark_yield_shift_bps:+.1f} bps "
                f"(DV01: {swap.signed_dv01:,.0f})"
            )
        else:
            delta_val = 0.0
            stressed_val = baseline_val
            shock_summary = "Unimpacted"

        # Percentage change uses notional as reference denominator if baseline MTM is near zero
        pct_change = (delta_val / swap.notional) if swap.notional > 0 else 0.0

        return PositionStressDelta(
            position_id=swap.position_id,
            asset_class=AssetClass.SWAP,
            entity_id=swap.entity_id,
            counterparty_name=swap.counterparty_name,
            sector=swap.sector,
            baseline_value_usd=round(baseline_val, 2),
            stressed_value_usd=round(stressed_val, 2),
            pnl_usd=round(delta_val, 2),
            pct_change=round(pct_change, 6),
            market_risk_pnl_usd=round(delta_val, 2),
            applied_shock_summary=shock_summary,
            sleeve=swap.sleeve,
        )

    def value_cash(self, cash: CashPosition, shock: ScaledShock) -> PositionStressDelta:
        """Cash valuation: zero market or credit delta."""
        baseline_val = cash.market_value
        return PositionStressDelta(
            position_id=cash.position_id,
            asset_class=AssetClass.CASH,
            entity_id=cash.entity_id,
            counterparty_name=cash.counterparty_name,
            sector=cash.sector,
            baseline_value_usd=round(baseline_val, 2),
            stressed_value_usd=round(baseline_val, 2),
            pnl_usd=0.0,
            pct_change=0.0,
            applied_shock_summary="Unimpacted (Risk-free cash)",
            sleeve=cash.sleeve,
        )

    def run_stress_test(
        self,
        shock: ScaledShock,
        run_id: str = "stress-run-001",
        trigger_type: str = "EVENT_TRIGGERED",
        trigger_signal_id: Optional[str] = None,
        event_class: str = "CREDIT",
        impact_score: int = 8,
        enable_contagion: bool = False,
        max_hops: int = 2,
        hop_decay: float = 0.60,
    ) -> StressRunResult:
        """Revalue entire portfolio, compute asset/sector breakdowns, and enforce reconciliation."""
        stress_id = f"stress-{uuid.uuid4().hex[:12]}"
        executed_at = datetime.utcnow().isoformat()

        position_deltas: List[PositionStressDelta] = []

        # Multi-hop contagion targets
        contagion_targets: Dict[str, Tuple[float, int]] = {}
        if (
            enable_contagion
            and shock.target_scope == "entity"
            and shock.target_entity
            and self.contagion_graph
        ):
            contagion_targets = self.contagion_graph.get_contagion_targets(
                shock.target_entity, max_hops=max_hops, hop_decay=hop_decay
            )

        # Value each asset class independently
        for loan in self.portfolio.loans:
            ent = loan.entity_id.upper()
            if ent in contagion_targets and ent != (shock.target_entity or "").upper():
                factor, hops = contagion_targets[ent]
                position_deltas.append(
                    self.value_loan(
                        loan,
                        shock,
                        transmission_factor=factor,
                        is_contagion=True,
                        contagion_hops=hops,
                        contagion_source=shock.target_entity,
                    )
                )
            else:
                position_deltas.append(self.value_loan(loan, shock))

        for bond in self.portfolio.bonds:
            ent = bond.entity_id.upper()
            if ent in contagion_targets and ent != (shock.target_entity or "").upper():
                factor, hops = contagion_targets[ent]
                position_deltas.append(
                    self.value_bond(
                        bond,
                        shock,
                        transmission_factor=factor,
                        is_contagion=True,
                        contagion_hops=hops,
                        contagion_source=shock.target_entity,
                    )
                )
            else:
                position_deltas.append(self.value_bond(bond, shock))

        for swap in self.portfolio.swaps:
            position_deltas.append(self.value_swap(swap, shock))

        for cash in self.portfolio.cash:
            position_deltas.append(self.value_cash(cash, shock))

        # Financial totals: funded book value (loans + bonds + cash)
        # Note: Swap MTM is segregated from funded balance sheet, but included in P&L
        baseline_funded = self.portfolio.total_funded_exposure
        total_pnl = sum(p.pnl_usd for p in position_deltas)
        stressed_funded = baseline_funded + total_pnl

        credit_ecl_change = sum(p.incremental_ecl_usd for p in position_deltas)
        market_mtm_change = sum(p.market_risk_pnl_usd for p in position_deltas)

        contagion_pnl = sum(p.pnl_usd for p in position_deltas if p.is_contagion)
        contagion_count = sum(1 for p in position_deltas if p.is_contagion)

        # Asset class aggregations
        asset_class_groups: Dict[AssetClass, List[PositionStressDelta]] = defaultdict(list)
        for p in position_deltas:
            asset_class_groups[p.asset_class].append(p)

        asset_class_breakdown: List[AssetClassStressSummary] = []
        for ac in [AssetClass.LOAN, AssetClass.BOND, AssetClass.SWAP, AssetClass.CASH]:
            positions = asset_class_groups[ac]
            base_v = sum(p.baseline_value_usd for p in positions)
            stress_v = sum(p.stressed_value_usd for p in positions)
            pnl_v = sum(p.pnl_usd for p in positions)
            ecl_v = sum(p.incremental_ecl_usd for p in positions)
            mtm_v = sum(p.market_risk_pnl_usd for p in positions)

            denom = base_v
            gross_notional = 0.0
            if ac == AssetClass.SWAP:
                gross_notional = self.portfolio.total_derivative_notional
                denom = gross_notional if gross_notional > 0 else 1.0

            pct_v = (pnl_v / denom) if denom > 0 else 0.0

            asset_class_breakdown.append(
                AssetClassStressSummary(
                    asset_class=ac,
                    baseline_value_usd=round(base_v, 2),
                    stressed_value_usd=round(stress_v, 2),
                    total_pnl_usd=round(pnl_v, 2),
                    pct_change=round(pct_v, 6),
                    credit_ecl_delta_usd=round(ecl_v, 2),
                    mark_to_market_pnl_usd=round(mtm_v, 2),
                    derivative_gross_notional_usd=round(gross_notional, 2),
                )
            )

        # Sector aggregations
        sector_groups: Dict[str, List[PositionStressDelta]] = defaultdict(list)
        for p in position_deltas:
            sector_groups[p.sector].append(p)

        sector_breakdown: List[SectorStressSummary] = []
        for sector_name, positions in sorted(sector_groups.items()):
            base_v = sum(p.baseline_value_usd for p in positions)
            stress_v = sum(p.stressed_value_usd for p in positions)
            pnl_v = sum(p.pnl_usd for p in positions)
            pct_v = (pnl_v / base_v) if base_v > 0 else 0.0

            sector_breakdown.append(
                SectorStressSummary(
                    sector=sector_name,
                    baseline_value_usd=round(base_v, 2),
                    stressed_value_usd=round(stress_v, 2),
                    total_pnl_usd=round(pnl_v, 2),
                    pct_change=round(pct_v, 6),
                )
            )

        # PRD Section 13.3 Invariants Reconciliation Check:
        # 1. sum of position PnL equals total_pnl
        # 2. for each position: baseline + pnl == stressed
        sum_position_pnl = sum(p.pnl_usd for p in position_deltas)
        pnl_reconciliation = abs(sum_position_pnl - total_pnl) < 0.01

        positions_reconciled = all(
            abs((p.baseline_value_usd + p.pnl_usd) - p.stressed_value_usd) < 0.02
            for p in position_deltas
        )

        reconciliation_passed = pnl_reconciliation and positions_reconciled

        total_pnl_pct = (total_pnl / baseline_funded) if baseline_funded > 0 else 0.0

        # PRD 9.1: funded balance-sheet value vs derivative MTM, and per-sleeve subtotals
        derivative_mtm = sum(p.pnl_usd for p in position_deltas if p.asset_class == AssetClass.SWAP)
        funded_pnl = total_pnl - derivative_mtm
        sleeve_breakdown = []
        for sleeve in sorted({p.sleeve for p in position_deltas}):
            funded = [
                p
                for p in position_deltas
                if p.sleeve == sleeve and p.asset_class != AssetClass.SWAP
            ]
            base_v = sum(p.baseline_value_usd for p in funded)
            pnl_v = sum(p.pnl_usd for p in funded)
            sleeve_breakdown.append(
                SleeveStressSummary(
                    sleeve=sleeve,
                    baseline_value_usd=round(base_v, 2),
                    stressed_value_usd=round(base_v + pnl_v, 2),
                    total_pnl_usd=round(pnl_v, 2),
                    pct_change=round(pnl_v / base_v, 6) if base_v > 0 else 0.0,
                )
            )

        shock_params_dict = {
            "bond_spread_shift_bps": shock.bond_spread_shift_bps,
            "loan_pd_increment": shock.loan_pd_increment,
            "lgd_increment": shock.lgd_increment,
            "benchmark_yield_shift_bps": shock.benchmark_yield_shift_bps,
            "scale_multiplier": shock.scale_multiplier,
            "target_entity": shock.target_entity,
            "target_scope": shock.target_scope,
        }

        return StressRunResult(
            stress_id=stress_id,
            run_id=run_id,
            executed_at=executed_at,
            trigger_type=trigger_type,
            trigger_signal_id=trigger_signal_id,
            event_class=event_class,
            impact_score=impact_score,
            target_entity=shock.target_entity,
            target_scope=shock.target_scope,
            shock_parameters=shock_params_dict,
            model_version=self.MODEL_VERSION,
            baseline_total_book_value_usd=round(baseline_funded, 2),
            stressed_total_book_value_usd=round(stressed_funded, 2),
            total_pnl_usd=round(total_pnl, 2),
            total_pnl_pct=round(total_pnl_pct, 6),
            credit_ecl_change_usd=round(credit_ecl_change, 2),
            market_mtm_change_usd=round(market_mtm_change, 2),
            contagion_pnl_usd=round(contagion_pnl, 2),
            contagion_positions_count=contagion_count,
            asset_class_breakdown=asset_class_breakdown,
            sector_breakdown=sector_breakdown,
            position_deltas=position_deltas,
            reconciliation_passed=reconciliation_passed,
            sleeve_breakdown=sleeve_breakdown,
            funded_baseline_value_usd=round(baseline_funded, 2),
            funded_stressed_value_usd=round(baseline_funded + funded_pnl, 2),
            derivative_mtm_change_usd=round(derivative_mtm, 2),
        )
