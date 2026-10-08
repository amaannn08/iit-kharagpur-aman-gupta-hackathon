"""Tests for FinBERTSentimentAnalyzer and fallback mode (PRD Section 7.2)."""

from sentinel.nlp.sentiment import FinBERTSentimentAnalyzer


def test_sentiment_negative_distress_detection():
    analyzer = FinBERTSentimentAnalyzer()
    text = "Apex Industrial faces acute liquidity crisis and severe debt default warning."
    output = analyzer.analyze(text)

    assert output.label == "negative"
    assert output.score < 0.0
    assert output.probabilities.negative > output.probabilities.positive
    total_prob = (
        output.probabilities.positive
        + output.probabilities.negative
        + output.probabilities.neutral
    )
    assert abs(total_prob - 1.0) < 0.01


def test_sentiment_positive_earnings_growth():
    analyzer = FinBERTSentimentAnalyzer()
    text = "Company reported record profit surge and revenue expansion with upgraded guidance."
    output = analyzer.analyze(text)

    assert output.label == "positive"
    assert output.score > 0.0
    assert output.probabilities.positive > output.probabilities.negative
    total_prob = (
        output.probabilities.positive
        + output.probabilities.negative
        + output.probabilities.neutral
    )
    assert abs(total_prob - 1.0) < 0.01


def test_sentiment_neutral_text():
    analyzer = FinBERTSentimentAnalyzer()
    text = "Annual general meeting scheduled for next Thursday at headquarters."
    output = analyzer.analyze(text)

    assert output.label == "neutral"
    assert output.score == 0.0
    assert output.probabilities.neutral >= 0.70


def test_sentiment_degraded_mode_reporting():
    # In absence of downloaded local checkpoint files, degraded_mode is reported truthfully
    analyzer = FinBERTSentimentAnalyzer()
    assert analyzer.degraded_mode is True
    assert analyzer.model_version == "lexicon_fallback_v1"
