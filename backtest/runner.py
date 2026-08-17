from pathlib import Path
import pandas as pd

from backtest.mtf_engine import MTFBacktestEngine
from backtest.metrics import calculate_metrics


def section(title):
    print()
    print("=" * 72)
    print(title.center(72))
    print("=" * 72)


def main():
    section("AUREUS AI V4\nA+ MARKET MECHANICS — ONE SETUP ONLY")
    print("Core model: 4H direction → 1H fresh POI → 15M market shift →")
    print("15M liquidity sweep → 10M market-shift confirmation → M5 execution.")
    print("Deliberately excluded from V4: FVG entries, OB entries, scoring stacks,")
    print("premium/discount triggers, double-zone breakout and multiple entry models.")

    path = Path(input("Enter M5 CSV file path: ").strip())
    if not path.exists():
        print("ERROR: File does not exist:", path)
        return

    df = pd.read_csv(path)
    section("DATA")
    print("Candles:", len(df))
    print("Columns:", list(df.columns))

    engine = MTFBacktestEngine(
        starting_balance=10000,
        risk_percent=1.0,
        minimum_rr=2.0,
        stop_buffer=0.00002,
        same_candle_priority="stop",
        progress_every=100_000,
    )

    try:
        trades, analysed, signal_map = engine.run(df)
    except Exception as exc:
        print("\nERROR while running AUREUS V4:", exc)
        raise

    metrics = calculate_metrics(trades)
    closed = [t for t in trades if t.get("result") in ("WIN", "LOSS")]

    section("AUREUS V4 RESULTS")
    for key, label in [
        ("total_trades", "Total trades"),
        ("wins", "Wins"),
        ("losses", "Losses"),
        ("win_rate", "Win rate"),
        ("profit_factor", "Profit factor"),
        ("net_result_R", "Net result (R)"),
        ("average_R", "Average R"),
        ("expectancy_R", "Expectancy (R)"),
        ("max_drawdown_R", "Max drawdown (R)"),
        ("best_trade_R", "Best trade (R)"),
        ("worst_trade_R", "Worst trade (R)"),
    ]:
        suffix = "%" if key == "win_rate" else ""
        print(f"{label}: {metrics[key]}{suffix}")

    print("Long trades:", sum(t["direction"] == "BUY" for t in closed))
    print("Short trades:", sum(t["direction"] == "SELL" for t in closed))

    section("SIGNALS")
    print("A+ actionable signals:", len(signal_map))
    print("BUY signals:", engine.signal_count["BUY"])
    print("SELL signals:", engine.signal_count["SELL"])
    print("WAIT candles:", engine.signal_count["WAIT"])

    section("TIMEFRAME STATUS")
    for tf in ("1d", "4h", "1h", "15m", "10m"):
        frame = analysed[tf]
        print(f"{tf.upper():>3} bars: {len(frame)} | bias: {frame['trend_state'].iloc[-1]}")

    section("ONE-SETUP DIAGNOSTICS")
    print("4H bullish CHOCH:", int(analysed["4h"]["bullish_choch"].astype(bool).sum()))
    print("4H bearish CHOCH:", int(analysed["4h"]["bearish_choch"].astype(bool).sum()))
    print("1H fresh bullish POIs:", int(analysed["1h"]["bullish_poi_available"].astype(bool).sum()))
    print("1H fresh bearish POIs:", int(analysed["1h"]["bearish_poi_available"].astype(bool).sum()))
    print("15M sell-side sweeps:", int(analysed["15m"]["sell_side_sweep"].astype(bool).sum()))
    print("15M buy-side sweeps:", int(analysed["15m"]["buy_side_sweep"].astype(bool).sum()))

    section("TRADE SAMPLE")
    print(pd.DataFrame(closed[:10]).to_string(index=False) if closed else "No closed trades.")

    section("BACKTEST COMPLETE")


if __name__ == "__main__":
    main()
