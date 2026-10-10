"""Tests for additive impact severity rubric engine (PRD Section 7.4)."""

from sentinel.contracts.signals import EntityReference
from sentinel.nlp.severity import SeverityRubricEngine


def test_severe_credit_default_with_contagion():
    engine = SeverityRubricEngine()
    entity = EntityReference(name="Apex Industrial Holdings", ticker="APEX", scope="company")
    text = "Apex declared bankruptcy as nationwide contagion spreads across all banks."

    output, spans = engine.evaluate(
        event_class="CREDIT",
        text=text,
        entity=entity,
    )

    assert output.components.event_base == 5
    assert output.components.scope == 2
    assert output.components.explicit_severity == 2
    assert output.score == 9
    assert len(spans) >= 1
    assert any("bankruptcy" in s.text.lower() for s in spans)


def test_moderate_regulatory_probe():
    engine = SeverityRubricEngine()
    entity = EntityReference(name="Quantum Semiconductor", ticker="QSEM", scope="company")
    text = "DOJ opened formal antitrust investigation into proposed merger."

    output, spans = engine.evaluate(
        event_class="REGULATORY",
        text=text,
        entity=entity,
    )

    assert output.components.event_base == 4
    assert output.components.scope == 0
    assert output.components.explicit_severity == 1
    assert output.score == 5
    assert len(spans) >= 1


def test_routine_announcement_minimal_score():
    engine = SeverityRubricEngine()
    entity = EntityReference(name="Apple Inc", ticker="AAPL", scope="company")
    text = "Company uploaded regular corporate presentation slides to website."

    output, spans = engine.evaluate(
        event_class="OTHER",
        text=text,
        entity=entity,
    )

    assert output.components.event_base == 1
    assert output.components.scope == 0
    assert output.components.explicit_severity == 0
    assert output.score == 1
    assert len(spans) == 0


def test_score_clamped_bounds():
    engine = SeverityRubricEngine()
    entity = EntityReference(name="Systemic Entity", ticker=None, scope="macro")
    text = "Catastrophic default and nationwide contagion across all markets."

    output, _ = engine.evaluate("CREDIT", text, entity)
    assert 1 <= output.score <= 10


def _signal(text):
    from sentinel.contracts.records import InputRecord, SourceType
    from sentinel.nlp.engine import NLPEngine

    rec = InputRecord(record_id="imp", source_id="t", source_type=SourceType.NEWS, text=text)
    return NLPEngine().process_record(rec, "run-impact")


def test_market_calibration_card_beats_rubric_out_of_fold():
    """CI gate: the learned impact model must stay significantly related to real reactions."""
    import json

    from sentinel.config import settings

    m = json.loads((settings.base_dir / "models" / "impact_v2.card.json").read_text())["metrics"]
    assert m["events"] >= 2000
    assert m["learned_oof_spearman_ci95"][0] > 0  # CI excludes zero
    # the learned model must beat the explainable rubric out of fold (the rubric itself gained
    # signal once earnings news stopped being classified OTHER)
    assert m["learned_oof_spearman"] > m["rubric_v1_spearman"]
    assert m["large_move_rate_decile_10"] >= 3 * m["large_move_rate_decile_1"]


def test_company_signal_is_market_calibrated_with_audit_fields():
    s = _signal("Ford quarterly earnings miss estimates as profit falls 30%")
    assert s.entity.ticker == "F" and s.event.label == "EARNINGS"
    assert s.impact.method == "market_calibrated"
    cal = s.impact.market_calibration
    assert cal["decile"] == s.impact.score and cal["predicted_abs_abnormal_z"] > 0
    assert cal["model"].startswith("impact_v2:")


def test_systemic_scores_need_explicit_magnitude_to_exceed_threshold():
    assert (
        _signal("4 Low-Beta Utility Stocks to Buy Ahead of Fed's Likely Rate Hike").impact.score
        <= 7
    )
    hike = _signal("Federal Reserve raises rates by 75 basis points in surprise move")
    assert hike.impact.score >= 8
    assert any(e.text == "75 basis points" for e in hike.evidence)


def test_catastrophic_credit_language_sets_floor():
    s = _signal("Apex Industrial files emergency Chapter 11 bankruptcy petition after debt default")
    assert s.event.label == "CREDIT"
    assert s.impact.score >= 8


def test_company_signal_without_an_event_keeps_the_rubric():
    """Impact describes an event: an opinion piece classified OTHER is not market-calibrated."""
    s = _signal("Better Buy: ExxonMobil or Chevron? Both have strong balance sheets")
    assert s.event.label == "OTHER"
    assert s.impact.method == "rubric" and s.impact.score <= 3
