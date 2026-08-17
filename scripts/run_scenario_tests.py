from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd

from backtest.mtf_engine import MTFBacktestEngine
from strategy.top_down import TopDownStrategy
from strategy.timeframes import build_mtf_data


SCENARIO_DIR = ROOT / "data" / "test_scenarios"
CSV = SCENARIO_DIR / "Aplus_bullish_golden.csv"
MANIFEST = SCENARIO_DIR / "Aplus_bullish_golden.json"


def main():
    print("=" * 72)
    print("AUREUS V4 — A+ GOLDEN SCENARIO TEST")
    print("=" * 72)

    df = pd.read_csv(CSV)
    print(f"Loaded synthetic M5 candles: {len(df):,}")
    print(f"Start: {df['timestamp'].iloc[0]}")
    print(f"End:   {df['timestamp'].iloc[-1]}")

    mtf = build_mtf_data(df)
    strategy = TopDownStrategy()
    analysed = strategy.prepare(mtf)

    checks = {}

    checks["4H bullish bias"] = (
        str(analysed["4h"]["trend_state"].iloc[-1]).lower() == "bullish"
    )

    h1_poi_rows = analysed["1h"][
        analysed["1h"]["bullish_poi_available"].astype(bool)
    ]
    checks["1H bullish POI detected"] = len(h1_poi_rows) > 0

    shift_rows = analysed["15m"][
        analysed["15m"]["bullish_choch"].astype(bool)
    ]
    checks["15M bullish CHOCH detected"] = len(shift_rows) > 0

    sweep_rows = analysed["15m"][
        analysed["15m"]["sell_side_sweep"].astype(bool)
    ]
    checks["15M sell-side sweep detected"] = len(sweep_rows) > 0

    entry_shift_rows = analysed["10m"][
        analysed["10m"]["bullish_choch"].astype(bool)
    ]
    checks["10M bullish CHOCH detected"] = len(entry_shift_rows) > 0

    signal_map, _ = strategy.run_signals(mtf)
    checks["A+ BUY signal generated"] = len(signal_map) > 0

    print("\nDETECTED EVENTS")
    print("-" * 72)

    if len(h1_poi_rows):
        print(
            "1H POI:",
            h1_poi_rows[
                ["bar_close_time", "bullish_poi_high", "bullish_poi_low"]
            ].tail(3).to_string(index=False),
        )
    else:
        print("1H POI: NOT DETECTED")

    if len(shift_rows):
        print(
            "15M CHOCH:",
            shift_rows[
                ["bar_close_time", "close"]
            ].tail(5).to_string(index=False),
        )
    else:
        print("15M CHOCH: NOT DETECTED")

    if len(sweep_rows):
        print(
            "15M SWEEP:",
            sweep_rows[
                ["bar_close_time", "close", "sell_side_sweep_level"]
            ].tail(5).to_string(index=False),
        )
    else:
        print("15M SWEEP: NOT DETECTED")

    if len(entry_shift_rows):
        print(
            "10M CHOCH:",
            entry_shift_rows[
                ["bar_close_time", "close"]
            ].tail(5).to_string(index=False),
        )
    else:
        print("10M CHOCH: NOT DETECTED")

    print("\nCHECKLIST")
    print("-" * 72)
    for name, ok in checks.items():
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")

    print("\nA+ SIGNALS")
    print("-" * 72)
    if signal_map:
        for idx, setup in signal_map.items():
            print(
                f"index={idx} "
                f"signal={setup.signal} "
                f"entry={setup.entry:.5f} "
                f"stop={setup.stop:.5f} "
                f"target={setup.target:.5f} "
                f"RR={setup.planned_rr:.2f}"
            )
            print("reasons:", " | ".join(setup.reasons))
    else:
        print("NO A+ SIGNAL GENERATED.")

    print("\nIMPORTANT")
    print("-" * 72)
    print(
        "A PASS on every event is required before trusting the strategy "
        "against historical EURUSD data."
    )
    print(
        "A FAIL is useful: it tells us exactly which stage of the single "
        "A+ model the engine does not yet reproduce."
    )


if __name__ == "__main__":
    main()
