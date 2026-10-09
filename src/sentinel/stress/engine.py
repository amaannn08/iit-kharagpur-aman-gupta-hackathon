"""Event-triggered stress testing orchestrator conforming to PRD Section 9.3."""

from pathlib import Path
from typing import Optional, Set, Union

from sentinel.config import settings
from sentinel.contracts.signals import RiskSignal
from sentinel.contracts.stress import StressRunResult
from sentinel.stress.portfolio import WholesalePortfolio
from sentinel.stress.shocks import DEFAULT_SHOCK_CATALOG, build_scaled_shock
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
        if portfolio_path is not None:  # a single explicit file (tests, sandbox)
            self.portfolio = WholesalePortfolio.load_from_json(portfolio_path)
        else:
            files = [settings.data_dir / f for f in settings.portfolio_files]
            self.portfolio = WholesalePortfolio.load_many([f for f in files if f.exists()])
        self.valuation_engine = ValuationEngine(self.portfolio)
        self.confidence_threshold = (
            confidence_threshold
            if confidence_threshold is not None
            else settings.action_confidence_threshold
        )
        self.impact_threshold = (
            impact_threshold if impact_threshold is not None else settings.action_impact_threshold
        )
        self.acted_signal_ids: Set[str] = set()

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

        return True

    def trigger_from_signal(self, signal: RiskSignal) -> Optional[StressRunResult]:
        """Automatically execute stress test against baseline portfolio for eligible signal."""
        if not self.should_trigger(signal):
            return None

        event_class = signal.event.label.upper()
        impact = signal.impact.score

        # Correct Scope assignment (conforming to PRD Section 9.3 & Bug B1 fix):
        # Systemic macro and geopolitical events must shock the entire benchmark curve
        # or broad market. Sector events shock sector-specific loans and bonds.
        # Single entity shocks require a valid ticker.
        if (
            event_class in {"MACRO", "GEOPOLITICAL"}
            or signal.entity.scope == "macro"
            or not signal.entity.ticker
        ):
            scope = "systemic"
            target_entity = None
        elif signal.entity.scope == "sector":
            scope = "sector"
            target_entity = signal.entity.name
        else:
            scope = "entity"
            # Always use ticker symbol (e.g. 'APEX'), never company name string
            target_entity = signal.entity.ticker

        # Easing detection for macro rate events (Bug B2 fix)
        is_easing = False
        if getattr(signal.event, "macro_direction", None) == "easing":
            is_easing = True
        else:
            evidence_text = " ".join(e.text for e in signal.evidence).lower()
            if any(
                w in evidence_text
                for w in (
                    "rate cut",
                    "cuts rate",
                    "cutting rate",
                    "easing",
                    "lower rate",
                    "lowers rate",
                )
            ):
                is_easing = True

        shock = build_scaled_shock(
            event_class=event_class,
            impact_score=impact,
            target_entity=target_entity,
            target_scope=scope,
            is_easing=is_easing,
        )

        enable_contagion = scope == "entity" and event_class in {"CREDIT", "SUPPLY_CHAIN"}

        result = self.valuation_engine.run_stress_test(
            shock=shock,
            run_id=signal.run_id,
            trigger_type="EVENT_TRIGGERED",
            trigger_signal_id=signal.signal_id,
            event_class=event_class,
            impact_score=impact,
            enable_contagion=enable_contagion,
        )

        self.acted_signal_ids.add(signal.signal_id)
        return result

    def run_manual_stress(
        self,
        event_class: str,
        impact_score: int,
        target_entity: Optional[str] = None,
        target_scope: str = "entity",
        is_easing: bool = False,
        enable_contagion: bool = False,
        run_id: str = "manual-run",
    ) -> StressRunResult:
        """Execute a user-triggered / sandbox stress simulation with custom shock parameters."""
        shock = build_scaled_shock(
            event_class=event_class,
            impact_score=impact_score,
            target_entity=target_entity,
            target_scope=target_scope,
            is_easing=is_easing,
        )

        return self.valuation_engine.run_stress_test(
            shock=shock,
            run_id=run_id,
            trigger_type="USER_TRIGGERED",
            trigger_signal_id=None,
            event_class=event_class.upper(),
            impact_score=impact_score,
            enable_contagion=enable_contagion,
        )

    def reset_triggers(self) -> None:
        """Reset deduplication cache of acted-upon signals."""
        self.acted_signal_ids.clear()
