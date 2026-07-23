"""
Central configuration: tickers, date ranges, and strategy parameters.
Tweak these first before touching pipeline logic.
"""

from datetime import date

# --- Universe -----------------------------------------------------------
# yfinance continuous front-month futures tickers
TICKERS = {
    "CL": "CL=F",   # WTI Crude Oil
    "NG": "NG=F",   # Henry Hub Natural Gas
    "RB": "RB=F",   # RBOB Gasoline
    "HO": "HO=F",   # Heating Oil / ULSD
}

# EIA series IDs for weekly inventory/storage data (v2 API)
# https://www.eia.gov/opendata/browser/
EIA_SERIES = {
    "NG": "NG.NW2_EPG0_SWO_R48_BCF.W",       # Lower 48 working gas in storage, weekly
    "CL": "PET.WCRSTUS1.W",                    # Weekly U.S. crude oil ending stocks
}

START_DATE = "2015-01-01"
END_DATE = date.today().isoformat()

# --- Signal parameters ----------------------------------------------------
MOMENTUM_LOOKBACKS_WEEKS = [12, 26]
SEASONALITY_MIN_YEARS = 5          # min years of history before trusting a seasonal effect
CARRY_SMOOTHING_WEEKS = 4          # smoothing window for the carry proxy

# --- Portfolio / backtest parameters --------------------------------------
TARGET_ANNUAL_VOL = 0.15           # 15% annualized vol target per commodity
MAX_LEVERAGE = 2.0                 # cap on position size after vol scaling
TRANSACTION_COST_BPS = 5           # round-turn cost assumption, in basis points
RISK_FREE_RATE = 0.04              # annualized, for Sharpe calc
REBALANCE_FREQ = "W-FRI"           # weekly rebalance, Friday close

# Realized portfolio vol chronically undershoots TARGET_ANNUAL_VOL: the
# composite signal's typical magnitude (mean |z| ~0.47) rarely nears the
# tanh squashing function's +-3 saturation point, so average conviction
# sizing was only ~22% of "full conviction" -- confirmed the leverage cap
# and vol estimator were not the cause (see backtest investigation).
# This multiplier restores the intended vol level; calibrated empirically
# against the gap between realized portfolio vol (3.72%) and
# TARGET_ANNUAL_VOL (15%) under the current SIGNAL_WEIGHTS. Recalibrate
# (TARGET_ANNUAL_VOL / realized portfolio AnnVol) if weights or the
# commodity universe change materially.
CONVICTION_SCALE = 4.03

# --- Signal combination weights (tuned: seasonality carried the edge,
# momentum/carry were net-negative in isolation) --------------------------
SIGNAL_WEIGHTS = {
    "momentum": 0.15,
    "carry": 0.15,
    "seasonality": 0.7,
}

DATA_DIR = "data"
OUTPUT_DIR = "output"
