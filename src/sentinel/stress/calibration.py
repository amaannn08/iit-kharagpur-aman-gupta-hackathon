"""Module B shock calibration formulas and utilities."""

HY_DURATION = 3.7  # HYG
IG_DURATION = 8.4  # LQD
TSY_DURATION = 7.3  # IEF (7-10y Treasuries)


def implied_spread_change_bps(
    r_credit: float,
    r_tsy: float,
    d_credit: float,
    d_tsy: float = TSY_DURATION,
) -> float:
    """Credit-spread change implied by a credit ETF vs a duration-matched Treasury hedge.

    r_credit ≈ -D_c (dy + ds),  r_tsy ≈ -D_t dy  =>  ds = -(r_credit - (D_c / D_t) r_tsy) / D_c
    Price returns include carry; over windows of weeks this is < 10 bp and is ignored.
    """
    return -(r_credit - (d_credit / d_tsy) * r_tsy) / d_credit * 1e4
