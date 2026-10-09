"""Wholesale banking portfolio loader and validator conforming to PRD Section 9.1."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

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
        self.sector_fraud_rates: Dict[str, float] = {}  # from the retail sleeve, if loaded

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

    @classmethod
    def load_many(cls, paths: Sequence[Union[str, Path]]) -> "WholesalePortfolio":
        """Combine the wholesale book with sleeve files (e.g. the retail/SME credit sleeve).

        The first file provides the portfolio name and valuation date; the summary is
        recomputed from the combined positions so totals can never drift from the data.
        """
        books = [cls.load_from_json(paths[0])] + [cls._load_sleeve(Path(p)) for p in paths[1:]]
        base = books[0]
        merged = cls(
            portfolio_name=base.portfolio_name,
            base_currency=base.base_currency,
            valuation_date=base.valuation_date,
            summary=base.summary,
            loans=[x for b in books for x in b.loans],
            bonds=[x for b in books for x in b.bonds],
            swaps=[x for b in books for x in b.swaps],
            cash=[x for b in books for x in b.cash],
        )
        merged.summary = merged._computed_summary()
        for b in books:
            merged.sector_fraud_rates.update(b.sector_fraud_rates)
        return merged

    @classmethod
    def _load_sleeve(cls, path: Path) -> "WholesalePortfolio":
        data = json.loads(path.read_text(encoding="utf-8"))
        loans = [
            LoanPosition.model_validate(p) for p in data["positions"] if p["asset_class"] == "loan"
        ]
        sleeve = cls(
            portfolio_name=data.get("portfolio_name", path.stem),
            base_currency=data.get("base_currency", "USD"),
            valuation_date=data.get("valuation_date", "2026-03-01"),
            summary=PortfolioSummary(
                total_book_value_usd=0.0,
                corporate_loans_value_usd=0.0,
                corporate_bonds_value_usd=0.0,
                cash_reserves_usd=0.0,
                interest_rate_swaps_gross_notional_usd=0.0,
            ),
            loans=loans,
            bonds=[],
            swaps=[],
            cash=[],
        )
        sleeve.sector_fraud_rates = data.get("sector_fraud_rates", {})
        return sleeve

    def _computed_summary(self) -> PortfolioSummary:
        return PortfolioSummary(
            total_book_value_usd=self.total_funded_exposure,
            corporate_loans_value_usd=sum(p.market_value for p in self.loans),
            corporate_bonds_value_usd=sum(p.market_value for p in self.bonds),
            cash_reserves_usd=sum(p.market_value for p in self.cash),
            interest_rate_swaps_mtm_usd=sum(p.market_value for p in self.swaps),
            interest_rate_swaps_gross_notional_usd=self.total_derivative_notional,
        )

    def sleeve_totals(self) -> Dict[str, float]:
        totals: Dict[str, float] = {}
        for pos in [*self.loans, *self.bonds, *self.cash]:
            totals[pos.sleeve] = totals.get(pos.sleeve, 0.0) + pos.market_value
        return totals

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
            "funded_value_by_sleeve_usd": self.sleeve_totals(),
        }
