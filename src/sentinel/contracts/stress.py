"""Wholesale banking stress testing contracts conforming to PRD Section 10."""

from datetime import date
from enum import Enum

from pydantic import BaseModel, Field


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
