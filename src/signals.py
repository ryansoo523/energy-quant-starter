"""
Signal construction: momentum, carry (term-structure proxy), and
seasonality. Each function returns a DataFrame shaped like the price
data (dates x commodities) with z-scored signal values, so they can be
combined directly.
"""

import numpy as np
import pandas as pd

import config


def _zscore(df: pd.DataFrame, window: int = 252) -> pd.DataFrame:
    """Rolling z-score, per column, to keep signals comparable across
    commodities with very different price scales and volatilities."""
    roll_mean = df.rolling(window, min_periods=window // 2).mean()
    roll_std = df.rolling(window, min_periods=window // 2).std()
    z = (df - roll_mean) / roll_std.replace(0, np.nan)
    return z.clip(-3, 3)  # winsorize extreme z-scores


def momentum_signal(prices: pd.DataFrame) -> pd.DataFrame:
    """
    Time-series momentum: average of N-week returns across the
    configured lookback windows, z-scored.

    CL (WTI) traded negative on 2020-04-20 (-$37.63 front-month
    settlement), so pct_change is undefined/nonsensical for any lookback
    window anchored at or near a zero/negative price. CL uses raw price
    differences instead, which are well-defined for any price sign; the
    other commodities stay on pct_change since they've never gone
    non-positive. Per-column z-scoring downstream makes the differing
    units (dollars vs. fraction) comparable, so nothing else changes.
    """
    weekly = prices.resample(config.REBALANCE_FREQ).last()
    signals = []
    for weeks in config.MOMENTUM_LOOKBACKS_WEEKS:
        ret = weekly.pct_change(weeks)
        if "CL" in weekly.columns:
            ret["CL"] = weekly["CL"].diff(weeks)
        signals.append(ret)
    combined = sum(signals) / len(signals)
    return _zscore(combined, window=52)


def carry_signal(prices: pd.DataFrame) -> pd.DataFrame:
    """
    Carry / term-structure proxy.

    NOTE: yfinance's 'CL=F' style tickers only give you the front-month
    continuous contract, not a second month — so you can't compute a true
    calendar spread from this data alone. As an MVP proxy, we use the
    trailing price-vs-rolling-mean relationship as a stand-in for
    curve shape (persistent premium to trailing average ~ backwardation-
    like behavior; persistent discount ~ contango-like behavior).

    TO UPGRADE: once you have two contract months (CME delayed data, a
    broker feed, or paid vendor), replace this with:
        carry = (front_month_price - next_month_price) / front_month_price
    which is the real, standard carry signal traders use. Keep this
    function's output shape (weekly, per-commodity, z-scored) the same
    so nothing downstream needs to change.

    CL note: same negative-price issue as momentum_signal. Dividing by
    trailing_mean turns nonsensical whenever that trailing average is at
    or near zero (which a negative print like 2020-04-20 can drag it
    toward), so CL uses the raw dollar premium/discount vs. its trailing
    mean instead of the percentage version. Other commodities keep the
    percentage proxy.
    """
    weekly = prices.resample(config.REBALANCE_FREQ).last()
    trailing_mean = weekly.rolling(config.CARRY_SMOOTHING_WEEKS).mean()
    proxy = (weekly - trailing_mean) / trailing_mean
    if "CL" in weekly.columns:
        proxy["CL"] = weekly["CL"] - trailing_mean["CL"]
    return _zscore(proxy, window=52)


def seasonality_signal(prices: pd.DataFrame) -> pd.DataFrame:
    """
    Month-of-year seasonality: for each commodity, compute the average
    historical return for the *current* calendar month vs. other months,
    using only data available up to that point (expanding window to
    avoid look-ahead bias).

    CL note: same negative-price issue as momentum_signal. CL uses raw
    price differences instead of pct_change; other commodities unchanged.
    """
    weekly = prices.resample(config.REBALANCE_FREQ).last()
    monthly_ret = weekly.pct_change(4)  # approx monthly return in weekly steps
    if "CL" in weekly.columns:
        monthly_ret["CL"] = weekly["CL"].diff(4)

    result = pd.DataFrame(index=weekly.index, columns=weekly.columns, dtype=float)

    for col in weekly.columns:
        series = monthly_ret[col].dropna()
        for dt in weekly.index:
            history = series[series.index < dt]
            if history.empty:
                continue
            same_month = history[history.index.month == dt.month]
            years_seen = same_month.index.year.nunique()
            if years_seen < config.SEASONALITY_MIN_YEARS:
                continue
            result.loc[dt, col] = same_month.mean()

    return _zscore(result.astype(float), window=52)


def combine_signals(prices: pd.DataFrame) -> pd.DataFrame:
    """
    Combine momentum, carry, and seasonality into one composite score
    per commodity per week, using config.SIGNAL_WEIGHTS.
    """
    mom = momentum_signal(prices)
    carry = carry_signal(prices)
    season = seasonality_signal(prices)

    w = config.SIGNAL_WEIGHTS
    composite = (
        w["momentum"] * mom.fillna(0)
        + w["carry"] * carry.fillna(0)
        + w["seasonality"] * season.fillna(0)
    )

    # Require at least the momentum signal to be live, else no position
    composite = composite.where(mom.notna())
    return composite


if __name__ == "__main__":
    import data_pipeline

    prices, _ = data_pipeline.load_all()
    composite = combine_signals(prices)
    print(composite.tail(10))
