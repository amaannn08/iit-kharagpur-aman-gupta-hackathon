"""Event-triggered stress testing orchestrator conforming to PRD Section 9.3."""

from pathlib import Path
from typing import Optional, Set, Union

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
        confidence_threshold: float = 0.60,
    ) -> None:
        self.portfolio = WholesalePortfolio.load_from_json(portfolio_path)
        self.valuation_engine = ValuationEngine(self.portfolio)
        self.confidence_threshold = confidence_threshold
        self.acted_signal_ids: Set[str] = set()

    def should_trigger(self, signal: RiskSignal) -> bool:
        """Evaluate if an incoming RiskSignal meets criteria for automated stress testing."""

        if not signal.eligible_for_action:
            return False

        if signal.event.label.upper() not in self.SUPPORTED_EVENT_CLASSES:
            return False

        if signal.impact.score <= 7:
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
        target_entity = signal.entity.ticker or signal.entity.name

        # Scope assignment
        if event_class in {"MACRO", "GEOPOLITICAL"} and not target_entity:
            scope = "systemic"
        elif target_entity:
            scope = "entity"
        else:
            scope = "systemic"

        # Easing detection for macro rate events
        evidence_text = " ".join(e.text for e in signal.evidence).lower()
        is_easing = (
            "rate cut" in evidence_text
            or "easing" in evidence_text
            or "lowers rates" in evidence_text
        )

        shock = build_scaled_shock(
            event_class=event_class,
            impact_score=impact,
            target_entity=target_entity,
            target_scope=scope,
            is_easing=is_easing,
        )

        result = self.valuation_engine.run_stress_test(
            shock=shock,
            run_id=signal.run_id,
            trigger_type="EVENT_TRIGGERED",
            trigger_signal_id=signal.signal_id,
            event_class=event_class,
            impact_score=impact,
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
        )

    def reset_triggers(self) -> None:
        """Reset deduplication cache of acted-upon signals."""
        self.acted_signal_ids.clear()
