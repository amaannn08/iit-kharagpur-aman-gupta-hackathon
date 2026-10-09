"""Sentiment analysis engine with local FinBERT loader and fallback (PRD Section 7.2)."""

import logging
from pathlib import Path
from typing import Dict, Optional, Union

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

    def __init__(self, model_dir: Optional[Union[str, Path]] = None) -> None:
        self.model_dir = Path(model_dir) if model_dir else Path(".runtime/models/finbert")
        self.degraded_mode: bool = True
        self.model_version: str = "lexicon_fallback_v1"
        self._model = None
        self._tokenizer = None
        self._id2label: Dict[int, str] = {}

        self._try_load_local_finbert()

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
        if not self.degraded_mode and self._model is not None and self._tokenizer is not None:
            return self._analyze_finbert(text)
        return self._analyze_lexicon(text)

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
