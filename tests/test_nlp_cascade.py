"""Tests for Two-Stage Threshold Event Classification Verification."""

from sentinel.nlp.cascade import CascadeEventClassifier


def test_cascade_fast_tier_resolution():
    cascade = CascadeEventClassifier()
    # High confidence clear credit default text
    text = "Company files Chapter 11 bankruptcy in Delaware court after defaulting on senior notes."
    res = cascade.classify(text)
    assert res.label == "CREDIT"
    assert res.tier_used == "fast_tier_1"
    assert "Fast tier confident" in res.routing_reason
    assert res.latency_ms > 0


def test_cascade_uncertain_routing():
    cascade = CascadeEventClassifier(confidence_cutoff=0.90, margin_cutoff=0.30)
    # Text with non-OTHER candidate but confidence < 0.90 routes to tier 2 verification
    text = "Company announces merger agreement with rival firm"
    res = cascade.classify(text)
    assert res.tier_used == "deep_tier_2"
    assert "Routed to Tier 2" in res.routing_reason


def test_cascade_stats_tracking():
    cascade = CascadeEventClassifier()
    cascade.classify("Fed raises interest rates")
    cascade.classify("Apple unveils new iPhone model")
    stats = cascade.stats.to_dict()
    assert stats["total_calls"] >= 2
    assert stats["tier1_resolved"] + stats["tier2_routed"] == stats["total_calls"]
    assert 0.0 <= stats["routing_rate_pct"] <= 100.0
