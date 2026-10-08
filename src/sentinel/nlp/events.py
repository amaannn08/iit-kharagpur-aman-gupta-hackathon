"""Event classification engine with TF-IDF baseline and abstention logic (PRD Section 7.3)."""

import logging
from pathlib import Path
from typing import List, Optional, Tuple, Union

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from sentinel.contracts.signals import EventOutput

logger = logging.getLogger(__name__)

SUPPORTED_EVENT_CLASSES = [
    "GEOPOLITICAL",
    "MACRO",
    "CREDIT",
    "M_AND_A",
    "PRODUCT",
    "REGULATORY",
    "SUPPLY_CHAIN",
    "EARNINGS",
    "CYBER",
    "OTHER",
]

# High-fidelity curated domain training examples representing each event class
SEED_TRAINING_CORPUS: List[Tuple[str, str]] = [
    # CREDIT
    ("missed scheduled coupon payment default covenant breach debt restructuring", "CREDIT"),
    ("downgraded to junk status credit rating cut to Baa3 by Moody's", "CREDIT"),
    ("bankruptcy protection chapter 11 filing insolvent credit lines frozen", "CREDIT"),
    ("liquidity shortfall unable to meet commercial paper redemption obligations", "CREDIT"),
    ("bank run depositor outflows trigger emergency liquidity borrowing", "CREDIT"),
    ("default on credit facility borrower distressed restructuring", "CREDIT"),
    ("credit facility coupon payment missed default covenants triggered", "CREDIT"),
    # MACRO
    ("Federal Reserve raises benchmark interest rates 50 basis points to curb inflation", "MACRO"),
    ("central bank cuts discount rate amid slowing economic growth and disinflation", "MACRO"),
    ("treasury yields invert across 2-year and 10-year curve signaling recession", "MACRO"),
    ("consumer price index inflation surge forces monetary policy tightening", "MACRO"),
    ("unemployment rate rises as GDP contracts for second consecutive quarter", "MACRO"),
    ("interest rates benchmark hike monetary policy tighten yields", "MACRO"),
    ("Federal Reserve benchmark interest rates inflation monetary policy", "MACRO"),
    # GEOPOLITICAL
    ("trade sanctions imposed on key trading partner blocking energy exports", "GEOPOLITICAL"),
    ("tariffs enacted on steel and aluminum sparking retaliatory trade measures", "GEOPOLITICAL"),
    ("cross-border military conflict disrupts critical shipping corridor", "GEOPOLITICAL"),
    ("foreign government nationalizes corporate assets without compensation", "GEOPOLITICAL"),
    ("bilateral trade negotiations collapse amid diplomatic standoff", "GEOPOLITICAL"),
    # M_AND_A
    ("announced all-cash acquisition agreement valued at four billion dollars", "M_AND_A"),
    ("hostile takeover bid launched by activist hedge fund for outstanding shares", "M_AND_A"),
    ("merger of equals approved by boards to create industry conglomerate", "M_AND_A"),
    ("divestiture of non-core consumer unit completed for cash consideration", "M_AND_A"),
    ("definitive purchase agreement signed to acquire regional competitor", "M_AND_A"),
    # PRODUCT
    ("wins priority FDA approval for breakthrough oncology drug therapeutic", "PRODUCT"),
    ("voluntary nationwide product recall issued over safety defect and hazards", "PRODUCT"),
    ("phase 3 clinical trial fails primary efficacy endpoint in clinical study", "PRODUCT"),
    ("patent infringement injunction halts distribution of flagship device", "PRODUCT"),
    ("next-generation hardware architecture launched commercially worldwide", "PRODUCT"),
    # REGULATORY
    ("DOJ files antitrust lawsuit to block monopolistic market concentration", "REGULATORY"),
    ("SEC launches formal enforcement investigation into accounting irregularities", "REGULATORY"),
    ("consumer financial protection agency levies record civil money penalty", "REGULATORY"),
    ("stricter emissions standard enforced with immediate operational curbs", "REGULATORY"),
    ("banking regulators issue cease-and-desist order for compliance deficiencies", "REGULATORY"),
    # SUPPLY_CHAIN
    ("declares force majeure after fire damages primary blast furnace", "SUPPLY_CHAIN"),
    ("port dockworkers strike halts container freight operations nationwide", "SUPPLY_CHAIN"),
    ("semiconductor component shortages force production line shutdowns", "SUPPLY_CHAIN"),
    ("freight logistics delays double container turnaround times at key hubs", "SUPPLY_CHAIN"),
    ("raw material export embargo cuts off essential lithium battery inputs", "SUPPLY_CHAIN"),
    # EARNINGS
    ("reports record quarterly earnings as net interest margin widens thirty bps", "EARNINGS"),
    ("slashes full year revenue guidance and profit targets due to rising costs", "EARNINGS"),
    ("first quarter earnings per share beat consensus estimates by fifteen percent", "EARNINGS"),
    ("operating profit drops sharply as operating margin compresses", "EARNINGS"),
    ("quarterly net income surges fifty percent driven by commercial loan growth", "EARNINGS"),
    # CYBER
    ("critical zero-day security flaw in enterprise gateway actively exploited", "CYBER"),
    ("ransomware attack compromises internal corporate databases and encrypted servers", "CYBER"),
    ("malicious unauthorized data breach exposes customer banking credentials", "CYBER"),
    ("distributed denial of service attacks knock online trading portals offline", "CYBER"),
    ("supply chain software infiltration compromises downstream client networks", "CYBER"),
    ("ransomware zero-day security flaw exploit breach databases", "CYBER"),
    # OTHER
    ("board of directors schedules annual general meeting of shareholders", "OTHER"),
    ("company updates routine corporate governance committee charter", "OTHER"),
    ("executive appointed to non-executive board seat at industry association", "OTHER"),
    ("regular quarterly dividend declared payable on standard record date", "OTHER"),
    ("routine investor relations presentation slides uploaded to company website", "OTHER"),
]


class EventClassifier:
    """TF-IDF and Logistic Regression event classifier with auditable abstention."""

    def __init__(
        self,
        model_path: Optional[Union[str, Path]] = None,
        confidence_threshold: float = 0.50,
    ) -> None:
        self.model_path = (
            Path(model_path) if model_path else Path(".runtime/models/events/model.joblib")
        )
        self.confidence_threshold = confidence_threshold
        self.pipeline: Optional[Pipeline] = None

        self._load_or_train()

    def _load_or_train(self) -> None:
        """Load persisted model artifact if present, otherwise fit on curated corpus."""
        if self.model_path.exists():
            try:
                self.pipeline = joblib.load(self.model_path)
                logger.info("Loaded trained event classifier from %s", self.model_path)
                return
            except Exception as exc:
                logger.warning("Could not load %s (%s). Retraining baseline.", self.model_path, exc)

        self._train_baseline()

    def _train_baseline(self) -> None:
        """Fit a TF-IDF + Logistic Regression pipeline on the curated seed corpus."""
        texts = [item[0] for item in SEED_TRAINING_CORPUS]
        labels = [item[1] for item in SEED_TRAINING_CORPUS]

        pipeline = Pipeline([
            (
                "tfidf",
                TfidfVectorizer(
                    ngram_range=(1, 2),
                    sublinear_tf=True,
                    lowercase=True,
                ),
            ),
            (
                "clf",
                LogisticRegression(
                    C=25.0,
                    class_weight="balanced",
                    max_iter=500,
                    random_state=42,
                ),
            ),
        ])
        pipeline.fit(texts, labels)
        self.pipeline = pipeline

    def save_model(self, path: Optional[Union[str, Path]] = None) -> Path:
        """Persist current trained pipeline to disk."""
        target = Path(path) if path else self.model_path
        target.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.pipeline, target)
        logger.info("Saved event classifier pipeline to %s", target)
        return target

    def predict(self, text: str) -> EventOutput:
        """Predict event category with explicit confidence threshold and abstention.

        If top predicted probability < confidence_threshold or top class is OTHER,
        abstains to OTHER with abstained=True.
        """
        if self.pipeline is None:
            return EventOutput(label="OTHER", confidence=0.0, abstained=True)

        probs = self.pipeline.predict_proba([text])[0]
        classes = self.pipeline.classes_

        best_idx = probs.argmax()
        top_label = classes[best_idx]
        top_conf = round(float(probs[best_idx]), 4)

        if top_conf < self.confidence_threshold or top_label == "OTHER":
            return EventOutput(
                label="OTHER",
                confidence=top_conf,
                abstained=True,
            )

        return EventOutput(
            label=top_label,
            confidence=top_conf,
            abstained=False,
        )
