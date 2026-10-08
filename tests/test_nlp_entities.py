"""Tests for EntityLinker resolution and disambiguation (PRD Section 7.1)."""

from sentinel.nlp.entities import EntityLinker


def test_cashtag_resolution():
    linker = EntityLinker()
    text = "Heavy trading pressure observed for $APEX ahead of bond maturity."
    entity, spans = linker.resolve(text)

    assert entity.resolved is True
    assert entity.ticker == "APEX"
    assert entity.name == "Apex Industrial Holdings"
    assert len(spans) == 1
    assert spans[0].text == "$APEX"
    assert text[spans[0].start : spans[0].end] == "$APEX"


def test_alias_resolution():
    linker = EntityLinker()
    text = "Credit rating downgraded for Global Logistics following default on credit facility."
    entity, spans = linker.resolve(text)

    assert entity.resolved is True
    assert entity.ticker == "GLOG"
    assert entity.name == "Global Logistics Corp"
    assert len(spans) == 1
    assert spans[0].text.lower() == "global logistics"


def test_ambiguity_handling():
    linker = EntityLinker()

    # Ambiguous token without financial context -> should NOT resolve to AAPL
    food_text = "I bought an apple at the farmer market."
    entity, _ = linker.resolve(food_text)
    assert entity.ticker != "AAPL"

    # Ambiguous token WITH financial context -> DOES resolve to AAPL
    fin_text = "Apple quarterly revenue and earnings topped analyst expectations for shares."
    entity_fin, spans = linker.resolve(fin_text)
    assert entity_fin.resolved is True
    assert entity_fin.ticker == "AAPL"
    assert spans[0].text == "Apple"


def test_unknown_entity_not_hallucinated():
    linker = EntityLinker()
    text = "Some totally unknown startup announced a new blockchain gadget."
    entity, spans = linker.resolve(text)

    assert entity.resolved is False
    assert entity.ticker is None
    assert entity.scope == "unknown"


def test_macro_entity_resolution():
    linker = EntityLinker()
    text = "Federal Reserve signals higher policy rates to combat stubborn inflation."
    entity, _ = linker.resolve(text)

    assert entity.resolved is True
    assert entity.scope == "macro"
