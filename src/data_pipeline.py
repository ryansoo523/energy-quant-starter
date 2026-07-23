"""
Data pipeline: pulls daily futures prices (yfinance) and weekly EIA
storage/inventory data, cleans and caches both to data/.

Run standalone for a quick sanity check:
    python src/data_pipeline.py
"""

import os
import time
import warnings

import numpy as np
import pandas as pd

try:
    import yfinance as yf
except ImportError:
    yf = None

import requests
from dotenv import load_dotenv

import config

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))


def _cache_path(name: str) -> str:
    os.makedirs(config.DATA_DIR, exist_ok=True)
    return os.path.join(config.DATA_DIR, name)


def fetch_futures_prices(force_refresh: bool = False) -> pd.DataFrame:
    """
    Pull daily close prices for every ticker in config.TICKERS.
    Returns a DataFrame indexed by date, one column per commodity code
    (e.g. 'CL', 'NG', 'RB', 'HO').
    """
    cache_file = _cache_path("futures_prices.csv")
    if os.path.exists(cache_file) and not force_refresh:
        df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
        return df

    if yf is None:
        raise ImportError("yfinance is not installed. Run: pip install yfinance")

    frames = {}
    for code, ticker in config.TICKERS.items():
        for attempt in range(3):
            try:
                raw = yf.download(
                    ticker,
                    start=config.START_DATE,
                    end=config.END_DATE,
                    progress=False,
                    auto_adjust=True,
                )
                if raw.empty:
                    raise ValueError(f"No data returned for {ticker}")
                # yfinance sometimes returns a MultiIndex column set
                # (Price, Ticker) even for a single ticker, so "Close" comes
                # back as a 1-column DataFrame rather than a Series.
                close = raw["Close"] if "Close" in raw.columns else raw.iloc[:, 0]
                if isinstance(close, pd.DataFrame):
                    close = close.iloc[:, 0]
                frames[code] = close
                break
            except Exception as e:
                warnings.warn(f"Attempt {attempt+1} failed for {ticker}: {e}")
                time.sleep(2)
        else:
            warnings.warn(f"Giving up on {ticker} after 3 attempts.")

    df = pd.DataFrame(frames)
    df = df.sort_index()
    df = df.ffill(limit=3)  # bridge small gaps (holidays, missed prints)
    df.to_csv(cache_file)
    return df


def fetch_eia_series(series_id: str, api_key: str = None) -> pd.Series:
    """
    Pull a single EIA v2 series (e.g. weekly nat gas storage).
    Requires a free API key: https://www.eia.gov/opendata/register.php
    Set EIA_API_KEY as an environment variable, or pass it directly.
    """
    api_key = api_key or os.environ.get("EIA_API_KEY")
    if not api_key:
        warnings.warn(
            "No EIA_API_KEY set. Skipping storage data pull — "
            "storage-surprise signal will be unavailable. "
            "Get a free key at https://www.eia.gov/opendata/register.php"
        )
        return pd.Series(dtype=float)

    # EIA v2 API: series route varies by dataset; this hits the generic
    # "seriesid" pattern used for legacy-style series IDs.
    url = f"https://api.eia.gov/v2/seriesid/{series_id}"
    params = {"api_key": api_key}

    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    payload = resp.json()

    try:
        rows = payload["response"]["data"]
    except KeyError:
        warnings.warn(f"Unexpected EIA response shape for {series_id}: {payload}")
        return pd.Series(dtype=float)

    df = pd.DataFrame(rows)
    date_col = "period"
    value_col = "value"
    df[date_col] = pd.to_datetime(df[date_col])
    series = df.set_index(date_col)[value_col].astype(float).sort_index()
    series.name = series_id
    return series


def fetch_all_storage_data(force_refresh: bool = False) -> pd.DataFrame:
    cache_file = _cache_path("eia_storage.csv")
    if os.path.exists(cache_file) and not force_refresh:
        return pd.read_csv(cache_file, index_col=0, parse_dates=True)

    frames = {}
    for code, series_id in config.EIA_SERIES.items():
        s = fetch_eia_series(series_id)
        if not s.empty:
            frames[code] = s

    if not frames:
        return pd.DataFrame()

    df = pd.DataFrame(frames)
    df.to_csv(cache_file)
    return df


def load_all(force_refresh: bool = False):
    """Convenience wrapper: returns (prices_df, storage_df)."""
    prices = fetch_futures_prices(force_refresh=force_refresh)
    storage = fetch_all_storage_data(force_refresh=force_refresh)
    return prices, storage


if __name__ == "__main__":
    prices, storage = load_all()
    print("Futures prices:")
    print(prices.tail())
    print("\nEIA storage data (if key was set):")
    print(storage.tail() if not storage.empty else "  (none — set EIA_API_KEY)")
