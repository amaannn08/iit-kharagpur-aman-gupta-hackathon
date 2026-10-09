"""Sentiment analysis engine (PRD Section 7.2).

Backends, in priority order:
  1. Local FinBERT weights in .runtime/models/finbert (optional tier 2, `nlp` extra)
  2. models/sentiment_v2.joblib: TF-IDF + logistic regression trained on real labeled financial
     tweets (scripts/models/train_sentiment.py); 0.77 macro-F1 on 2,388 held-out tweets
  3. Finance lexicon (degraded mode, reported via degraded_mode / model_version)

Score = P(positive) - P(negative), bounded to [-1, 1]; probabilities sum to 1.
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, Optional, Tuple, Union

import joblib

from sentinel.config import settings
from sentinel.contracts.signals import SentimentOutput, SentimentProbabilities

logger = logging.getLogger(__name__)

# Curated finance domain polar lexicon for transparent fallback
FIN_NEGATIVE_WORDS = {
    "default",
    "downgrade",
    "downgraded",
    "loss",
    "losses",
    "drop",
    "dropped",
    "plunge",
    "plunged",
    "bankruptcy",
    "bankrupt",
    "insolvent",
    "insolvency",
    "distress",
    "fail",
    "failed",
    "failure",
    "crisis",
    "fall",
    "fell",
    "slump",
    "slumped",
    "warning",
    "warns",
    "deficit",
    "selloff",
    "collapse",
    "collapsed",
    "liquidation",
    "outflow",
    "outflows",
    "curb",
    "probe",
    "fraud",
    "breach",
    "sanction",
    "decline",
    "declined",
    "inflation",
    "hike",
    "hiking",
    "combat",
    "stubborn",
    "tightening",
    "catastrophic",
    "fire",
    "majeure",
    "lawsuit",
    "antitrust",
    "monopolization",
    "ransomware",
    "unpatched",
    "flaw",
    "exploit",
    "exploited",
    "uncertainty",
}

FIN_POSITIVE_WORDS = {
    "upgrade",
    "upgraded",
    "gain",
    "gains",
    "growth",
    "grow",
    "surge",
    "surged",
    "profit",
    "profitable",
    "beat",
    "beats",
    "record",
    "rally",
    "rallied",
    "outperform",
    "strong",
    "rebound",
    "rebounded",
    "dividend",
    "revenue",
    "rise",
    "rose",
    "jump",
    "jumped",
    "recovery",
    "expansion",
    "soar",
    "soared",
    "boost",
    "boosted",
    "approval",
    "denies",
    "denied",
    "operational",
    "breakthrough",
    "priority",
    "wins",
    "confirms",
}


class FinBERTSentimentAnalyzer:
    """Financial sentiment analyzer that loads local FinBERT or transparently falls back."""

    def __init__(
        self,
        model_dir: Optional[Union[str, Path]] = None,
        tfidf_path: Optional[Union[str, Path]] = None,
    ) -> None:
        self.model_dir = Path(model_dir) if model_dir else Path(".runtime/models/finbert")
        self.tfidf_path = (
            Path(tfidf_path) if tfidf_path else settings.base_dir / "models" / "sentiment_v2.joblib"
        )
        self.degraded_mode: bool = True
        self.model_version: str = "lexicon_fallback_v1"
        self.backend: str = "lexicon"
        self._model = None
        self._tokenizer = None
        self._tfidf = None
        self._id2label: Dict[int, str] = {}

        self._try_load_local_finbert()
        if self.backend == "lexicon":
            self._try_load_tfidf()

    def _try_load_tfidf(self) -> None:
        """Tier 1: committed TF-IDF model trained on real labeled data."""
        if not self.tfidf_path.exists():
            logger.info("No %s; sentiment runs in degraded lexicon mode.", self.tfidf_path)
            return
        try:
            self._tfidf = joblib.load(self.tfidf_path)
            card_path = self.tfidf_path.with_suffix(".card.json")
            card = json.loads(card_path.read_text()) if card_path.exists() else {}
            self.model_version = f"sentiment_v2:{card.get('model_sha256', 'unknown')[:12]}"
            self.backend = "tfidf"
            self.degraded_mode = False
        except Exception as exc:
            logger.warning("Failed loading %s (%s); using lexicon.", self.tfidf_path, exc)

    def _try_load_local_finbert(self) -> None:
        """Attempt to load local checkpoint with local_files_only=True."""
        if not (self.model_dir.exists() and (self.model_dir / "config.json").exists()):
            logger.info(
                "Local FinBERT weights not found at %s. Using lexicon fallback.",
                self.model_dir,
            )
            self.degraded_mode = True
            self.model_version = "lexicon_fallback_v1"
            return

        try:
            from transformers import AutoModelForSequenceClassification, AutoTokenizer

            self._tokenizer = AutoTokenizer.from_pretrained(
                str(self.model_dir),
                local_files_only=True,
            )
            self._model = AutoModelForSequenceClassification.from_pretrained(
                str(self.model_dir),
                local_files_only=True,
            )
            self._model.eval()

            # Read actual label mapping from config - do not assume index order
            raw_id2label = getattr(self._model.config, "id2label", None)
            if raw_id2label:
                self._id2label = {int(k): str(v).lower() for k, v in raw_id2label.items()}
            else:
                self._id2label = {0: "positive", 1: "negative", 2: "neutral"}

            self.degraded_mode = False
            self.backend = "finbert"
            self.model_version = f"ProsusAI/finbert-local-{self._model.config.transformers_version}"
            logger.info("Successfully loaded offline FinBERT from %s", self.model_dir)
        except Exception as exc:
            logger.warning("Failed loading local FinBERT (%s). Operating in degraded mode.", exc)
            self.degraded_mode = True
            self.model_version = "lexicon_fallback_v1"

    def analyze(self, text: str) -> SentimentOutput:
        """Compute sentiment output.

        Score = P(positive) - P(negative) bounded to [-1.0, 1.0].
        Probabilities sum to 1.0.
        """
        if self.backend == "finbert":
            return self._analyze_finbert(text)
        if self.backend == "tfidf":
            return self._analyze_tfidf(text)
        return self._analyze_lexicon(text)

    def _analyze_tfidf(self, text: str) -> SentimentOutput:
        cleaned = re.sub(r"https?://\S+|@\w+", " ", text).strip()
        probs = dict(zip(self._tfidf.classes_, self._tfidf.predict_proba([cleaned])[0]))
        p_pos = round(float(probs.get("positive", 0.0)), 4)
        p_neg = round(float(probs.get("negative", 0.0)), 4)
        p_neu = round(1.0 - p_pos - p_neg, 4)
        label = max(
            ("positive", p_pos), ("negative", p_neg), ("neutral", p_neu), key=lambda x: x[1]
        )[0]
        return SentimentOutput(
            score=max(-1.0, min(1.0, round(p_pos - p_neg, 4))),
            label=label,
            probabilities=SentimentProbabilities(positive=p_pos, negative=p_neg, neutral=p_neu),
        )

    def _analyze_finbert(self, text: str) -> SentimentOutput:
        import torch

        inputs = self._tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=512,
            padding=True,
        )
        with torch.no_grad():
            outputs = self._model(**inputs)
            logits = outputs.logits
            probs = torch.softmax(logits, dim=1).squeeze().tolist()

        prob_map: Dict[str, float] = {"positive": 0.0, "negative": 0.0, "neutral": 0.0}
        for idx, p in enumerate(probs):
            label = self._id2label.get(idx, "neutral")
            if label in prob_map:
                prob_map[label] = float(p)

        # Normalize sum to exactly 1.0
        total = sum(prob_map.values())
        if total > 0:
            p_pos = round(prob_map["positive"] / total, 4)
            p_neg = round(prob_map["negative"] / total, 4)
            p_neu = round(1.0 - p_pos - p_neg, 4)
        else:
            p_pos, p_neg, p_neu = 0.0, 0.0, 1.0

        score = max(-1.0, min(1.0, round(p_pos - p_neg, 4)))
        dominant_label = "neutral"
        if p_pos > p_neg and p_pos > p_neu:
            dominant_label = "positive"
        elif p_neg > p_pos and p_neg > p_neu:
            dominant_label = "negative"

        return SentimentOutput(
            score=score,
            label=dominant_label,
            probabilities=SentimentProbabilities(
                positive=p_pos,
                negative=p_neg,
                neutral=p_neu,
            ),
        )

    def _analyze_lexicon(self, text: str) -> SentimentOutput:
        """Transparent, deterministic rule-based sentiment fallback with negation and context."""
        import re

        lower_raw = text.lower()
        words = re.findall(r"\b[a-zA-Z]+\b", lower_raw)

        # Contextual financial multi-word phrases
        pos_phrases = (
            "rate cut",
            "cuts rate",
            "cuts rates",
            "cutting rate",
            "cutting rates",
            "rate reduction",
            "emergency easing",
            "monetary easing",
            "policy easing",
            "denies rumors",
            "denied rumors",
            "tops estimates",
            "beats estimates",
            "beat estimates",
            "crushed expectations",
            "strong lending",
            "rebounded sharply",
        )
        neg_phrases = (
            "rate hike",
            "hikes rate",
            "hikes rates",
            "hiking rate",
            "hiking rates",
            "interest rate hike",
            "dividend cut",
            "job cuts",
            "cuts jobs",
            "spending cuts",
            "budget cut",
            "halted output",
            "skipped interest",
            "missed payment",
            "missed scheduled",
            "monetary tightening",
            "credit default",
            "covenant breach",
        )

        pos_phrase_hits = sum(1.0 for p in pos_phrases if p in lower_raw)
        neg_phrase_hits = sum(1.0 for p in neg_phrases if p in lower_raw)

        negation_tokens = {
            "no",
            "not",
            "without",
            "never",
            "denies",
            "denied",
            "rejects",
            "rejected",
        }

        pos_hits = pos_phrase_hits
        neg_hits = neg_phrase_hits

        for i, w in enumerate(words):
            is_negated = any(words[j] in negation_tokens for j in range(max(0, i - 3), i))
            if w in FIN_NEGATIVE_WORDS:
                if is_negated:
                    pos_hits += 0.5  # Negated negative implies mitigating/positive
                else:
                    neg_hits += 1.0
            elif w in FIN_POSITIVE_WORDS:
                if is_negated:
                    neg_hits += 0.5
                else:
                    pos_hits += 1.0

        if neg_hits > pos_hits + 0.3:
            diff = neg_hits - pos_hits
            neg_weight = min(0.90, 0.45 + 0.10 * diff)
            pos_weight = max(0.05, 0.15 - 0.05 * diff)
            neu_weight = round(1.0 - neg_weight - pos_weight, 4)
            score = max(-1.0, min(1.0, round(pos_weight - neg_weight, 4)))
            dominant_label = "negative"
        elif pos_hits > neg_hits + 0.3:
            diff = pos_hits - neg_hits
            pos_weight = min(0.90, 0.45 + 0.10 * diff)
            neg_weight = max(0.05, 0.15 - 0.05 * diff)
            neu_weight = round(1.0 - pos_weight - neg_weight, 4)
            score = max(-1.0, min(1.0, round(pos_weight - neg_weight, 4)))
            dominant_label = "positive"
        else:
            pos_weight, neg_weight, neu_weight = 0.10, 0.10, 0.80
            score = 0.0
            dominant_label = "neutral"

        return SentimentOutput(
            score=score,
            label=dominant_label,
            probabilities=SentimentProbabilities(
                positive=round(pos_weight, 4),
                negative=round(neg_weight, 4),
                neutral=round(neu_weight, 4),
            ),
        )


# Macro indicators whose *rise* is bad news (and fall good news) for credit and rates books.
# Text models trained on stock chatter read "claims rose sharply" as positive momentum.
_BAD_WHEN_UP = r"(jobless claims|unemployment( rate)?|inflation|cpi|ppi|core prices|bond yields?|"
_BAD_WHEN_UP += r"treasury yields?|default rates?|delinquenc\w+|layoffs?|jobless)"
_UP = r"(ris\w*|rose|jump\w*|surg\w*|climb\w*|soar\w*|spik\w*|accelerat\w*|increas\w*|higher)"
_DOWN = r"(fall\w*|fell|drop\w*|declin\w*|eas\w*|cool\w*|slow\w*|decreas\w*|lower|retreat\w*)"
_GAP = r"\W+(?:[\w.%-]+\W+){0,4}"
MACRO_UP = re.compile(rf"\b{_BAD_WHEN_UP}{_GAP}{_UP}\b", re.I)
MACRO_DOWN = re.compile(rf"\b{_BAD_WHEN_UP}{_GAP}{_DOWN}\b", re.I)


_RATES = r"(?:interest |policy |benchmark |key |repo |federal funds |fed funds )?rates?"
EASING = re.compile(
    rf"\b(?:(?:cut|cuts|cutting|lower|lowers|lowered|lowering|reduce[sd]?|reducing|slash\w*)\W+"
    rf"(?:\w+\W+){{0,3}}{_RATES}|rate cuts?|monetary easing|policy easing|quantitative easing)\b",
    re.I,
)
TIGHTENING = re.compile(
    rf"\b(?:(?:raise[sd]?|raising|hike[sd]?|hiking|increase[sd]?|increasing|lift\w*)\W+"
    rf"(?:\w+\W+){{0,3}}{_RATES}|rate hikes?|rate increases?|monetary tightening|policy tightening)\b",
    re.I,
)


def policy_direction(text: str) -> Tuple[str, Optional[re.Match]]:
    """'easing' / 'tightening' / 'none' for central-bank policy-rate moves, with evidence."""
    for label, pattern in (("easing", EASING), ("tightening", TIGHTENING)):
        m = pattern.search(text)
        if m:
            return label, m
    return "none", None


def macro_polarity(text: str) -> Optional[Tuple[float, re.Match]]:
    """Direction of a MACRO headline for a credit/rates book, with the evidence match.

    Policy easing and falling bad-when-up indicators are +1; tightening and rising ones -1.
    """
    direction, m = policy_direction(text)
    if m:
        return (1.0 if direction == "easing" else -1.0), m
    for pattern, sign in ((MACRO_UP, -1.0), (MACRO_DOWN, 1.0)):
        m = pattern.search(text)
        if m:
            return sign, m
    return None


def apply_macro_polarity(sentiment: SentimentOutput, text: str) -> Optional[re.Match]:
    """Blend a MACRO signal's probabilities 50/50 toward the indicator direction.

    Keeps the contract score = P(positive) - P(negative); returns the evidence match.
    """
    hit = macro_polarity(text)
    if hit is None:
        return None
    sign, m = hit
    p = sentiment.probabilities
    pos = 0.5 * p.positive + (0.5 if sign > 0 else 0.0)
    neg = 0.5 * p.negative + (0.5 if sign < 0 else 0.0)
    neu = 1.0 - pos - neg
    sentiment.probabilities = SentimentProbabilities(
        positive=round(pos, 4), negative=round(neg, 4), neutral=round(neu, 4)
    )
    sentiment.score = max(-1.0, min(1.0, round(pos - neg, 4)))
    sentiment.label = max(
        (("positive", pos), ("negative", neg), ("neutral", neu)), key=lambda x: x[1]
    )[0]
    return m
