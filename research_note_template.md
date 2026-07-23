# Trade Research Note: Cross-Commodity Term Structure & Momentum

*Fill this in once you have real backtest results. Keep it to ~2 pages —
this should read like something you'd hand to a PM, not a term paper.*

## 1. Thesis

*One paragraph. What's the market inefficiency or structural pattern
you're trying to capture? Why should it exist? Why hasn't it been
arbitraged away?*

Example framing: "Energy futures term structure reflects storage
economics and near-term supply/demand imbalances. Combined with
trend persistence from slow-moving capital flows and known seasonal
demand patterns (winter heating, summer driving), a systematic signal
combining carry, momentum, and seasonality should generate risk-adjusted
returns uncorrelated with a simple buy-and-hold commodity basket."

## 2. Universe & Data

- Commodities: WTI Crude (CL), Henry Hub Natural Gas (NG), RBOB
  Gasoline (RB), Heating Oil (HO)
- Sample period: [fill in actual dates from your data]
- Data sources: yfinance (price), EIA (storage) — *note any known data
  limitations, e.g. the carry proxy caveat in signals.py*

## 3. Signal Construction

| Signal | Logic | Rationale |
|---|---|---|
| Momentum | avg. 12-week & 26-week return, z-scored | trend persistence |
| Carry | [describe your actual implementation] | contango/backwardation |
| Seasonality | historical same-month return, expanding window | known demand cycles |

## 4. Backtest Results

*Paste your actual output/strategy_metrics.csv table here, plus the
equity curve image.*

| | Sharpe | Ann. Return | Ann. Vol | Max DD | Hit Rate |
|---|---|---|---|---|---|
| CL | | | | | |
| NG | | | | | |
| RB | | | | | |
| HO | | | | | |
| **Portfolio** | | | | | |

**vs. Buy & Hold benchmark:** [Sharpe, return, drawdown]

## 5. Risk & Limitations (be honest — this is what shows maturity)

- Backtest is subject to survivorship/data-quality limits of free
  continuous-futures data (no clean roll adjustment).
- Carry signal is a proxy, not a true calendar spread — flag this
  explicitly, don't hide it.
- Transaction cost assumption (5bps) is a simplification; real futures
  costs vary by liquidity and contract.
- No regime-conditioning — the strategy may behave very differently in
  a low-vol vs. high-vol commodity environment.
- Sample period may not include enough distinct storage-shock or
  geopolitical-supply-shock regimes to be statistically robust.

## 6. Next Steps

- [ ] Get a real second-month futures series to replace the carry proxy
- [ ] Add storage-surprise signal using EIA weekly releases
- [ ] Walk-forward / out-of-sample validation instead of a single
      in-sample backtest
- [ ] Position-level attribution: which signal drove which trades
