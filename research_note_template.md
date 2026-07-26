# Trade Research Note: Cross-Commodity Term Structure & Momentum

*Updated 2026-07-26 with live backtest results.*

## 1. Thesis

Energy futures term structure reflects storage economics and near-term
supply/demand imbalances. Combined with trend persistence from
slow-moving capital flows and known seasonal demand patterns (winter
heating, summer driving), a systematic signal combining carry,
momentum, and seasonality should generate risk-adjusted returns
uncorrelated with a simple buy-and-hold commodity basket. In practice,
only one of the three legs of that thesis held up — see §4 and §5.

## 2. Universe & Data

- Commodities: WTI Crude (CL), Henry Hub Natural Gas (NG), RBOB
  Gasoline (RB), Heating Oil (HO)
- Sample period: 2015-01-02 → 2026-07-22 (2,905 daily observations,
  weekly rebalance on Friday close)
- Data sources: yfinance (front-month continuous futures, `CL=F` /
  `NG=F` / `RB=F` / `HO=F`), EIA v2 API (weekly NG working-gas storage
  and crude stocks, 1982–present, used as a data-quality cross-check —
  not yet consumed by any signal, see §6)
- Known data limitation: **CL printed -$37.63 on 2020-04-20** (the
  real physical-delivery expiry squeeze, not a data error). It broke
  every `pct_change`-based calculation that touched CL — momentum,
  carry, and seasonality signals, plus the P&L and vol-targeting math
  in the backtest engine. Fixed by switching CL (only) to price
  differences in the signal functions and to
  `(P_t - P_{t-1}) / |P_{t-1}|` in the return series that drives
  position sizing and P&L — mathematically identical to `pct_change`
  for positive prices, well-defined for any sign.

## 3. Signal Construction

| Signal | Logic | Rationale |
|---|---|---|
| Momentum | avg. 12-week & 26-week return, z-scored | trend persistence |
| Carry | trailing price vs. rolling 4-week mean, z-scored — a **proxy**, not a true calendar spread (yfinance only exposes the front-month continuous contract; no second month to compute an actual carry) | contango/backwardation stand-in |
| Seasonality | historical same-calendar-month return, expanding window, min. 5 years before trusting an effect | known demand cycles |

Composite signal = weighted z-score, converted to a position via
`tanh`-squashed conviction sizing, scaled to a 15% annualized vol
target per commodity, capped at 2x leverage, 5bps transaction cost on
turnover. **Signal weights: momentum 0.15 / carry 0.15 / seasonality
0.70** — reweighted from an initial equal-ish 0.4/0.4/0.2 split after
isolating each signal's standalone performance (§4).

## 4. Backtest Results

Current live configuration (`SIGNAL_WEIGHTS` 0.15/0.15/0.70,
`CONVICTION_SCALE` 4.03 — see §5 on why that multiplier exists):

| | Sharpe | Ann. Return | Ann. Vol | Max DD | Hit Rate |
|---|---|---|---|---|---|
| CL | 0.38 | 13.06% | 24.06% | -31.41% | 51.99% |
| NG | -0.07 | 2.61% | 19.51% | -30.80% | 49.64% |
| RB | 0.27 | 10.54% | 24.61% | -44.98% | 50.72% |
| HO | 0.44 | 14.33% | 23.38% | -27.42% | 48.01% |
| **Portfolio** | **0.41** | **10.14%** | **14.98%** | **-20.30%** | **51.45%** |

**vs. Buy & Hold benchmark:** Sharpe 0.35, Ann. Return 15.99%, Ann. Vol
34.65%, Max DD -64.44%. The strategy trades roughly a third of the
benchmark's return for a fifth of its volatility and drawdown — a
materially different risk profile, not a strictly better one; it does
not out-earn buy-and-hold in raw terms, but it is competitive on a
risk-adjusted basis and far gentler on drawdown.

**Signal decomposition** (each signal run in isolation, pre-vol-scale
fix, portfolio level): Momentum Sharpe -0.58, Carry -0.69, Seasonality
+0.25. Seasonality is the only signal carrying positive Sharpe; the
0.15/0.15/0.70 weighting reflects that. Full equity curve, per-signal
bar chart, and per-commodity tables are in `docs/index.html`
(published at the project's GitHub Pages URL).

## 5. Risk & Limitations (be honest — this is what shows maturity)

- Backtest is subject to survivorship/data-quality limits of free
  continuous-futures data (no clean roll adjustment).
- **Carry signal is a proxy, not a true calendar spread** — a trailing
  price-vs-mean stand-in, explicitly not the real term-structure
  signal. It is also one of the two weakest legs (see below).
- **Momentum and carry are both net-negative in isolation**, at the
  portfolio level and on 4/4 (carry) and 4/4 (momentum) individual
  commodities. Most — but not all — of that "negative Sharpe" is a
  hurdle-rate effect: raw return was positive in every commodity/signal
  combination tested except NG-momentum, NG-carry, and RB-momentum,
  it just didn't clear the 4%/yr risk-free rate. Verified the Sharpe
  formula itself is correct (no double-penalization bug) before
  concluding this.
- **Carry's largest bets are not uniformly reliable.** Isolating the
  10 largest-|z-score| carry weeks per commodity: CL and RB show a
  coin-flip hit rate (50%) but net-positive contribution, dominated by
  one correctly-timed short entered 2020-03-13 ahead of the COVID
  crude crash — outlier-driven, not skill. **Heating Oil is different:
  7 of its 10 largest bets were wrong** (30% hit rate, -11.1%
  cumulative over those 10 weeks) — a systematic weakness worth
  trimming or excluding, not an outlier.
- **Momentum and carry do not transfer well to natural gas.** NG Sharpe
  is -0.70 (momentum) and -1.07 (carry) in isolation, vs. -0.16 for
  seasonality — the only signal with a positive correlation to NG's
  forward returns (+0.044, vs. -0.046 and -0.055 for momentum/carry).
  Plausibly NG's storage- and weather-driven seasonal dynamics suit a
  calendar-based signal better than trend- or curve-shape-based ones.
  Tested excluding NG entirely (portfolio Sharpe 0.44, but deepest
  drawdown of any option at -24.04%) vs. half/quarter-weighting it — a
  smooth, monotonic tradeoff with no dominant option. **Not yet
  decided; currently still equal-weighted.**
- **Vol-targeting was found to chronically undershoot its 15% target**
  (realized 3.72% before the fix) — root cause was `tanh`-squashed
  conviction sizing rarely nearing saturation given the composite
  signal's typical magnitude, compounded by genuine cross-commodity
  diversification (NG correlates negatively with the other three legs).
  Confirmed the 2x leverage cap was never the constraint, and the
  12-week vol estimator was not biased low. Fixed with a calibrated
  `CONVICTION_SCALE = 4.03` multiplier — this number is specific to
  the current `SIGNAL_WEIGHTS` and commodity set and should be
  recalibrated if either changes.
- Transaction cost assumption (5bps) is a simplification; real futures
  costs vary by liquidity and contract.
- No regime-conditioning — the strategy may behave very differently in
  a low-vol vs. high-vol commodity environment.
- Sample period may not include enough distinct storage-shock or
  geopolitical-supply-shock regimes to be statistically robust.

## 6. Next Steps

- [ ] Decide NG treatment: keep equal-weight, reduce to 0.5x/0.25x, or
      exclude — no option dominates, it's a Sharpe-vs-drawdown call
- [ ] Trim or exclude high-|z| carry bets specifically on HO
- [ ] Get a real second-month futures series to replace the carry proxy
- [ ] Consume the EIA storage series in an actual storage-surprise
      signal — currently pulled and validated but unused
- [ ] Walk-forward / out-of-sample validation instead of a single
      in-sample backtest
- [ ] Position-level attribution: which signal drove which trades
