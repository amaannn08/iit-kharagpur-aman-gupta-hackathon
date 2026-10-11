"""Unit tests for acquirer-side M&A shock handling (Item 10).

Validates:
1. Acquirer role resolution on active syntax ('Broadcom to acquire VMware ...').
2. Passive syntax resolution ('VMware to be acquired by Broadcom ...').
3. Target entity receives no shock (takeover premium, not stress).
4. Unresolved roles emit no shock ('Broadcom and VMware in merger talks').
5. Debt-financing multiplier (1.5x) and all-stock multiplier (0.5x).
6. Shock parameters for M_AND_A in catalog.
"""

from datetime import datetime

from sentinel.contracts.records import InputRecord
from sentinel.nlp.engine import NLPEngine
from sentinel.nlp.roles import (
    get_ma_financing_multiplier,
)
from sentinel.stress.engine import StressEngine
from sentinel.stress.shocks import DEFAULT_SHOCK_CATALOG, build_scaled_shock


def test_ma_catalog_and_supported_classes():
    assert "M_AND_A" in DEFAULT_SHOCK_CATALOG
    params = DEFAULT_SHOCK_CATALOG["M_AND_A"]
    assert params.bond_spread_shift_bps == 40.0
    assert params.loan_pd_increment == 0.004
    assert params.equity_shock_pct == -0.03

    engine = StressEngine()
    assert "M_AND_A" in engine.SUPPORTED_EVENT_CLASSES


def test_ma_financing_multipliers():
    assert get_ma_financing_multiplier("Deal funded by new debt") == 1.5
    assert get_ma_financing_multiplier("Acquisition backed by bridge loan") == 1.5
    assert get_ma_financing_multiplier("Term loan to finance purchase") == 1.5
    assert get_ma_financing_multiplier("All-stock merger agreement") == 0.5
    assert get_ma_financing_multiplier("Stock-for-stock combination") == 0.5
    assert get_ma_financing_multiplier("Acquisition for $61 billion") == 1.0


def test_active_ma_resolves_acquirer_and_debt_scale():
    nlp = NLPEngine()
    stress = StressEngine()
    text = "Broadcom to acquire VMware for $61 billion, funded by new debt"

    record = InputRecord(
        record_id="rec-ma-1",
        source_id="news_test",
        source_type="news",
        text=text,
        published_at=datetime.utcnow(),
        timestamp_quality="original",
        simulated_at=datetime.utcnow(),
        is_synthetic=False,
    )

    signals = nlp.process_record_multi(record, run_id="run-ma-1")
    assert len(signals) >= 1

    avgo_sig = next((s for s in signals if s.entity.ticker == "AVGO"), None)
    assert avgo_sig is not None
    assert avgo_sig.entity.role == "acquirer"
    assert avgo_sig.eligible_for_action is True
    assert avgo_sig.impact.score >= 8

    assert stress.should_trigger(avgo_sig) is True
    res = stress.trigger_from_signal(avgo_sig)
    assert res is not None
    assert res.shock_parameters["target_entity"] == "AVGO"
    # Base spread 40 * (8/8) * 1.5 (debt) = 60 bps
    assert res.shock_parameters["bond_spread_shift_bps"] == 60.0
    # Base PD 0.004 * 1.5 = 0.006
    assert res.shock_parameters["loan_pd_increment"] == 0.006
    # Base equity -0.03 * 1.5 = -0.045
    assert res.shock_parameters["equity_shock_pct"] == -0.045


def test_passive_ma_resolves_acquirer():
    nlp = NLPEngine()
    stress = StressEngine()
    text = "VMware to be acquired by Broadcom for $61 billion, funded by new debt"

    record = InputRecord(
        record_id="rec-ma-2",
        source_id="news_test",
        source_type="news",
        text=text,
        published_at=datetime.utcnow(),
        timestamp_quality="original",
        simulated_at=datetime.utcnow(),
        is_synthetic=False,
    )

    signals = nlp.process_record_multi(record, run_id="run-ma-2")
    avgo_sig = next((s for s in signals if s.entity.ticker == "AVGO"), None)
    assert avgo_sig is not None
    assert avgo_sig.entity.role == "acquirer"
    assert stress.should_trigger(avgo_sig) is True
    res = stress.trigger_from_signal(avgo_sig)
    assert res is not None
    assert res.shock_parameters["target_entity"] == "AVGO"


def test_target_entity_is_not_stressed():
    nlp = NLPEngine()
    stress = StressEngine()
    # Broadcom is the target here
    text = "VMware to acquire Broadcom for $61 billion"

    record = InputRecord(
        record_id="rec-ma-3",
        source_id="news_test",
        source_type="news",
        text=text,
        published_at=datetime.utcnow(),
        timestamp_quality="original",
        simulated_at=datetime.utcnow(),
        is_synthetic=False,
    )

    signals = nlp.process_record_multi(record, run_id="run-ma-3")
    avgo_sig = next((s for s in signals if s.entity.ticker == "AVGO"), None)
    assert avgo_sig is not None
    assert avgo_sig.entity.role == "target"
    assert avgo_sig.eligible_for_action is False
    assert "TARGET_TAKEOVER_PREMIUM_NOT_STRESSED" in avgo_sig.action_block_reasons
    assert stress.should_trigger(avgo_sig) is False


def test_undetermined_roles_emit_no_shock():
    nlp = NLPEngine()
    stress = StressEngine()
    text = "Broadcom and VMware in merger talks"

    record = InputRecord(
        record_id="rec-ma-4",
        source_id="news_test",
        source_type="news",
        text=text,
        published_at=datetime.utcnow(),
        timestamp_quality="original",
        simulated_at=datetime.utcnow(),
        is_synthetic=False,
    )

    signals = nlp.process_record_multi(record, run_id="run-ma-4")
    avgo_sig = next((s for s in signals if s.entity.ticker == "AVGO"), None)
    assert avgo_sig is not None
    assert avgo_sig.entity.role == "undetermined"
    assert avgo_sig.eligible_for_action is False
    assert "MA_ROLES_UNDETERMINED" in avgo_sig.action_block_reasons
    assert stress.should_trigger(avgo_sig) is False


def test_all_stock_financing_scale():
    shock = build_scaled_shock(
        event_class="M_AND_A",
        impact_score=8,
        target_entity="AVGO",
        target_scope="entity",
        financing_multiplier=0.5,
    )
    # Base spread 40 * 1.0 * 0.5 = 20 bps
    assert shock.bond_spread_shift_bps == 20.0
    # Base PD 0.004 * 0.5 = 0.002
    assert shock.loan_pd_increment == 0.002
    # Base equity -0.03 * 0.5 = -0.015
    assert shock.equity_shock_pct == -0.015
