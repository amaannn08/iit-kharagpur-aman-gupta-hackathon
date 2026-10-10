"""Module A: tactical sentiment-driven rebalancing of a mock S&P 100 index (PS Section 3).

Subscribes to the NLP engine's sentiment score. For each stock in the mock index:
  - positive sentiment increases its weight, negative sentiment decreases it (PS);
  - sentiment is a time-decayed exponential moving average of signal scores per ticker;
  - target weight = base x (1 + k x EMA), long-only, capped at 20% per name and 40% per
    sector, renormalized to sum to 1 (PRD Section 10).
Every rebalance is recorded with turnover = 0.5 x sum |w_new - w_old| and a reason per name.
This is a mock index for demonstration, not an S&P product.
"""

import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from sentinel.contracts.signals import RiskSignal

# 20 S&P 100 names with the best real-tweet coverage in the Kaggle stock-tweets data
DEFAULT_UNIVERSE: Dict[str, str] = {
    "AAPL": "Information Technology", "ADBE": "Information Technology",
    "CSCO": "Information Technology", "INTC": "Information Technology",
    "MSFT": "Information Technology", "AMZN": "Consumer Discretionary",
    "MCD": "Consumer Discretionary", "META": "Communication Services",
    "GOOGL": "Communication Services", "NFLX": "Communication Services",
    "CMCSA": "Communication Services", "DIS": "Communication Services",
    "JPM": "Financials", "C": "Financials", "BLK": "Financials", "MA": "Financials",
    "BA": "Industrials", "FDX": "Industrials", "COST": "Consumer Staples", "CVX": "Energy",
}  # fmt: skip


@dataclass
class RebalanceRecord:
    timestamp: str
    weights: Dict[str, float]
    sentiment_ema: Dict[str, float]
    turnover: float
    reasons: Dict[str, str]
    trigger_ticker: Optional[str] = None
    trigger_signal_id: Optional[str] = None


@dataclass
class IndexRebalancer:
    universe: Dict[str, str] = field(default_factory=lambda: dict(DEFAULT_UNIVERSE))
    k: float = 1.5  # weight sensitivity to sentiment
    alpha: float = 0.3  # EMA weight of a new signal
    halflife_days: float = 5.0  # sentiment decays toward neutral without new signals
    name_cap: float = 0.20
    sector_cap: float = 0.40

    def __post_init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        n = len(self.universe)
        self.base = {t: 1.0 / n for t in self.universe}
        self.ema: Dict[str, float] = {t: 0.0 for t in self.universe}
        self.last_seen: Dict[str, Optional[datetime]] = {t: None for t in self.universe}
        self.weights = dict(self.base)
        self.history: List[RebalanceRecord] = [
            RebalanceRecord(
                "initial",
                dict(self.base),
                dict(self.ema),
                0.0,
                {t: "base weight" for t in self.universe},
            )  # fmt: skip
        ]

    def _decay(self, ticker: str, now: Optional[datetime]) -> None:
        last = self.last_seen[ticker]
        if now is not None and last is not None and now > last:
            days = (now - last).total_seconds() / 86400
            self.ema[ticker] *= math.exp(-math.log(2) * days / self.halflife_days)

    def _target_weights(self) -> Dict[str, float]:
        raw = {t: max(0.0, self.base[t] * (1 + self.k * self.ema[t])) for t in self.universe}
        total = sum(raw.values()) or 1.0
        w = {t: v / total for t, v in raw.items()}
        for _ in range(50):  # iterative capping with redistribution to uncapped names
            capped = False
            for t in w:
                if w[t] > self.name_cap + 1e-12:
                    w[t], capped = self.name_cap, True
            for sector in set(self.universe.values()):
                names = [t for t in w if self.universe[t] == sector]
                s = sum(w[t] for t in names)
                if s > self.sector_cap + 1e-12:
                    for t in names:
                        w[t] *= self.sector_cap / s
                    capped = True
            total = sum(w.values())
            free = [t for t in w if w[t] < self.name_cap - 1e-12]
            if abs(total - 1.0) > 1e-12 and free:
                scale_free = (1.0 - sum(w[t] for t in w if t not in free)) / sum(w[t] for t in free)
                for t in free:
                    w[t] *= scale_free
            if not capped and abs(sum(w.values()) - 1.0) < 1e-9:
                break
        total = sum(w.values())
        return {t: round(v / total, 6) for t, v in w.items()}

    def on_signal(self, signal: RiskSignal) -> Optional[RebalanceRecord]:
        """Update the ticker's sentiment EMA from an eligible signal and rebalance."""
        ticker = signal.entity.ticker
        if ticker not in self.universe:
            return None
        blocked = {"DUPLICATE_TEXT_SUPPRESSED", "SOCIAL_SPAM", "NO_FINANCIAL_CONTEXT"}
        if blocked & set(signal.action_block_reasons):
            return None
        now = signal.simulated_at or signal.published_at
        return self.update(ticker, signal.sentiment.score, now, signal.signal_id)

    def update(
        self,
        ticker: str,
        score: float,
        now: Optional[datetime] = None,
        signal_id: Optional[str] = None,
    ) -> Optional[RebalanceRecord]:
        """Fold one sentiment observation into the ticker's EMA and rebalance the index."""
        if ticker not in self.universe:
            return None
        if now is not None and now.tzinfo is not None:
            now = now.replace(tzinfo=None)
        self._decay(ticker, now)
        self.ema[ticker] = (1 - self.alpha) * self.ema[ticker] + self.alpha * score
        self.last_seen[ticker] = now
        new = self._target_weights()
        turnover = round(0.5 * sum(abs(new[t] - self.weights[t]) for t in new), 6)
        reasons = {}
        for t, w in new.items():
            e = self.ema[t]
            if w >= self.name_cap - 1e-9 and e > 0:
                reasons[t] = f"capped at {self.name_cap:.0%} (sentiment {e:+.2f})"
            elif e > 0.02:
                reasons[t] = f"increase: positive sentiment {e:+.2f}"
            elif e < -0.02:
                reasons[t] = f"decrease: negative sentiment {e:+.2f}"
            else:
                reasons[t] = "neutral: base weight"
        self.weights = new
        record = RebalanceRecord(
            timestamp=(now.isoformat() if now else datetime.utcnow().isoformat()),
            weights=new,
            sentiment_ema={t: round(v, 4) for t, v in self.ema.items()},
            turnover=turnover,
            reasons=reasons,
            trigger_ticker=ticker,
            trigger_signal_id=signal_id,
        )
        self.history.append(record)
        return record
