"""
Vectorized backtest engine.

Given a composite signal (dates x commodities) and price data, this:
  1. Converts signal -> target position (-1 to +1 direction, scaled by
     inverse realized vol so each commodity contributes similar risk)
  2. Applies a leverage cap
  3. Charges transaction costs on position changes
  4. Computes portfolio and per-commodity returns
  5. Reports Sharpe, max drawdown, hit rate, and annualized return

This is intentionally written out longhand (not hidden behind a
library) so you can explain every line of it in an interview.
"""

import numpy as np
import pandas as pd

import config


def realized_vol(weekly_returns: pd.DataFrame, window: int = 12) -> pd.DataFrame:
    """Annualized rolling realized volatility, weekly data -> *sqrt(52)."""
    return weekly_returns.rolling(window, min_periods=window // 2).std() * np.sqrt(52)


def signal_to_positions(signal: pd.DataFrame, weekly_returns: pd.DataFrame) -> pd.DataFrame:
    """
    Convert a z-scored composite signal into vol-targeted positions.

    direction = sign-preserving, magnitude-scaled by the signal itself
                (tanh-squashed so extreme z-scores don't blow up position size)
    size      = TARGET_ANNUAL_VOL / realized_vol, capped at MAX_LEVERAGE,
                then uniformly scaled by CONVICTION_SCALE to correct for
                the composite signal's typical magnitude rarely nearing
                the tanh's saturation point (see config.py for detail)
    """
    direction = np.tanh(signal / 2.0)  # smooth squashing into roughly [-1, 1]
    vol = realized_vol(weekly_returns)
    vol_scalar = (config.TARGET_ANNUAL_VOL / vol).clip(upper=config.MAX_LEVERAGE)
    positions = direction * vol_scalar * config.CONVICTION_SCALE
    return positions.clip(-config.MAX_LEVERAGE, config.MAX_LEVERAGE)


def run_backtest(prices: pd.DataFrame, composite_signal: pd.DataFrame) -> dict:
    """
    Runs the full backtest and returns a dict with:
      - 'positions': target positions per commodity per week
      - 'commodity_returns': net-of-cost weekly returns per commodity
      - 'portfolio_returns': equal-weighted combination across commodities
      - 'metrics': DataFrame of Sharpe / max DD / hit rate per commodity
                    plus a 'PORTFOLIO' row
    """
    weekly_prices = prices.resample(config.REBALANCE_FREQ).last()
    weekly_returns = weekly_prices.pct_change()
    if "CL" in weekly_prices.columns:
        # CL has traded negative (2020-04-20), so pct_change can blow up
        # or sign-invert whenever the prior price is at/near zero. Scale
        # the price diff by the prior price's absolute value instead --
        # identical to pct_change whenever price is positive, but always
        # well-defined and keeps CL's "return" in the same fractional
        # units as NG/RB/HO, so vol-targeting, Sharpe, and the portfolio
        # average across commodities all stay comparable.
        prev_cl = weekly_prices["CL"].shift(1)
        weekly_returns["CL"] = (weekly_prices["CL"] - prev_cl) / prev_cl.abs()

    positions = signal_to_positions(composite_signal, weekly_returns)
    # Trade on the signal computed as of week t, realized over week t+1
    positions_lagged = positions.shift(1)

    gross_returns = positions_lagged * weekly_returns

    # Transaction costs: charged on the change in position size, in bps
    turnover = positions_lagged.diff().abs().fillna(0)
    cost = turnover * (config.TRANSACTION_COST_BPS / 10_000)
    net_returns = gross_returns - cost

    portfolio_returns = net_returns.mean(axis=1, skipna=True)

    metrics = compute_metrics(net_returns, portfolio_returns)

    return {
        "positions": positions_lagged,
        "commodity_returns": net_returns,
        "portfolio_returns": portfolio_returns,
        "metrics": metrics,
    }


def compute_metrics(commodity_returns: pd.DataFrame, portfolio_returns: pd.Series) -> pd.DataFrame:
    rows = {}

    def _row(returns: pd.Series) -> dict:
        returns = returns.dropna()
        if returns.empty:
            return {"Sharpe": np.nan, "AnnReturn": np.nan, "AnnVol": np.nan,
                    "MaxDrawdown": np.nan, "HitRate": np.nan}
        ann_return = returns.mean() * 52
        ann_vol = returns.std() * np.sqrt(52)
        sharpe = (ann_return - config.RISK_FREE_RATE) / ann_vol if ann_vol > 0 else np.nan

        cum = (1 + returns).cumprod()
        running_max = cum.cummax()
        drawdown = (cum - running_max) / running_max
        max_dd = drawdown.min()

        hit_rate = (returns > 0).mean()

        return {
            "Sharpe": round(sharpe, 2),
            "AnnReturn": round(ann_return, 4),
            "AnnVol": round(ann_vol, 4),
            "MaxDrawdown": round(max_dd, 4),
            "HitRate": round(hit_rate, 4),
        }

    for col in commodity_returns.columns:
        rows[col] = _row(commodity_returns[col])
    rows["PORTFOLIO"] = _row(portfolio_returns)

    return pd.DataFrame(rows).T


def buy_and_hold_benchmark(prices: pd.DataFrame) -> dict:
    """Simple equal-weight buy-and-hold benchmark for comparison."""
    weekly_prices = prices.resample(config.REBALANCE_FREQ).last()
    weekly_returns = weekly_prices.pct_change()
    if "CL" in weekly_prices.columns:
        # Same fix as run_backtest: keeps CL in fractional-return units
        # (identical to pct_change when price is positive) without
        # blowing up or sign-inverting around a zero/negative print.
        prev_cl = weekly_prices["CL"].shift(1)
        weekly_returns["CL"] = (weekly_prices["CL"] - prev_cl) / prev_cl.abs()
    portfolio_returns = weekly_returns.mean(axis=1, skipna=True)
    metrics = compute_metrics(weekly_returns, portfolio_returns)
    return {"commodity_returns": weekly_returns, "portfolio_returns": portfolio_returns,
            "metrics": metrics}


if __name__ == "__main__":
    import data_pipeline
    import signals

    prices, _ = data_pipeline.load_all()
    composite = signals.combine_signals(prices)
    result = run_backtest(prices, composite)

    print("Strategy metrics:")
    print(result["metrics"])

    bh = buy_and_hold_benchmark(prices)
    print("\nBuy-and-hold benchmark:")
    print(bh["metrics"])
