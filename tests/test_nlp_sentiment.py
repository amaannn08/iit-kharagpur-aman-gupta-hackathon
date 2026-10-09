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
        output.probabilities.positive + output.probabilities.negative + output.probabilities.neutral
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
        output.probabilities.positive + output.probabilities.negative + output.probabilities.neutral
    )
    assert abs(total_prob - 1.0) < 0.01


def test_sentiment_neutral_text():
    analyzer = FinBERTSentimentAnalyzer()
    text = "Annual general meeting scheduled for next Thursday at headquarters."
    output = analyzer.analyze(text)

    assert output.label == "neutral"
    assert abs(output.score) < 0.2  # score = P(pos) - P(neg); a learned model is not exactly 0
    assert output.probabilities.neutral >= 0.70


def test_sentiment_backend_and_degraded_mode_reporting(tmp_path):
    # The committed real-data model is the normal path ...
    analyzer = FinBERTSentimentAnalyzer()
    assert analyzer.backend == "tfidf"
    assert analyzer.degraded_mode is False
    assert analyzer.model_version.startswith("sentiment_v2:")
    # ... and without any artifact, degraded lexicon mode is reported truthfully
    bare = FinBERTSentimentAnalyzer(
        model_dir=tmp_path / "none", tfidf_path=tmp_path / "none.joblib"
    )
    assert bare.degraded_mode is True
    assert bare.model_version == "lexicon_fallback_v1"
    assert bare.analyze("Severe debt default warning").label == "negative"


def test_policy_direction_and_macro_polarity():
    from sentinel.nlp.sentiment import macro_polarity, policy_direction

    assert policy_direction("Fed cuts interest rates by 50 basis points")[0] == "easing"
    assert policy_direction("ECB lowers its key deposit rate")[0] == "easing"
    assert policy_direction("Federal Reserve raises benchmark interest rates")[0] == "tightening"
    assert policy_direction("Jobs report beats estimates")[0] == "none"
    assert macro_polarity("Initial jobless claims rose sharply to 260,000")[0] == -1.0
    assert macro_polarity("US inflation cooled to 3.1% in November")[0] == 1.0


def test_macro_polarity_keeps_score_probability_contract():
    from sentinel.contracts.signals import SentimentOutput, SentimentProbabilities
    from sentinel.nlp.sentiment import apply_macro_polarity

    s = SentimentOutput(
        score=0.8,
        label="positive",
        probabilities=SentimentProbabilities(positive=0.85, negative=0.05, neutral=0.10),
    )
    m = apply_macro_polarity(s, "Jobless claims surged to a two-year high")
    assert m is not None and m.group().lower().startswith("jobless claims")
    p = s.probabilities
    assert abs(s.score - (p.positive - p.negative)) < 1e-6
    assert abs(p.positive + p.negative + p.neutral - 1.0) < 1e-6
    assert s.score < 0.8


def test_rate_cut_and_hike_get_opposite_signs_in_engine():
    from sentinel.contracts.records import InputRecord, SourceType
    from sentinel.nlp.engine import NLPEngine

    engine = NLPEngine()

    def score(text):
        rec = InputRecord(record_id="r", source_id="t", source_type=SourceType.NEWS, text=text)
        return engine.process_record(rec, "run").sentiment.score

    assert score("Fed cuts interest rates by 50 basis points") > 0
    assert score("Federal Reserve raises benchmark interest rates 75 basis points") < 0
