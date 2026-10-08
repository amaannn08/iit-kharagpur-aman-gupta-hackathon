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
