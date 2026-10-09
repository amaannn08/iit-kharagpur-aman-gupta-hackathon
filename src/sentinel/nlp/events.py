"""Event classification engine (PRD Section 7.3).

Primary model: models/event_v2.joblib, trained by scripts/models/train_event.py on committed
real labeled data (HF twitter-financial-news topic, SEC 8-K item statements, weak-labeled real
headlines). Its card (models/event_v2.card.json) carries the abstention threshold chosen on a
dev split and the held-out metrics.

After classification, domain gates require visible evidence for classes whose training labels
are broader than the PS definition (e.g. the "Politics" topic is not geopolitical risk).
If the model artifact is missing, a TF-IDF baseline is fitted on data/train/synthetic_seeds.csv
and the classifier reports degraded_mode=True.
"""

import csv
import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from sentinel.config import settings
from sentinel.contracts.signals import EventOutput, EvidenceSpan

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

# zeroshot/twitter-financial-news-topic label id -> PS event class (others -> OTHER)
TOPIC_TO_PS_CLASS: Dict[int, str] = {
    1: "MACRO",  # Fed | Central Banks
    14: "MACRO",  # Macro
    3: "CREDIT",  # Treasuries | Corporate Debt
    5: "EARNINGS",  # Earnings
    13: "M_AND_A",  # M&A | Investments
    12: "REGULATORY",  # Legal | Regulation
    16: "GEOPOLITICAL",  # Politics (gated below: not all politics is geopolitical risk)
    2: "PRODUCT",  # Company | Product News (gated below: not all company news is a launch)
}

# A label survives only if the text shows class evidence (measured on real Polygon/GDELT news:
# actionable false positives fell from 14 to 6 and from 52 to 2).
GATES: Dict[str, re.Pattern] = {
    "MACRO": re.compile(
        r"\b(fed|federal reserve|fomc|central bank|interest rates?|rate (hike|cut)s?|inflation|"
        r"cpi|ppi|gdp|recession|jobless|payrolls?|unemployment|treasury|treasuries|yields?|"
        r"monetary|fiscal|tariffs?|trade deficit|imf|world bank|ecb|boe|boj|rbi|pboc|"
        r"currency|devaluation|basis points?|bps)\b",
        re.I,
    ),
    "GEOPOLITICAL": re.compile(
        r"\b(sanctions?|tariffs?|export (ban|controls?)|embargo|war|invasion|military|missiles?|"
        r"troops|conflict|ceasefire|nato|opec|strait|border|nationali[sz]\w*|trade (war|deal|"
        r"talks|tensions)|geopolitic\w*|coup|blockade|annex\w*)\b",
        re.I,
    ),
    "PRODUCT": re.compile(
        r"\b(launch\w*|unveil\w*|introduc\w*|releas\w*|approv\w*|recalls?|recalled|debut\w*|"
        r"rolls? out|new (product|model|chip|drug|device|service|phone|vehicle)|fda|clinical trial)\b",
        re.I,
    ),
}
MACRO_GATE_WINDOW = 200  # macro evidence must appear in the headline-sized prefix

# Corporate credit-distress language. The topic dataset files most bankruptcies/defaults under
# "Company | Product News"; under the PS taxonomy they are Credit Events.
CREDIT_DISTRESS = re.compile(
    r"\b(default(s|ed)? on|in default|bankrupt(cy|cies)?|chapter (11|7)|insolven(t|cy)|"
    r"receivership|downgrade[sd]? .{0,30}\bjunk|junk (status|territory)|"
    r"(credit|debt) rating (cut|downgrade)|cuts? .{0,30}(credit|debt) rating|"
    r"missed (a |an |its )?(\w+ )?(interest|coupon|debt|bond|loan) payments?|debt restructuring|"
    r"restructur\w+ (of )?(its )?debt|covenant (breach|waiver)|liquidity crisis|distressed debt|"
    r"creditors? committee)\b",
    re.I,
)


# Earnings language. The topic dataset files earnings-driven price reactions under "Stock
# Movement" / "Analyst Update" (-> OTHER), so "cuts its full-year profit guidance" was learned
# as a non-event. Only refines labels that would otherwise be OTHER.
EARNINGS_LANGUAGE = re.compile(
    r"\b(earnings|eps|quarterly (results|profit|loss|revenue|sales)|"
    r"q[1-4] (results|earnings|revenue|profit|sales)|"
    r"(raises|raised|cuts|cut|lowers|lowered|slashes|withdraws|reaffirms|beats|beat|misses|missed|"
    r"tops|topped) (its |their )?(full[- ]year |annual |quarterly |sales |revenue |profit )?"
    r"(guidance|forecast|outlook|estimates|expectations)|"
    r"profit (warning|falls|fell|drops|dropped|rises|rose|jumps|jumped|plunges|surges)|"
    r"revenue (beats|misses|falls|fell|rises|rose|tops|jumps))\b",
    re.I,
)


def ps_aligned_label(topic_label: int, text: str) -> str:
    """Map a twitter-financial-news topic label onto the PS event taxonomy.

    Deterministic and shared by training and evaluation. Two refinements of the topic taxonomy:
    credit-distress language -> CREDIT (a bankruptcy is a PS Credit Event even when the dataset
    files it under company news), and explicit earnings language on an otherwise-OTHER topic ->
    EARNINGS. Evidence gates are applied at inference only.
    """
    if CREDIT_DISTRESS.search(text):
        return "CREDIT"
    label = TOPIC_TO_PS_CLASS.get(int(topic_label), "OTHER")
    if label == "OTHER" and EARNINGS_LANGUAGE.search(text):
        return "EARNINGS"
    return label


def clean_for_classifier(text: str) -> str:
    """Strip URLs and @handles; identical preprocessing at training and inference time."""
    return re.sub(r"https?://\S+|@\w+", " ", str(text)).strip()


def apply_gate(label: str, text: str) -> Tuple[str, List[EvidenceSpan]]:
    gate = GATES.get(label)
    if gate is None:
        return label, []
    window = text[:MACRO_GATE_WINDOW] if label == "MACRO" else text
    m = gate.search(window)
    if not m:
        return "OTHER", []
    return label, [EvidenceSpan(start=m.start(), end=m.end(), text=m.group())]


def _model_dir() -> Path:
    return settings.base_dir / "models"


def _load_seed_corpus() -> List[Tuple[str, str]]:
    path = settings.data_dir / "train" / "synthetic_seeds.csv"
    with open(path, newline="", encoding="utf-8") as f:
        return [(r["text"], r["label"]) for r in csv.DictReader(f)]


class EventClassifier:
    """Calibrated event classifier with auditable abstention and evidence gates."""

    def __init__(
        self,
        model_path: Optional[Union[str, Path]] = None,
        confidence_threshold: Optional[float] = None,
    ) -> None:
        self.model_path = Path(model_path) if model_path else _model_dir() / "event_v2.joblib"
        self.pipeline: Optional[Pipeline] = None
        self.degraded_mode = False
        self.model_version = "event_v2"
        card_threshold = self._load()
        if confidence_threshold is not None:
            self.confidence_threshold = confidence_threshold
        else:
            self.confidence_threshold = card_threshold

    def _load(self) -> float:
        """Load the trained artifact; return the abstention threshold from its card."""
        if self.model_path.exists():
            try:
                self.pipeline = joblib.load(self.model_path)
                card_path = self.model_path.with_suffix(".card.json")
                card = json.loads(card_path.read_text()) if card_path.exists() else {}
                self.model_version = f"event_v2:{card.get('model_sha256', 'unknown')[:12]}"
                logger.info("Loaded event classifier %s", self.model_path)
                return float(card.get("abstain_threshold", settings.action_confidence_threshold))
            except Exception as exc:
                logger.warning("Could not load %s (%s). Using seed baseline.", self.model_path, exc)
        self._train_seed_baseline()
        return 0.40

    def _train_seed_baseline(self) -> None:
        """Degraded fallback: fit TF-IDF + LR on the synthetic seed corpus."""
        corpus = _load_seed_corpus()
        pipeline = Pipeline(
            [
                ("tfidf", TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)),
                (
                    "clf",
                    LogisticRegression(
                        C=25.0, class_weight="balanced", max_iter=500, random_state=42
                    ),
                ),
            ]
        )
        pipeline.fit([t for t, _ in corpus], [y for _, y in corpus])
        self.pipeline = pipeline
        self.degraded_mode = True
        self.model_version = "seed_baseline_degraded"

    def save_model(self, path: Optional[Union[str, Path]] = None) -> Path:
        """Persist the current pipeline (training scripts also write a model card)."""
        target = Path(path) if path else self.model_path
        target.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.pipeline, target, compress=3)
        return target

    def predict(self, text: str) -> EventOutput:
        """Predict an event class; abstain to OTHER below threshold or without gate evidence."""
        if self.pipeline is None:
            return EventOutput(label="OTHER", confidence=0.0, abstained=True)

        cleaned = clean_for_classifier(text)
        probs = self.pipeline.predict_proba([cleaned])[0]
        best = int(probs.argmax())
        top_label = str(self.pipeline.classes_[best])
        top_conf = round(float(probs[best]), 4)
        dist = {str(c): round(float(p), 4) for c, p in zip(self.pipeline.classes_, probs)}

        if top_conf < self.confidence_threshold or top_label == "OTHER":
            return EventOutput(
                label="OTHER", confidence=top_conf, abstained=True, probabilities=dist
            )

        gated_label, evidence = apply_gate(top_label, text)
        if gated_label == "OTHER":
            return EventOutput(
                label="OTHER", confidence=top_conf, abstained=True, probabilities=dist
            )
        return EventOutput(
            label=top_label,
            confidence=top_conf,
            abstained=False,
            evidence=evidence,
            probabilities=dist,
        )
