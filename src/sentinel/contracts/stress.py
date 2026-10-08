"""Wholesale banking stress testing contracts conforming to PRD Section 10."""

from datetime import date
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class AssetClass(str, Enum):
    LOAN = "loan"
    BOND = "bond"
    SWAP = "swap"
    CASH = "cash"


class LoanPosition(BaseModel):
    position_id: str
    asset_class: AssetClass = AssetClass.LOAN
    entity_id: str
    counterparty_name: str
    sector: str
    currency: str = "USD"
    market_value: float = Field(..., ge=0.0)
    ead: float = Field(..., ge=0.0, description="Exposure at default")
    baseline_pd: float = Field(..., ge=0.0, le=1.0, description="Probability of default")
    lgd: float = Field(..., ge=0.0, le=1.0, description="Loss given default")
    rating: str
    maturity_date: date


class BondPosition(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    position_id: str
    asset_class: AssetClass = AssetClass.BOND
    entity_id: str
    counterparty_name: str
    sector: str
    currency: str = "USD"
    market_value: float = Field(..., ge=0.0)
    notional: float = Field(..., ge=0.0)
    coupon: float = Field(..., ge=0.0)
    yield_val: float = Field(..., alias="yield", ge=0.0)
    spread_bps: float = Field(..., ge=0.0)
    modified_duration: float = Field(..., ge=0.0, description="Effective duration in years")
    rating: str
    maturity_date: date


class SwapPosition(BaseModel):
    position_id: str
    asset_class: AssetClass = AssetClass.SWAP
    entity_id: str
    counterparty_name: str
    sector: str
    currency: str = "USD"
    market_value: float = Field(default=0.0, description="Mark to market value")
    notional: float = Field(..., ge=0.0, description="Gross derivative notional")
    pay_receive: str = Field(..., description="receive_fixed or pay_fixed")
    fixed_rate: float
    floating_benchmark: str = "SOFR"
    signed_dv01: float = Field(..., description="Dollar value of 1 basis point shift")
    maturity_years: float = Field(..., ge=0.0)
    maturity_date: date


class CashPosition(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    position_id: str
    asset_class: AssetClass = AssetClass.CASH
    entity_id: str
    counterparty_name: str
    sector: str = "Government / Cash"
    currency: str = "USD"
    market_value: float = Field(..., ge=0.0)
    notional: float = Field(..., ge=0.0)
    yield_val: float = Field(..., alias="yield", ge=0.0)
    modified_duration: float = 0.0
    rating: str = "AAA"
    maturity_date: date


class PortfolioSummary(BaseModel):
    total_book_value_usd: float = Field(..., ge=0.0)
    corporate_loans_value_usd: float = Field(..., ge=0.0)
    corporate_bonds_value_usd: float = Field(..., ge=0.0)
    cash_reserves_usd: float = Field(..., ge=0.0)
    interest_rate_swaps_mtm_usd: float = 0.0
    interest_rate_swaps_gross_notional_usd: float = Field(..., ge=0.0)


class PositionStressDelta(BaseModel):
    position_id: str
    asset_class: AssetClass
    entity_id: str
    counterparty_name: str
    sector: str
    baseline_value_usd: float
    stressed_value_usd: float
    pnl_usd: float
    pct_change: float
    ecl_baseline_usd: float = 0.0
    ecl_stressed_usd: float = 0.0
    incremental_ecl_usd: float = 0.0
    market_risk_pnl_usd: float = 0.0
    applied_shock_summary: str = "Unimpacted"


class AssetClassStressSummary(BaseModel):
    asset_class: AssetClass
    baseline_value_usd: float
    stressed_value_usd: float
    total_pnl_usd: float
    pct_change: float
    credit_ecl_delta_usd: float = 0.0
    mark_to_market_pnl_usd: float = 0.0
    derivative_gross_notional_usd: float = 0.0


class SectorStressSummary(BaseModel):
    sector: str
    baseline_value_usd: float
    stressed_value_usd: float
    total_pnl_usd: float
    pct_change: float


class StressRunResult(BaseModel):
    stress_id: str
    run_id: str
    executed_at: str
    trigger_type: str = "EVENT_TRIGGERED"
    trigger_signal_id: Optional[str] = None
    event_class: str
    impact_score: int
    target_entity: Optional[str] = None
    target_scope: str = "entity"
    shock_parameters: dict = Field(default_factory=dict)
    model_version: str = "v1.0.0-multiasset"
    baseline_total_book_value_usd: float
    stressed_total_book_value_usd: float
    total_pnl_usd: float
    total_pnl_pct: float
    credit_ecl_change_usd: float
    market_mtm_change_usd: float
    asset_class_breakdown: List[AssetClassStressSummary]
    sector_breakdown: List[SectorStressSummary]
    position_deltas: List[PositionStressDelta]
    reconciliation_passed: bool

