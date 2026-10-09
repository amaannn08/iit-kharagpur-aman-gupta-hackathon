"""Social relevance screening (spam and non-financial chatter are never actionable)."""

from sentinel.contracts.records import InputRecord, SourceType
from sentinel.nlp.engine import NLPEngine
from sentinel.nlp.relevance import social_block_reason


def test_listing_spam_and_chatter_are_blocked():
    assert (
        social_block_reason("DO NOT MISS IT Samsung Galaxy S7 32GB Factory Unlocked GSM Phone")
        == "SOCIAL_SPAM"
    )
    assert (
        social_block_reason("You could #win a Sony PS4 Pro. Enter our #prize #giveaway")
        == "SOCIAL_SPAM"
    )
    assert (
        social_block_reason("#MadamCJWalker is coming to Netflix, with Octavia Spencer")
        == "NO_FINANCIAL_CONTEXT"
    )


def test_financial_posts_pass_including_bond_coupons_and_macro():
    assert (
        social_block_reason("Chatter that $APEX defaulted on its loan coupon. CDS spreads +280 bps")
        is None
    )
    assert social_block_reason("ECB hawkish surprise, European sovereign yields spiking") is None
    assert (
        social_block_reason("Netflix shares jump after subscriber growth beats estimates") is None
    )


def test_engine_blocks_irrelevant_social_but_not_news():
    engine = NLPEngine()
    text = "Walmart and Drake brought it up, I did not wake up today to make fun of anyone"
    social = InputRecord(record_id="s", source_id="t", source_type=SourceType.SOCIAL, text=text)
    news = InputRecord(record_id="n", source_id="t", source_type=SourceType.NEWS, text=text)
    assert "NO_FINANCIAL_CONTEXT" in engine.process_record(social, "r").action_block_reasons
    assert "NO_FINANCIAL_CONTEXT" not in engine.process_record(news, "r").action_block_reasons
