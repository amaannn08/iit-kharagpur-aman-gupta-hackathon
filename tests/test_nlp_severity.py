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
