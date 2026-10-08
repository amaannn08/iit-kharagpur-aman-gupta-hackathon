"""Wholesale banking portfolio loader and validator conforming to PRD Section 9.1."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from sentinel.contracts.stress import (
    BondPosition,
    CashPosition,
    LoanPosition,
    PortfolioSummary,
    SwapPosition,
)


class WholesalePortfolio:
    """Holds institutional credit and rates portfolio with strict asset segregation."""

    def __init__(
        self,
        portfolio_name: str,
        base_currency: str,
        valuation_date: str,
        summary: PortfolioSummary,
        loans: List[LoanPosition],
        bonds: List[BondPosition],
        swaps: List[SwapPosition],
        cash: List[CashPosition],
    ) -> None:
        self.portfolio_name = portfolio_name
        self.base_currency = base_currency
        self.valuation_date = valuation_date
        self.summary = summary
        self.loans = loans
        self.bonds = bonds
        self.swaps = swaps
        self.cash = cash

    @classmethod
    def load_from_json(cls, file_path: Optional[Union[str, Path]] = None) -> "WholesalePortfolio":
        path = Path(file_path) if file_path else Path("data/wholesale_positions.json")
        if not path.exists():
            raise FileNotFoundError(f"Portfolio file not found at {path}")

        with open(path, mode="r", encoding="utf-8") as f:
            data = json.load(f)

        summary = PortfolioSummary.model_validate(data["summary"])

        loans: List[LoanPosition] = []
        bonds: List[BondPosition] = []
        swaps: List[SwapPosition] = []
        cash: List[CashPosition] = []

        for p in data.get("positions", []):
            asset_class = p.get("asset_class")
            if asset_class == "loan":
                loans.append(LoanPosition.model_validate(p))
            elif asset_class == "bond":
                bonds.append(BondPosition.model_validate(p))
            elif asset_class == "swap":
                swaps.append(SwapPosition.model_validate(p))
            elif asset_class == "cash":
                cash.append(CashPosition.model_validate(p))

        return cls(
            portfolio_name=data.get("portfolio_name", "Wholesale Portfolio"),
            base_currency=data.get("base_currency", "USD"),
            valuation_date=data.get("valuation_date", "2026-03-01"),
            summary=summary,
            loans=loans,
            bonds=bonds,
            swaps=swaps,
            cash=cash,
        )

    @property
    def total_funded_exposure(self) -> float:
        """Funded exposure: loans + bonds + cash."""
        loan_val = sum(pos.market_value for pos in self.loans)
        bond_val = sum(pos.market_value for pos in self.bonds)
        cash_val = sum(pos.market_value for pos in self.cash)
        return loan_val + bond_val + cash_val

    @property
    def total_derivative_notional(self) -> float:
        """Derivative gross notional (segregated from funded book value)."""
        return sum(pos.notional for pos in self.swaps)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "portfolio_name": self.portfolio_name,
            "base_currency": self.base_currency,
            "valuation_date": self.valuation_date,
            "summary": self.summary.model_dump(),
            "loans": [pos.model_dump(mode="json") for pos in self.loans],
            "bonds": [pos.model_dump(mode="json") for pos in self.bonds],
            "swaps": [pos.model_dump(mode="json") for pos in self.swaps],
            "cash": [pos.model_dump(mode="json") for pos in self.cash],
        }
