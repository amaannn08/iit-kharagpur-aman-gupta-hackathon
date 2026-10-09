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


def _tickers(linker, text):
    return [ref.ticker for ref, _ in linker.resolve_all(text)]


def test_resolve_all_returns_every_company_with_exact_spans():
    linker = EntityLinker()
    text = "Nasdaq-listed Tesla and Apple rally as Microsoft earnings beat; IBM, AMD slip"
    found = linker.resolve_all(text)
    assert [ref.ticker for ref, _ in found] == ["TSLA", "AAPL", "MSFT", "IBM", "AMD"]
    for ref, spans in found:
        assert spans and all(text[s.start : s.end] == s.text for s in spans)
        assert ref.sector


def test_cashtag_does_not_double_count_bare_ticker():
    _, spans = EntityLinker().resolve("Puts on $APEX are exploding before the APEX bond call")
    assert [s.text for s in spans] == ["$APEX", "APEX"]


def test_exchange_notation_and_possessive_official_names():
    linker = EntityLinker()
    assert _tickers(linker, "S&P Global Ratings lowers Ford (NYSE: F) to BB+ on weak margins") == [
        "F"
    ]
    assert _tickers(linker, "McDonald's vs. Procter & Gamble Stock") == ["MCD", "PG"]
    assert _tickers(linker, "Moody's shares rise after quarterly earnings beat") == ["MCO"]


def test_rating_agencies_brokers_and_sponsors_are_not_subjects():
    linker = EntityLinker()
    assert _tickers(linker, "Apex Industrial downgraded to junk by Moody's on debt load") == [
        "APEX"
    ]
    assert "WFC" not in _tickers(linker, "Wells Fargo maintains Overweight rating on Exxon shares")
    assert "MS" not in _tickers(
        linker, "Airbnb stock dropped after a Morgan Stanley analyst cut it"
    )
    assert "IVZ" not in _tickers(linker, "Is the Invesco FTSE RAFI US 1000 ETF a strong buy?")
    assert "TGT" not in _tickers(
        linker, "Here's a look at recent price target changes for Microsoft"
    )


def test_all_caps_headlines_and_acronyms_are_not_tickers():
    linker = EntityLinker()
    ref, _ = linker.resolve("BREAKING: FED HIKES RATES AS CPI JUMPS")
    assert ref.ticker is None
    assert _tickers(linker, "Which stock has the better PEG ratio this quarter?") == [None]


def test_universe_marks_demo_issuers_synthetic():
    linker = EntityLinker()
    assert linker.entities["APEX"].is_synthetic is True
    assert linker.entities["AAPL"].is_synthetic is False
    assert len([e for e in linker.entities.values() if not e.is_synthetic]) >= 500
