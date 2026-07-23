# Cross-Commodity Term Structure & Momentum Strategy

A systematic trading strategy across energy commodity futures (WTI Crude,
Henry Hub Natural Gas, RBOB Gasoline, Heating Oil) combining:

- **Time-series momentum** (trend-following)
- **Carry / term structure** (contango vs. backwardation)
- **Seasonality** (month-of-year demand effects)
- **(Optional/stretch) Storage surprise** using EIA weekly inventory data

Built to demonstrate commodity-market-structure intuition, not just an
ML pipeline — the kind of signal logic an energy trading desk actually
watches week to week.

## Repo structure

```
energy_quant_project/
├── README.md
├── requirements.txt
├── src/
│   ├── config.py          # tickers, dates, strategy params
│   ├── data_pipeline.py   # pulls futures prices + EIA storage data
│   ├── signals.py         # momentum, carry, seasonality signal construction
│   ├── backtest.py        # vectorized backtest engine + performance metrics
│   └── main.py            # runs the full pipeline end-to-end
├── data/                   # cached CSVs land here
├── output/                 # backtest results, plots, metrics land here
└── research_note_template.md   # fill this in with your results
```

## Quickstart

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

# optional but recommended: free EIA API key (instant signup)
# https://www.eia.gov/opendata/register.php
export EIA_API_KEY=your_key_here

python src/main.py
```

Results (equity curve, per-commodity metrics, weights) will be written to
`output/`.

## Roadmap (suggested 3-4 week build)

1. **Week 1 — Data pipeline.** Get `data_pipeline.py` pulling clean daily
   prices for CL, NG, RB, HO and weekly EIA storage series. Sanity-check
   for missing days, stale data, contract rolls.
2. **Week 2 — Signals.** Build and visualize each signal independently
   before combining them. Check that carry actually flips sign around
   known contango/backwardation regimes (e.g., NG in shoulder months).
3. **Week 3 — Backtest.** Add vol-targeted position sizing, transaction
   costs, and compute Sharpe / max drawdown / hit rate per commodity and
   for the combined portfolio. Benchmark against buy-and-hold.
4. **Week 4 — Research note.** Fill in `research_note_template.md` with
   your actual results, thesis, and risk caveats. Clean up the README functions/README, and post the repo publicly.

## Notes on data

- `yfinance` continuous futures (`CL=F`, `NG=F`, `RB=F`, `HO=F`) are good
  enough for a front-month price series but do NOT give you a second
  contract month for a clean carry signal. `data_pipeline.py` includes a
  fallback that approximates carry using a seasonal-adjusted proxy, with
  a clearly marked spot to swap in real second-month futures data if you
  get access to a paid feed (or CME's free delayed quotes) later.
- EIA's API is free, well-documented, and exactly the data real traders
  watch (weekly nat gas storage Thursdays, crude/product inventories
  Wednesdays). Get a key at https://www.eia.gov/opendata/register.php.
