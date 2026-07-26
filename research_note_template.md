# Trade Research Note: Cross-Commodity Term Structure & Momentum

*Updated 2026-07-26 with live backtest results.*

## 1. Thesis

Energy futures term structure is basically a readout of storage
economics and near-term supply/demand imbalance, and on top of that
you've got two more well-documented effects: trend persistence (slow
capital flows chasing moves) and seasonality (nobody's surprised
heating oil rallies in winter). Stack carry, momentum, and seasonality
into one signal and you'd expect something that makes money and
doesn't just track the commodity basket. That was the pitch going in.

It's half right. One of the three signals actually works. The other
two don't, and not in a subtle way — see §4 and §5 for the receipts.

## 2. Universe & Data

- Commodities: WTI Crude (CL), Henry Hub Natural Gas (NG), RBOB
  Gasoline (RB), Heating Oil (HO)
- Sample: 2015-01-02 → 2026-07-22, 2,905 daily obs, rebalanced weekly
  on Friday close
- Data: yfinance for front-month continuous futures (`CL=F`, `NG=F`,
  `RB=F`, `HO=F`), EIA v2 API for weekly NG storage and crude stocks
  (goes back to 1982). The EIA data's in the pipeline and validated but
  no signal actually uses it yet — low-hanging fruit, see §6.
- One data quirk worth flagging so nobody thinks we messed up the
  pipeline: **CL traded at -$37.63 on 2020-04-20.** That's real — the
  physical-delivery squeeze at contract expiry, not a bad print. It
  does, however, break `pct_change` math for anything touching CL
  (momentum, carry, seasonality, and the P&L / vol-targeting in the
  backtest), since dividing by a price near or below zero doesn't mean
  anything. Fix: CL uses price differences in the signal functions and
  `(P_t - P_{t-1}) / |P_{t-1}|` for the return series driving position
  sizing and P&L. Same number as `pct_change` whenever price is
  positive, just doesn't blow up when it isn't.

## 3. Signal Construction

| Signal | Logic | Rationale |
|---|---|---|
| Momentum | avg. 12-wk & 26-wk return, z-scored | trend persistence |
| Carry | trailing price vs. 4-wk rolling mean, z-scored — **a proxy**, not real carry (yfinance only gives us front-month, no second contract to build an actual spread) | contango/backwardation stand-in |
| Seasonality | historical same-calendar-month return, expanding window, needs 5+ years before we trust it | known demand cycles |

Composite = weighted z-score → position via `tanh`-squashed conviction
sizing → scaled to a 15% annualized vol target per commodity, capped
at 2x leverage, 5bps cost per unit of turnover. **Current weights:
momentum 0.15 / carry 0.15 / seasonality 0.70.** That's not the
weighting we started with (we started roughly equal, 0.4/0.4/0.2) —
we moved weight toward seasonality once we isolated each signal and
saw which one was actually pulling its weight (§4).

## 4. Backtest Results

Live config (`SIGNAL_WEIGHTS` 0.15/0.15/0.70, `CONVICTION_SCALE`
4.03 — the second one's explained in §5, it's not a random constant):

| | Sharpe | Ann. Return | Ann. Vol | Max DD | Hit Rate |
|---|---|---|---|---|---|
| CL | 0.38 | 13.06% | 24.06% | -31.41% | 51.99% |
| NG | -0.07 | 2.61% | 19.51% | -30.80% | 49.64% |
| RB | 0.27 | 10.54% | 24.61% | -44.98% | 50.72% |
| HO | 0.44 | 14.33% | 23.38% | -27.42% | 48.01% |
| **Portfolio** | **0.41** | **10.14%** | **14.98%** | **-20.30%** | **51.45%** |

**vs. Buy & Hold:** Sharpe 0.35, Ann. Return 15.99%, Ann. Vol 34.65%,
Max DD -64.44%. So we give up about a third of the benchmark's return
and get roughly a fifth of its vol and drawdown in exchange. That's a
different risk profile, not a strictly better one — we're not beating
buy-and-hold on raw return, we're beating it on how much you have to
stomach to get there.

**Per-signal, isolated** (pre-vol-scale-fix, portfolio level):
Momentum Sharpe -0.58, Carry -0.69, Seasonality +0.25. One out of
three signals is actually positive on its own. The 0.15/0.15/0.70 split
is us reacting to that, not a hunch. Charts and full per-commodity
tables for all of this live in `docs/index.html` (also up on GitHub
Pages).

## 5. Risk & Limitations (the honest section)

- Free continuous-futures data has the usual survivorship / no-clean-
  roll-adjustment caveats that come with not paying for a real vendor
  feed.
- **Carry is a proxy, full stop.** Trailing price vs. rolling mean is
  not a calendar spread. We knew this going in, but it's also
  underperformed enough that the approximation itself might be part of
  the problem, not just the "we're missing the real signal" part.
- **Momentum and carry are net-negative in isolation** — every single
  commodity, both signals. Most of that "negative Sharpe" turned out to
  be a hurdle-rate artifact, not actual losses: raw return was positive
  in every commodity/signal combo we ran except NG-momentum, NG-carry,
  and RB-momentum — it just didn't clear the 4%/yr risk-free rate we're
  benchmarking against. We checked the Sharpe formula itself for a
  double-counting bug before believing this. There isn't one.
- **Carry's biggest bets aren't reliably right, and that matters
  differently by commodity.** We pulled the 10 largest-|z-score| carry
  weeks per commodity. CL and RB: 50% hit rate (a coin flip) but
  net-positive P&L, entirely because one short entered 2020-03-13 right
  before the COVID crude crash carried the whole sample. That's a
  timing outlier, not evidence the signal works. **HO is a different
  story: 7 of its 10 biggest bets were wrong** (30% hit rate, -11.1%
  cumulative over those 10 weeks alone). That's not an outlier problem,
  that's the signal being bad at HO specifically, and it should
  probably be trimmed or cut there.
- **Momentum and carry basically don't work on natural gas.** NG Sharpe
  in isolation: -0.70 momentum, -1.07 carry, -0.16 seasonality —
  seasonality is still negative but way less bad, and it's the only one
  of the three with a positive correlation to NG's forward returns
  (+0.044 vs. -0.046 and -0.055). Our read: NG's storage- and
  weather-driven dynamics are a seasonal pattern more than a trend or
  curve-shape one, so a calendar signal has a shot where the other two
  don't. We tried excluding NG entirely (portfolio Sharpe ticks up to
  0.44, but drawdown gets worse, -24.04% vs. -20.30%) and half/quarter
  weighting it — it's a clean, monotonic Sharpe-vs-drawdown tradeoff
  with no obviously correct answer. **Still undecided, still
  equal-weighted for now.**
- **We also caught the vol-targeting silently underperforming its own
  target** — 15% annualized vol target, 3.72% realized, before we
  fixed it. Not the 2x leverage cap (never once binding), not a slow
  vol estimator (checked, it wasn't biased). It was the `tanh`
  conviction-squashing rarely getting anywhere near saturation given
  how small the composite signal's typical magnitude actually is, plus
  real diversification benefit across the four legs compounding on top
  of that. Fixed with a calibrated `CONVICTION_SCALE = 4.03` multiplier
  — that number is tied to the current signal weights and commodity
  set, so if either changes, recalibrate it, don't just carry it over.
- 5bps transaction cost assumption is a simplification — real cost
  depends on contract liquidity, not a flat number.
- No regime-conditioning anywhere. We have no idea how this behaves in
  a genuinely different vol regime than what's in-sample.
- The sample may just not contain enough distinct storage-shock or
  geopolitical-supply-shock events to call any of this statistically
  solid yet.

## 6. Next Steps

- [ ] Actually decide what to do with NG — equal-weight, half/quarter,
      or cut it. It's a Sharpe-vs-drawdown call, not a right-answer one.
- [ ] Trim or exclude HO's high-|z| carry bets specifically
- [ ] Get a real second-month futures series so carry stops being a proxy
- [ ] Build an actual storage-surprise signal off the EIA data we're
      already pulling and just not using
- [ ] Walk-forward / out-of-sample test instead of trusting one
      in-sample backtest
- [ ] Position-level attribution — which signal actually drove which
      trade, not just aggregate Sharpe
