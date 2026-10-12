"""Early Warning System (EWS) Watchlist for institutional credit.

Institutional lenders and commercial banks use Early Warning Systems
to detect obligor credit deterioration months before formal default or missed payments.

This module models an institutional EWS Watchlist for wholesale obligors:
  - Aggregates recent risk signals, developing story intensity, and sentiment drift
  - Incorporates obligor baseline credit metrics (rating, baseline PD, leverage tier)
  - Computes composite EWS score (0 to 100) and triggers:
      GREEN  (0 - 39):  Routine performance, quarterly review
      AMBER  (40 - 64): Emerging credit pressure, enhanced monitoring, freeze credit limit
      RED    (65 - 100): High default / downgrade risk, IFRS 9 Stage 2 SICR trigger
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sentinel.stress.portfolio import WholesalePortfolio
from sentinel.stress.story_trigger import StoryTracker


@dataclass
class EWSWatchlistItem:
    """Early Warning System record for a single wholesale obligor."""

    entity_id: str
    counterparty_name: str
    sector: str
    rating: str
    baseline_pd: float
    total_funded_exposure_usd: float
    ews_score: int  # 0 to 100
    status: str     # GREEN, AMBER, RED
    story_intensity: float
    active_story_id: Optional[str]
    recent_signals_count: int
    sentiment_score: float
    triggers: List[str]
    recommended_action: str
    updated_at: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "counterparty_name": self.counterparty_name,
            "sector": self.sector,
            "rating": self.rating,
            "baseline_pd": round(self.baseline_pd, 4),
            "total_funded_exposure_usd": round(self.total_funded_exposure_usd, 2),
            "ews_score": self.ews_score,
            "status": self.status,
            "story_intensity": round(self.story_intensity, 2),
            "active_story_id": self.active_story_id,
            "recent_signals_count": self.recent_signals_count,
            "sentiment_score": round(self.sentiment_score, 3),
            "triggers": self.triggers,
            "recommended_action": self.recommended_action,
            "updated_at": self.updated_at,
        }


class EarlyWarningSystem:
    """Evaluates wholesale portfolio obligors against early-warning credit risk rubric."""

    def __init__(self, portfolio: WholesalePortfolio) -> None:
        self.portfolio = portfolio

    def generate_watchlist(
        self,
        story_tracker: Optional[StoryTracker] = None,
        as_of: Optional[datetime] = None,
    ) -> List[EWSWatchlistItem]:
        """Generate full EWS watchlist for all distinct obligors in the portfolio."""
        now_ts = (as_of or datetime.now(timezone.utc)).isoformat()
        obligors: Dict[str, Dict[str, Any]] = {}

        # Collect exposure and ratings per entity
        for p in self.portfolio.loans:
            ent = p.entity_id
            if ent not in obligors:
                obligors[ent] = {
                    "counterparty_name": p.counterparty_name,
                    "sector": p.sector or "Unknown",
                    "rating": p.rating,
                    "baseline_pd": p.baseline_pd,
                    "exposure": 0.0,
                }
            obligors[ent]["exposure"] += p.ead

        for p in self.portfolio.bonds:
            ent = p.entity_id
            base_pd = getattr(p, "baseline_pd", 0.008)
            if ent not in obligors:
                obligors[ent] = {
                    "counterparty_name": p.counterparty_name,
                    "sector": p.sector or "Unknown",
                    "rating": p.rating,
                    "baseline_pd": base_pd,
                    "exposure": 0.0,
                }
            obligors[ent]["exposure"] += p.market_value

        # Retrieve active stories per entity if story_tracker is provided
        active_stories_by_ticker: Dict[str, Dict[str, Any]] = {}
        if story_tracker is not None:
            for s in story_tracker.get_active_stories():
                t = s.get("entity_ticker")
                if t:
                    active_stories_by_ticker[t] = s

        items: List[EWSWatchlistItem] = []

        for ent, info in obligors.items():
            if ent in ("TREASURY", "MACRO"):
                continue

            story = active_stories_by_ticker.get(ent)
            story_intensity = story.get("intensity", 1.0) if story else 1.0
            active_story_id = story.get("story_id") if story else None
            article_count = story.get("article_count", 0) if story else 0
            sentiment = story.get("avg_sentiment", 0.0) if story else 0.0

            # Base score derived from rating / credit risk
            # AAA/AA: 10, A: 20, BBB: 35, BB/B: 50
            rating = info["rating"].upper()
            if "AAA" in rating or "AA" in rating:
                base_score = 10
            elif "A" in rating:
                base_score = 20
            elif "BBB" in rating:
                base_score = 35
            else:
                base_score = 50

            triggers: List[str] = []

            # Scoring increment from news / story intensity
            story_score = 0
            if story_intensity >= 8.0:
                story_score = 40
                triggers.append(f"Severe story intensity ({story_intensity:.1f}/15) on {story.get('event_class', 'CREDIT')}")
            elif story_intensity >= 6.0:
                story_score = 25
                triggers.append(f"Elevated story velocity ({story.get('velocity_hourly', 0):.1f} art/h)")
            elif story_intensity >= 4.0:
                story_score = 10

            # Negative sentiment penalty
            sent_score = 0
            if sentiment < -0.4:
                sent_score = 20
                triggers.append(f"Negative sentiment surge ({sentiment:.2f})")
            elif sentiment < -0.15:
                sent_score = 10

            composite_score = min(100, max(0, base_score + story_score + sent_score))

            if composite_score >= 65:
                status = "RED"
                action = "Stage 2 SICR trigger; initiate covenant audit & limit freeze"
            elif composite_score >= 40:
                status = "AMBER"
                action = "Enhanced watchlist; request updated collateral valuation"
            else:
                status = "GREEN"
                action = "Standard monitoring; quarterly financial review"

            if not triggers:
                triggers.append(f"Stable baseline ({rating} rating, baseline PD {info['baseline_pd']:.2%})")

            item = EWSWatchlistItem(
                entity_id=ent,
                counterparty_name=info["counterparty_name"],
                sector=info["sector"],
                rating=info["rating"],
                baseline_pd=info["baseline_pd"],
                total_funded_exposure_usd=info["exposure"],
                ews_score=composite_score,
                status=status,
                story_intensity=story_intensity,
                active_story_id=active_story_id,
                recent_signals_count=article_count,
                sentiment_score=sentiment,
                triggers=triggers,
                recommended_action=action,
                updated_at=now_ts,
            )
            items.append(item)

        # Sort: RED first, then AMBER, then GREEN, within status by score desc
        status_rank = {"RED": 0, "AMBER": 1, "GREEN": 2}
        items.sort(key=lambda x: (status_rank[x.status], -x.ews_score, -x.total_funded_exposure_usd))
        return items
