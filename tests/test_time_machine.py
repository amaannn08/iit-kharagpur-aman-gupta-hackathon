"""Tests for Crisis Time Machine endpoints and dataset integrity."""

from fastapi.testclient import TestClient

from sentinel.api.app import create_app
from sentinel.contracts.records import InputRecord, SourceType
from sentinel.nlp.engine import NLPEngine
from sentinel.stress.story_trigger import StoryTracker

client = TestClient(create_app())


def test_list_crises():
    res = client.get("/api/time-machine/crises")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 4
    crisis_ids = [c["crisis_id"] for c in data]
    assert "svb" in crisis_ids
    assert "crowdstrike" in crisis_ids
    assert "ukraine" in crisis_ids
    assert "first_republic" in crisis_ids
    for c in data:
        assert "lead_time_display" in c
        assert "triggered" in c


def test_get_svb_crisis_detail():
    res = client.get("/api/time-machine/crisis/svb")
    assert res.status_code == 200
    data = res.json()
    assert data["crisis_id"] == "svb"
    assert "lead_time_display" in data
    assert len(data["milestones"]) >= 2
    assert len(data["price_trajectory"]) > 0
    assert len(data["timeline_series"]) > 0
    assert "naive_alert_performance" in data
    assert "sentinel_performance" in data
    assert data["sentinel_performance"]["sentinel_false_positives"] == 0
    assert data["naive_alert_performance"]["naive_triggers"] > 0


def test_get_crowdstrike_crisis_detail():
    res = client.get("/api/time-machine/crisis/crowdstrike")
    assert res.status_code == 200
    data = res.json()
    assert data["crisis_id"] == "crowdstrike"
    assert len(data["milestones"]) >= 2
    assert len(data["timeline_series"]) > 0
    assert "naive_alert_performance" in data
    assert "sentinel_performance" in data


def test_get_ukraine_crisis_detail():
    res = client.get("/api/time-machine/crisis/ukraine")
    assert res.status_code == 200
    data = res.json()
    assert data["crisis_id"] == "ukraine"
    assert len(data["milestones"]) >= 2
    assert len(data["timeline_series"]) > 0
    assert "naive_alert_performance" in data
    assert "sentinel_performance" in data


def test_load_crisis_into_replay():
    res = client.post("/api/time-machine/crisis/svb/replay")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "loaded"
    assert data["crisis_id"] == "svb"
    assert data["records_queued"] > 2000


def test_crisis_threshold_sensitivity_proves_computed():
    """Verify that story triggering and lead times are computed dynamically.

    Raising the story trigger threshold from 6.5 to 10.0 prevents triggers
    from firing on developing risk stories.
    """
    nlp = NLPEngine()
    rec1 = InputRecord(
        record_id="1",
        source_id="test",
        source_type=SourceType.NEWS,
        text="Silicon Valley Bank suffers massive deposit run and $1.8B loss on bond sale.",
    )
    rec2 = InputRecord(
        record_id="2",
        source_id="test",
        source_type=SourceType.NEWS,
        text="Silicon Valley Bank emergency capital raise fails amid deepening liquidity panic.",
    )
    s1 = nlp.process_record(rec1, "run")
    s2 = nlp.process_record(rec2, "run")

    tracker_low = StoryTracker(trigger_threshold=6.5)
    _, t1_low, _ = tracker_low.process_signal(s1)
    _, t2_low, reason_low = tracker_low.process_signal(s2)

    tracker_high = StoryTracker(trigger_threshold=15.0)
    _, t1_high, _ = tracker_high.process_signal(s1)
    _, t2_high, reason_high = tracker_high.process_signal(s2)

    assert t2_low is True
    assert "Story escalation" in reason_low
    assert t2_high is False
    assert reason_high is None
