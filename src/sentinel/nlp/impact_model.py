"""Market-calibrated impact model (PRD Section 7.4, plan WS5).

The additive rubric explains a score, but on 1,402 real 2023 article-ticker events it had no
relationship with the next-day market reaction (Spearman -0.04). This model is trained by
scripts/models/train_impact.py to predict the size of the standardized abnormal return
|z| = |r - beta * r_SPY| / sigma_30d on the reaction day, and maps its prediction onto 1-10 by
the deciles of out-of-fold predictions (models/impact_v2.joblib + card).

Features are computed identically at training and inference time by ``impact_features``.
"""

import json
import logging
import math
import re
from pathlib import Path
from typing import Dict, Optional, Tuple, Union

import joblib
import numpy as np
import pandas as pd

from sentinel.config import settings
from sentinel.contracts.signals import EventOutput

logger = logging.getLogger(__name__)

EVENT_CLASSES = [
    "CREDIT", "CYBER", "EARNINGS", "GEOPOLITICAL", "MACRO", "M_AND_A", "OTHER", "PRODUCT",
    "REGULATORY", "SUPPLY_CHAIN",
]  # fmt: skip

CATASTROPHIC = re.compile(
    r"\b(default(s|ed)?|bankrupt(cy)?|chapter 11|insolven(t|cy)|force majeure|bank run|"
    r"liquidation|ransomware|zero-day|covenant breach|delist(ed|ing)?|fraud)\b",
    re.I,
)
MATERIAL = re.compile(
    r"\b(downgrade[ds]?|probe|investigation|lawsuit|recall(s|ed)?|guidance cut|cuts? guidance|"
    r"misse[sd]|plunge[sd]?|halt(s|ed)?|suspend(s|ed)?|layoffs?|subpoena|antitrust|warning)\b",
    re.I,
)


def impact_features(
    event: EventOutput,
    sentiment_score: float,
    n_entities: int,
    text: str,
    is_social: bool,
) -> Dict[str, float]:
    feats = {f"p_{c}": float(event.probabilities.get(c, 0.0)) for c in EVENT_CLASSES}
    feats.update(
        sentiment=float(sentiment_score),
        abs_sentiment=abs(float(sentiment_score)),
        n_entities=float(n_entities),
        log_length=math.log1p(len(text)),
        is_social=float(is_social),
        catastrophic_language=float(bool(CATASTROPHIC.search(text))),
        material_language=float(bool(MATERIAL.search(text))),
    )
    return feats


class LearnedImpactModel:
    """Loads models/impact_v2.joblib; predicts expected |abnormal z| and its 1-10 decile."""

    def __init__(self, path: Optional[Union[str, Path]] = None) -> None:
        self.path = Path(path) if path else settings.base_dir / "models" / "impact_v2.joblib"
        self.available = False
        self.version = "unavailable"
        if not self.path.exists():
            return
        try:
            bundle = joblib.load(self.path)
            self._model = bundle["model"]
            self.features = bundle["features"]
            self.decile_edges = np.asarray(bundle["decile_edges"])
            card_path = self.path.with_suffix(".card.json")
            card = json.loads(card_path.read_text()) if card_path.exists() else {}
            self.version = f"impact_v2:{card.get('model_sha256', 'unknown')[:12]}"
            self.available = True
        except Exception as exc:
            logger.warning("Could not load impact model %s (%s); rubric only.", self.path, exc)

    def score(self, feats: Dict[str, float]) -> Tuple[float, int]:
        row = pd.DataFrame([feats])[self.features]
        pred = float(self._model.predict(row)[0])
        return pred, int(np.searchsorted(self.decile_edges, pred, side="right") + 1)
