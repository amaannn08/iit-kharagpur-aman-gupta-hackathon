"""Event-triggered stress testing: trigger rules, shock selection and runs."""

import json
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union

from sentinel.config import settings
from sentinel.contracts.signals import RiskSignal
from sentinel.contracts.stress import StressRunResult
from sentinel.nlp.roles import get_ma_financing_multiplier
from sentinel.nlp.sentiment import macro_polarity
from sentinel.stress.contagion import ContagionGraph
from sentinel.stress.portfolio import WholesalePortfolio
from sentinel.stress.sectors import normalize_sector
from sentinel.stress.shocks import (
    DEFAULT_SHOCK_CATALOG,
    ScaledShock,
    build_scaled_shock,
    shock_from_scenario,
)
from sentinel.stress.valuation import ValuationEngine


class StressEngine:
    """Manages baseline wholesale portfolio and triggers event-driven stress simulations."""

    SUPPORTED_EVENT_CLASSES = set(DEFAULT_SHOCK_CATALOG.keys())

    def __init__(
        self,
        portfolio_path: Optional[Union[str, Path]] = None,
        confidence_threshold: Optional[float] = None,
        impact_threshold: Optional[int] = None,
    ) -> None:
        self.profiles: Dict[str, WholesalePortfolio] = {}
        self.valuation_engines: Dict[str, ValuationEngine] = {}

        if portfolio_path is not None:  # a single explicit file (tests, sandbox)
            custom_p = WholesalePortfolio.load_from_json(portfolio_path)
            self.portfolio = custom_p
            self.valuation_engine = ValuationEngine(self.portfolio)
            self.profiles["custom"] = custom_p
            self.valuation_engines["custom"] = self.valuation_engine
        else:
            for prof_name, rel_paths in settings.portfolio_profiles.items():
                files = [settings.data_dir / f for f in rel_paths]
                existing = [f for f in files if f.exists()]
                if existing:
                    prof_port = WholesalePortfolio.load_many(existing)
                    self.profiles[prof_name] = prof_port
                    graph_file = (
                        settings.data_dir / "graph_edges_demo.csv"
                        if prof_name == "synthetic_demo"
                        else settings.data_dir / "graph_edges.csv"
                    )
                    c_graph = ContagionGraph(graph_file) if graph_file.exists() else None
                    self.valuation_engines[prof_name] = ValuationEngine(
                        prof_port, contagion_graph=c_graph
                    )

            default_prof = settings.default_portfolio_profile
            self.portfolio = self.profiles.get(default_prof) or next(iter(self.profiles.values()))
            self.valuation_engine = self.valuation_engines.get(default_prof) or next(
                iter(self.valuation_engines.values())
            )

        self.confidence_threshold = (
            confidence_threshold
            if confidence_threshold is not None
            else settings.action_confidence_threshold
        )
        self.impact_threshold = (
            impact_threshold if impact_threshold is not None else settings.action_impact_threshold
        )
        self.acted_signal_ids: Set[str] = set()

    def get_valuation_engine(self, profile: Optional[str] = None) -> Tuple[ValuationEngine, str]:
        prof_name = profile or settings.default_portfolio_profile
        if prof_name in self.valuation_engines:
            return self.valuation_engines[prof_name], prof_name
        return self.valuation_engine, prof_name

    def _macro_is_easing(self, signal: RiskSignal) -> Optional[bool]:
        """True = easing/benign, False = tightening/adverse, None = no direction (skip)."""
        direction = signal.event.macro_direction or "none"
        if direction in ("easing", "tightening"):
            return direction == "easing"
        pol = macro_polarity(signal.text_excerpt or "")
        if pol is not None:
            return pol[0] > 0
        return None

    def should_trigger(self, signal: RiskSignal) -> bool:
        """Evaluate if an incoming RiskSignal meets criteria for automated stress testing."""

        if not signal.eligible_for_action:
            return False

        if signal.event.label.upper() not in self.SUPPORTED_EVENT_CLASSES:
            return False

        if signal.impact.score <= self.impact_threshold:
            return False

        if signal.event.confidence < self.confidence_threshold:
            return False

        if signal.signal_id in self.acted_signal_ids:
            return False

        if signal.event.label.upper() == "MACRO" and self._macro_is_easing(signal) is None:
            return False  # direction unknown: do not guess

        if signal.event.label.upper() == "M_AND_A" and signal.entity.role != "acquirer":
            return False  # only acquirer is stressed; target/undetermined skipped

        return True

    def trigger_from_signal(
        self, signal: RiskSignal, profile: Optional[str] = None
    ) -> Optional[StressRunResult]:
        """Automatically execute stress test against baseline portfolio for eligible signal."""
        if not self.should_trigger(signal):
            return None

        event_class = signal.event.label.upper()
        impact = signal.impact.score

        # Scope assignment:
        # Systemic macro and geopolitical events shock the entire benchmark curve
        # or broad market. Sector events shock sector-specific loans and bonds.
        # Single entity shocks require a valid ticker.
        if (
            event_class in {"MACRO", "GEOPOLITICAL"}
            or signal.entity.scope == "macro"
        ):
            scope = "systemic"
            target_entity = None
            target_sector = None
        elif signal.entity.scope == "sector":
            scope = "sector"
            target_entity = None
            target_sector = normalize_sector(signal.entity.sector or signal.entity.name)
        elif not signal.entity.ticker:
            scope = "systemic"
            target_entity = None
            target_sector = None
        else:
            scope = "entity"
            # Always use ticker symbol (e.g. 'APEX'), never company name string
            target_entity = signal.entity.ticker
            target_sector = normalize_sector(signal.entity.sector)

        is_easing = bool(self._macro_is_easing(signal)) if event_class == "MACRO" else False

        financing_multiplier = (
            get_ma_financing_multiplier(signal.text_excerpt or "")
            if event_class == "M_AND_A"
            else 1.0
        )

        shock = build_scaled_shock(
            event_class=event_class,
            impact_score=impact,
            target_entity=target_entity,
            target_scope=scope,
            is_easing=is_easing,
            target_sector=target_sector,
            financing_multiplier=financing_multiplier,
        )

        enable_contagion = scope == "entity" and event_class in {"CREDIT", "SUPPLY_CHAIN"}

        val_engine, prof_name = self.get_valuation_engine(profile)
        result = val_engine.run_stress_test(
            shock=shock,
            run_id=signal.run_id,
            trigger_type="EVENT_TRIGGERED",
            trigger_signal_id=signal.signal_id,
            event_class=event_class,
            impact_score=impact,
            enable_contagion=enable_contagion,
        )
        result.portfolio_profile = prof_name

        self.acted_signal_ids.add(signal.signal_id)
        return self._mark_exposure(result)

    def run_manual_stress(
        self,
        event_class: str,
        impact_score: int,
        target_entity: Optional[str] = None,
        target_scope: str = "entity",
        is_easing: bool = False,
        enable_contagion: bool = False,
        run_id: str = "manual-run",
        target_sector: Optional[str] = None,
        profile: Optional[str] = None,
    ) -> StressRunResult:
        """Execute a user-triggered / sandbox stress simulation with custom shock parameters."""
        shock = build_scaled_shock(
            event_class=event_class,
            impact_score=impact_score,
            target_entity=target_entity,
            target_scope=target_scope,
            is_easing=is_easing,
            target_sector=target_sector,
        )

        val_engine, prof_name = self.get_valuation_engine(profile)
        result = val_engine.run_stress_test(
            shock=shock,
            run_id=run_id,
            trigger_type="USER_TRIGGERED",
            trigger_signal_id=None,
            event_class=event_class.upper(),
            impact_score=impact_score,
            enable_contagion=enable_contagion,
        )
        result.portfolio_profile = prof_name
        return self._mark_exposure(result)

    @staticmethod
    def _mark_exposure(result: StressRunResult) -> StressRunResult:
        """A trigger whose shock touches no position is reported as NO_EXPOSURE, not a $0 loss."""
        if all(abs(p.pnl_usd) < 0.005 for p in result.position_deltas):
            result.status = "NO_EXPOSURE"
        return result

    def list_scenarios(self) -> List[dict]:
        out = []
        for path in sorted((settings.data_dir / "scenarios").glob("*.json")):
            out.append(json.loads(path.read_text(encoding="utf-8")))
        return out

    def run_scenario(
        self,
        scenario_id: str,
        run_id: str = "scenario-run",
        profile: Optional[str] = None,
    ) -> StressRunResult:
        """Run a named scenario file (e.g. HIST-SVB_2023: the measured SVB-window market move)."""
        scenario = next((s for s in self.list_scenarios() if s["scenario_id"] == scenario_id), None)
        if scenario is None:
            raise KeyError(scenario_id)
        contagion = scenario.get("contagion", {})
        val_engine, prof_name = self.get_valuation_engine(profile)
        result = val_engine.run_stress_test(
            shock=shock_from_scenario(scenario),
            run_id=run_id,
            trigger_type="SCENARIO",
            event_class=scenario.get("event_class", "MACRO"),
            impact_score=int(scenario.get("trigger_impact_score", 8)),
            enable_contagion=bool(contagion.get("enabled")),
            max_hops=int(contagion.get("max_hops", 2) or 2),
            hop_decay=float(contagion.get("hop_decay", 0.6) or 0.6),
        )
        result.portfolio_profile = prof_name
        return self._mark_exposure(result)

    def run_custom_stress(
        self,
        equity_shock_pct: float = 0.0,
        benchmark_yield_shift_bps: float = 0.0,
        bond_spread_shift_bps: float = 0.0,
        loan_pd_increment: float = 0.0,
        lgd_increment: float = 0.0,
        run_id: str = "custom-run",
        pd_from_spread: bool = False,
        rating_tiered: bool = True,
        profile: Optional[str] = None,
    ) -> StressRunResult:
        """Explicit systemic shock set, e.g. the PS example: equities -10%, rates +200 bp."""
        shock = ScaledShock(
            bond_spread_shift_bps=bond_spread_shift_bps,
            loan_pd_increment=loan_pd_increment,
            lgd_increment=lgd_increment,
            benchmark_yield_shift_bps=benchmark_yield_shift_bps,
            scale_multiplier=1.0,
            target_entity=None,
            target_scope="systemic",
            equity_shock_pct=equity_shock_pct,
            catalog_entry="custom",
            pd_from_spread=pd_from_spread,
            rating_tiered=rating_tiered,
        )
        val_engine, prof_name = self.get_valuation_engine(profile)
        result = val_engine.run_stress_test(
            shock=shock, run_id=run_id, trigger_type="USER_TRIGGERED", event_class="CUSTOM"
        )
        result.portfolio_profile = prof_name
        return self._mark_exposure(result)

    def reset_triggers(self) -> None:
        """Reset deduplication cache of acted-upon signals."""
        self.acted_signal_ids.clear()
