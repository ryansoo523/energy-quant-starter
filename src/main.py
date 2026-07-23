"""
End-to-end runner: pulls data, builds signals, runs the backtest, and
saves an equity curve plot + metrics table to output/.

    python src/main.py
"""

import os

import matplotlib
matplotlib.use("Agg")  # headless-safe backend
import matplotlib.pyplot as plt

import config
import data_pipeline
import signals
import backtest


def main():
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)

    print("1/4  Fetching data...")
    prices, storage = data_pipeline.load_all()
    print(f"     Loaded {len(prices)} days of prices for {list(prices.columns)}")

    print("2/4  Building signals...")
    composite = signals.combine_signals(prices)

    print("3/4  Running backtest...")
    result = backtest.run_backtest(prices, composite)
    bh = backtest.buy_and_hold_benchmark(prices)

    print("4/4  Saving results to output/...")
    result["metrics"].to_csv(os.path.join(config.OUTPUT_DIR, "strategy_metrics.csv"))
    bh["metrics"].to_csv(os.path.join(config.OUTPUT_DIR, "benchmark_metrics.csv"))
    result["positions"].to_csv(os.path.join(config.OUTPUT_DIR, "positions.csv"))

    # Equity curve plot: strategy vs. buy-and-hold
    strat_curve = (1 + result["portfolio_returns"].fillna(0)).cumprod()
    bh_curve = (1 + bh["portfolio_returns"].fillna(0)).cumprod()

    fig, ax = plt.subplots(figsize=(10, 5))
    strat_curve.plot(ax=ax, label="Strategy (net of costs)")
    bh_curve.plot(ax=ax, label="Buy & Hold Benchmark")
    ax.set_title("Cross-Commodity Term Structure & Momentum Strategy")
    ax.set_ylabel("Growth of $1")
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(config.OUTPUT_DIR, "equity_curve.png"), dpi=150)

    print("\n=== Strategy metrics ===")
    print(result["metrics"])
    print("\n=== Benchmark metrics ===")
    print(bh["metrics"])
    print(f"\nDone. See {config.OUTPUT_DIR}/ for equity_curve.png and metrics CSVs.")


if __name__ == "__main__":
    main()
