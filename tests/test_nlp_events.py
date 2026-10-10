"""Tests for EventClassifier and abstention logic (PRD Section 7.3)."""

from sentinel.nlp.events import EventClassifier


def test_credit_event_classification():
    clf = EventClassifier(confidence_threshold=0.30)
    text = "Apex Industrial missed scheduled coupon payment, triggering default on credit facility."
    output = clf.predict(text)

    assert output.label == "CREDIT"
    assert output.abstained is False
    assert output.confidence >= 0.30


def test_macro_event_classification():
    clf = EventClassifier(confidence_threshold=0.30)
    text = "Federal Reserve raises benchmark interest rates to tighten policy against inflation."
    output = clf.predict(text)

    assert output.label == "MACRO"
    assert output.abstained is False


def test_cyber_event_classification():
    clf = EventClassifier(confidence_threshold=0.30)
    text = "Ransomware zero-day flaw actively exploited to breach customer databases."
    output = clf.predict(text)

    assert output.label == "CYBER"
    assert output.abstained is False


def test_abstention_on_routine_or_unclear_text():
    clf = EventClassifier(confidence_threshold=0.70)
    # Routine administrative text maps to OTHER with abstained=True
    text = "The annual general meeting of shareholders will convene to review governance."
    output = clf.predict(text)

    assert output.label == "OTHER"
    assert output.abstained is True


def test_abstention_under_high_confidence_threshold():
    # If confidence threshold is set impossibly high (e.g. 0.99), classifier must abstain
    clf = EventClassifier(confidence_threshold=0.99)
    text = "Company announces acquisition agreement."
    output = clf.predict(text)

    assert output.label == "OTHER"
    assert output.abstained is True


def test_model_persistence_and_reload(tmp_path):
    clf = EventClassifier()
    model_file = tmp_path / "event_model.joblib"
    clf.save_model(model_file)
    assert model_file.exists()

    reloaded_clf = EventClassifier(model_path=model_file)
    assert reloaded_clf.pipeline is not None
    pred = reloaded_clf.predict("missed coupon payment default debt restructuring")
    assert pred.label == "CREDIT"


def test_trained_model_loads_with_card_threshold():
    import json

    from sentinel.config import settings

    clf = EventClassifier()
    card = json.loads((settings.base_dir / "models" / "event_v2.card.json").read_text())
    assert clf.degraded_mode is False
    assert clf.confidence_threshold == card["abstain_threshold"]
    assert clf.model_version.startswith("event_v2:")


def test_card_reports_held_out_real_data_quality_gate():
    """CI gate: the committed model must keep >= 0.80 macro-F1 on held-out real tweets."""
    import json

    from sentinel.config import settings

    card = json.loads((settings.base_dir / "models" / "event_v2.card.json").read_text())
    valid = card["metrics"]["hf_topic_valid"]
    assert valid["n"] == 4117
    assert valid["macro_f1_8_ps_classes"] >= 0.80
    assert valid["abstention_at_threshold"]["precision"] >= 0.88


def test_gates_require_class_evidence():
    from sentinel.nlp.events import apply_gate

    assert apply_gate("GEOPOLITICAL", "Democrats bet on pastors in the midterms")[0] == "OTHER"
    label, spans = apply_gate("GEOPOLITICAL", "New sanctions hit Russian energy exports")
    assert label == "GEOPOLITICAL" and spans[0].text == "sanctions"
    assert apply_gate("MACRO", "Analyst expectations for Essex Property Trust")[0] == "OTHER"
    assert apply_gate("PRODUCT", "Apple unveils a new iPhone")[0] == "PRODUCT"
    assert apply_gate("CREDIT", "anything")[0] == "CREDIT"  # ungated class


def test_credit_distress_maps_to_credit_event():
    from sentinel.nlp.events import ps_aligned_label

    assert ps_aligned_label(2, "Celsius files for Chapter 11 bankruptcy protection") == "CREDIT"
    assert ps_aligned_label(2, "Apple unveils a new iPhone") == "PRODUCT"
    clf = EventClassifier()
    text = "Retailer files emergency Chapter 11 bankruptcy petition after debt default"
    assert clf.predict(text).label == "CREDIT"


def test_missing_artifact_falls_back_to_degraded_seed_baseline(tmp_path):
    clf = EventClassifier(model_path=tmp_path / "missing.joblib")
    assert clf.degraded_mode is True
    assert clf.model_version == "seed_baseline_degraded"
    assert clf.predict("ransomware attack encrypts bank servers").label in {"CYBER", "OTHER"}


def test_routine_8k_filings_rarely_look_like_credit_events():
    """CI gate: held-out routine 8-Ks (results, officer changes, Reg FD, other events, new debt)
    must rarely be sent to the credit/cyber stress path."""
    import json

    from sentinel.config import settings

    sec = json.loads((settings.base_dir / "models" / "event_v2.card.json").read_text())["metrics"]
    held = sec["sec_8k_heldout_filings"]
    assert held["routine_filings_false_stress_rate"] <= 0.15
    # ~8 held-out cyber filings: one miss is 12.5 points, so the gate allows one
    assert held["recall_by_class"]["CREDIT"] >= 0.80 and held["recall_by_class"]["CYBER"] >= 0.85
