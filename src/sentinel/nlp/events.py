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
    (
        "skipped an interest payment to bondholders and is in talks with lenders restructuring",
        "CREDIT",
    ),
    (
        "failed to remit scheduled payment to lending syndicate triggering 30-day cure period",
        "CREDIT",
    ),
    ("downgraded to junk status credit rating cut to Baa3 by Moody's negative outlook", "CREDIT"),
    (
        "credit rating agency issues negative outlook downgrade warning on heavy debt maturities",
        "CREDIT",
    ),
    ("bankruptcy protection chapter 11 filing insolvent credit lines frozen", "CREDIT"),
    ("files emergency chapter 11 bankruptcy petition debt default insolvency", "CREDIT"),
    ("liquidity shortfall unable to meet commercial paper redemption obligations", "CREDIT"),
    ("bank run depositor outflows trigger emergency liquidity borrowing discount window", "CREDIT"),
    (
        "default on syndicated credit facility borrower distressed debt restructuring counsel",
        "CREDIT",
    ),
    (
        "senior unsecured bondholders retain restructuring counsel to evaluate "
        "debt for equity swap",
        "CREDIT",
    ),
    (
        "creditors assemble ad hoc committee as firm enters comprehensive debt restructuring",
        "CREDIT",
    ),
    ("credit facility coupon payment missed technical default covenants triggered", "CREDIT"),
    (
        "central bank affirms standing discount window will support solvent lenders "
        "facing liquidity stress",
        "CREDIT",
    ),
    # MACRO
    ("Federal Reserve raises benchmark interest rates 50 basis points to curb inflation", "MACRO"),
    (
        "Federal Reserve signals benchmark rate hike amid persistent core services inflation",
        "MACRO",
    ),
    (
        "Federal Reserve announces emergency 100 basis point interest rate hike systemic contagion",
        "MACRO",
    ),
    (
        "central bank cuts discount rate amid slowing economic growth and disinflation easing",
        "MACRO",
    ),
    (
        "Federal Reserve cuts interest rates by 75 basis points in emergency monetary easing",
        "MACRO",
    ),
    (
        "sovereign bond prices plummet as benchmark 10-year Treasury yields surge "
        "14 basis points on PPI print",
        "MACRO",
    ),
    (
        "treasury yields invert across 2-year and 10-year curve signaling impending recession",
        "MACRO",
    ),
    ("consumer price index inflation surge forces monetary policy tightening cycle", "MACRO"),
    (
        "European Central Bank signals surprise liquidity reserve requirement hikes to "
        "stabilize currency",
        "MACRO",
    ),
    ("unemployment rate rises as GDP contracts for second consecutive quarter", "MACRO"),
    ("central bank governor confirms benchmark policy rate setting monetary committee", "MACRO"),
    # GEOPOLITICAL
    ("trade sanctions imposed on key trading partner blocking energy exports", "GEOPOLITICAL"),
    ("tariffs enacted on steel and aluminum sparking retaliatory trade measures", "GEOPOLITICAL"),
    (
        "cross-border military conflict disrupts critical shipping corridor maritime straits",
        "GEOPOLITICAL",
    ),
    (
        "naval skirmish closes maritime choke points driving benchmark crude oil "
        "futures up sharply",
        "GEOPOLITICAL",
    ),
    (
        "foreign government nationalizes corporate assets and energy concessions "
        "without compensation",
        "GEOPOLITICAL",
    ),
    (
        "bilateral trade negotiations collapse amid diplomatic standoff and export curbs",
        "GEOPOLITICAL",
    ),
    ("global trade pact talks stall over agricultural export subsidies deadlock", "GEOPOLITICAL"),
    # M_AND_A
    ("announced all-cash acquisition agreement valued at four billion dollars", "M_AND_A"),
    ("hostile takeover bid launched by activist hedge fund for outstanding shares", "M_AND_A"),
    ("merger of equals approved by boards to create industry conglomerate", "M_AND_A"),
    ("divestiture of non-core consumer unit completed for cash consideration", "M_AND_A"),
    ("definitive purchase agreement signed to acquire regional utility solar generator", "M_AND_A"),
    ("board of directors approves buyout bid from private equity consortium", "M_AND_A"),
    # PRODUCT
    ("wins priority FDA approval for breakthrough oncology drug therapeutic", "PRODUCT"),
    (
        "unconditional FDA approval received for novel oncology kinase inhibitor therapeutic",
        "PRODUCT",
    ),
    (
        "voluntary nationwide product recall issued over safety defect and battery fire hazard",
        "PRODUCT",
    ),
    (
        "phase 3 clinical trial fails primary efficacy endpoint in randomized clinical study",
        "PRODUCT",
    ),
    ("patent infringement injunction halts commercial distribution of flagship device", "PRODUCT"),
    (
        "activates transpacific subsea fiber network ahead of schedule expanding bandwidth",
        "PRODUCT",
    ),
    (
        "secures multi-year direct offtake agreement to provide battery grade lithium carbonate",
        "PRODUCT",
    ),
    # REGULATORY
    ("DOJ files antitrust lawsuit to block monopolistic market concentration", "REGULATORY"),
    (
        "Department of Justice launches antitrust inquiry into proposed semiconductor merger",
        "REGULATORY",
    ),
    ("SEC launches formal enforcement investigation into accounting irregularities", "REGULATORY"),
    (
        "Securities and Exchange Commission probes premature subscription revenue recognition",
        "REGULATORY",
    ),
    (
        "consumer financial protection agency levies record civil money penalty for "
        "deceptive practices",
        "REGULATORY",
    ),
    (
        "Federal Trade Commission files preliminary injunction to block corporate buyout",
        "REGULATORY",
    ),
    (
        "banking regulators issue cease-and-desist order for severe risk compliance deficiencies",
        "REGULATORY",
    ),
    # SUPPLY_CHAIN
    ("declares force majeure after fire damages primary blast furnace facility", "SUPPLY_CHAIN"),
    (
        "unexpected fire at primary rolling mill halted output indefinitely invoking force majeure",
        "SUPPLY_CHAIN",
    ),
    (
        "shares tumbled after the company halted output indefinitely at its "
        "main manufacturing plant",
        "SUPPLY_CHAIN",
    ),
    (
        "port dockworkers strike halts container freight shipping operations nationwide",
        "SUPPLY_CHAIN",
    ),
    (
        "critical port terminal bottleneck delays cargo container processing for "
        "manufacturing suppliers",
        "SUPPLY_CHAIN",
    ),
    ("semiconductor component shortages force automotive assembly line shutdowns", "SUPPLY_CHAIN"),
    (
        "freight logistics delays double container turnaround times at key regional cargo hubs",
        "SUPPLY_CHAIN",
    ),
    (
        "national freight rail strike averted as union ratifies wage agreement easing logistics",
        "SUPPLY_CHAIN",
    ),
    ("raw material export embargo cuts off essential lithium battery inputs", "SUPPLY_CHAIN"),
    # EARNINGS
    ("reports record quarterly earnings as net interest margin widens thirty bps", "EARNINGS"),
    (
        "slashes full year revenue guidance and profit targets due to rising operating costs",
        "EARNINGS",
    ),
    ("first quarter earnings per share beat consensus estimates by fifteen percent", "EARNINGS"),
    ("Meridian Financial profit tops estimates on stronger commercial lending yields", "EARNINGS"),
    (
        "operating profit drops sharply as operating margin compresses due to inventory discounts",
        "EARNINGS",
    ),
    ("quarterly net income surges fifty percent driven by commercial loan volume", "EARNINGS"),
    (
        "lowered second-half operating margin targets citing discounted inventory foot traffic",
        "EARNINGS",
    ),
    (
        "beats vehicle delivery expectations by twelve percent on battery factory efficiency ramp",
        "EARNINGS",
    ),
    (
        "firm fixed price contract awarded to modernize defense avionics countermeasure systems",
        "EARNINGS",
    ),
    # CYBER
    (
        "critical zero-day security flaw in enterprise gateway actively exploited by hackers",
        "CYBER",
    ),
    (
        "unpatched authentication bypass vulnerability actively exploited in enterprise firewall",
        "CYBER",
    ),
    ("ransomware attack compromises internal corporate databases and encrypted servers", "CYBER"),
    (
        "localized ransomware breach confirmed on legacy payment servers internal nodes encrypted",
        "CYBER",
    ),
    ("malicious unauthorized data breach exposes customer banking credentials", "CYBER"),
    ("distributed denial of service attacks knock online banking portals offline", "CYBER"),
    ("supply chain software infiltration compromises downstream client networks", "CYBER"),
    # OTHER
    ("board of directors schedules annual general meeting of shareholders proxy vote", "OTHER"),
    ("company updates routine corporate governance committee charter", "OTHER"),
    ("executive appointed to non-executive board seat at industry association", "OTHER"),
    ("regular quarterly dividend declared payable on standard record date", "OTHER"),
    ("routine investor relations presentation slides uploaded to corporate website", "OTHER"),
]


class EventClassifier:
    """TF-IDF and Logistic Regression event classifier with auditable abstention."""

    def __init__(
        self,
        model_path: Optional[Union[str, Path]] = None,
        confidence_threshold: float = 0.40,
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

        pipeline = Pipeline(
            [
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
            ]
        )
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
