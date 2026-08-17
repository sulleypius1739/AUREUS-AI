"""AUREUS V4 - one mechanical A+ market-mechanics setup.

Source basis: the supplied market-mechanics transcript.

Core sequence only:
    4H direction -> fresh 1H pro-trend POI -> 15M internal market shift ->
    15M liquidity sweep -> 10M same-direction market shift at the POI -> M5 execution.

Daily is context-only. FVG entries, OB entries, premium/discount triggers,
multiple scoring stacks, double-zone breakouts and multiple setup models are
intentionally excluded from V4.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

import numpy as np
import pandas as pd

from strategy.liquidity import LiquidityAnalyzer
from strategy.market_structure import MarketStructure
from strategy.timeframes import MultiTimeframeData
from strategy.zones import ZoneAnalyzer


@dataclass
class Setup:
    signal: str
    direction: Optional[str]
    score: int
    reasons: list[str]
    entry: float
    stop: float
    target: float
    timeframe: str
    daily_bias: str
    h4_bias: str
    h1_bias: str
    setup_zone_high: float
    setup_zone_low: float
    planned_rr: float


class TopDownStrategy:
    """Single A+ setup: HTF direction + POI + internal shift + sweep."""

    def __init__(
        self,
        swing_length: int = 3,
        equal_tolerance: float = 0.00015,
        fvg_min_size: float = 0.00005,
        minimum_rr: float = 2.0,
        risk_percent: float = 1.0,
        stop_buffer: float = 0.00002,
    ):
        self.swing_length = int(swing_length)
        self.equal_tolerance = float(equal_tolerance)
        self.fvg_min_size = float(fvg_min_size)
        self.minimum_rr = float(minimum_rr)
        self.risk_percent = float(risk_percent)
        self.stop_buffer = float(stop_buffer)

    @staticmethod
    def _bias(row: Optional[pd.Series]) -> str:
        if row is None:
            return "neutral"
        value = str(row.get("trend_state", "neutral")).lower()
        return value if value in {"bullish", "bearish", "neutral"} else "neutral"

    def _structure(self, frame: pd.DataFrame) -> pd.DataFrame:
        data, _ = MarketStructure(self.swing_length).analyze(frame.copy())
        return data

    def _internal(self, frame: pd.DataFrame) -> pd.DataFrame:
        data = self._structure(frame)
        return LiquidityAnalyzer(
            swing_lookback=self.swing_length,
            equal_tolerance=self.equal_tolerance,
            minimum_separation=2,
            liquidity_expiry=80,
        ).analyze(data)

    def _poi(self, frame: pd.DataFrame) -> pd.DataFrame:
        data = self._structure(frame)
        data = LiquidityAnalyzer(
            swing_lookback=self.swing_length,
            equal_tolerance=self.equal_tolerance,
            minimum_separation=2,
            liquidity_expiry=120,
        ).analyze(data)
        return ZoneAnalyzer(
            fvg_min_size=self.fvg_min_size,
            displacement_multiplier=1.35,
            baseline_window=20,
        ).analyze(data)

    def prepare(self, mtf: MultiTimeframeData) -> Dict[str, pd.DataFrame]:
        return {
            "1d": self._structure(mtf.frames["1d"]),
            "4h": self._structure(mtf.frames["4h"]),
            "1h": self._poi(mtf.frames["1h"]),
            "15m": self._internal(mtf.frames["15m"]),
            "10m": self._internal(mtf.frames["10m"]),
        }

    @staticmethod
    def _target(h1_row: pd.Series, direction: str, entry: float):
        cols = (
            ("last_major_high", "candidate_high", "swing_high_price")
            if direction == "bullish"
            else ("last_major_low", "candidate_low", "swing_low_price")
        )
        for col in cols:
            if col in h1_row.index:
                value = h1_row.get(col, np.nan)
                try:
                    value = float(value)
                except (TypeError, ValueError):
                    continue
                if not np.isfinite(value):
                    continue
                if direction == "bullish" and value > entry:
                    return value
                if direction == "bearish" and value < entry:
                    return value
        return None

    def _setup(
        self,
        price: float,
        direction: str,
        daily_bias: str,
        h4_bias: str,
        h1_row: pd.Series,
        poi: dict,
    ) -> Optional[Setup]:
        if not (poi["low"] <= price <= poi["high"]):
            return None

        stop = poi["low"] - self.stop_buffer if direction == "bullish" else poi["high"] + self.stop_buffer
        target = self._target(h1_row, direction, price)
        if target is None:
            # Baseline V4 execution fallback: use the opposite edge of the
            # active POI as the first mechanical target. Higher-timeframe
            # structural targets can be added later as a separate refinement.
            target = poi["high"] if direction == "bullish" else poi["low"]

        risk = abs(price - stop)
        if risk <= 0:
            return None
        rr = abs(target - price) / risk

        reasons = [
            f"4H direction: {h4_bias}",
            f"Fresh {poi['name']}",
            "15M internal market shift",
            "15M liquidity sweep",
            "10M same-direction market shift",
            "Price mitigated the POI",
            f"1H structural target: {target:.5f}",
            f"Planned RR: {rr:.2f}",
        ]
        return Setup(
            signal="BUY" if direction == "bullish" else "SELL",
            direction=direction,
            score=100,
            reasons=reasons,
            entry=float(price),
            stop=float(stop),
            target=float(target),
            timeframe="10m",
            daily_bias=daily_bias,
            h4_bias=h4_bias,
            h1_bias=self._bias(h1_row),
            setup_zone_high=float(poi["high"]),
            setup_zone_low=float(poi["low"]),
            planned_rr=float(rr),
        )

    def run_signals(self, mtf: MultiTimeframeData):
        analysed = self.prepare(mtf)
        signal_map: Dict[int, Setup] = {}
        base = mtf.base
        n = len(base)

        # Pointer arrays are precomputed once; the main M5 walk only advances
        # state when a higher timeframe bar changes.
        m5_close = base["bar_close_time"].to_numpy(dtype="datetime64[ns]")
        m5_price = base["close"].to_numpy(dtype=float)
        ptr = {}
        for name, frame in analysed.items():
            closes = frame["bar_close_time"].to_numpy(dtype="datetime64[ns]")
            ptr[name] = np.searchsorted(closes, m5_close, side="right") - 1

        current = {name: None for name in analysed}
        last_ptr = {name: -1 for name in analysed}

        active_poi = None
        active_poi_key = None
        armed_direction = None
        shift_time = None
        sweep_seen = False
        entry_shift_seen = False
        traded_poi_key = None

        for i in range(n - 1):
            # Advance timeframe state only when its closed bar changes.
            changed = []
            for name in ("1d", "4h", "1h", "15m", "10m"):
                p = int(ptr[name][i])
                if p != last_ptr[name]:
                    last_ptr[name] = p
                    current[name] = analysed[name].iloc[p] if p >= 0 else None
                    changed.append(name)

            drow = current["1d"]
            h4row = current["4h"]
            h1row = current["1h"]
            row15 = current["15m"]
            row10 = current["10m"]
            if h4row is None or h1row is None or row15 is None or row10 is None:
                continue

            daily_bias = self._bias(drow)
            h4_bias = self._bias(h4row)
            h1_bias = self._bias(h1row)
            ts = pd.Timestamp(base.iloc[i]["bar_close_time"])
            price = float(m5_price[i])

            if h4_bias not in {"bullish", "bearish"}:
                active_poi = None
                armed_direction = None
                shift_time = None
                sweep_seen = False
                entry_shift_seen = False
                continue

            # New 1H POI becomes the only active high-priority zone for V4.
            if "1h" in changed:
                if h4_bias == "bullish" and bool(h1row.get("bullish_poi_available", False)):
                    hi = h1row.get("bullish_poi_high", np.nan)
                    lo = h1row.get("bullish_poi_low", np.nan)
                    if np.isfinite(hi) and np.isfinite(lo):
                        active_poi = {"name": "Bullish POI", "high": float(hi), "low": float(lo), "created": h1row["bar_close_time"]}
                        active_poi_key = (active_poi["created"], active_poi["name"], active_poi["high"], active_poi["low"])
                elif h4_bias == "bearish" and bool(h1row.get("bearish_poi_available", False)):
                    hi = h1row.get("bearish_poi_high", np.nan)
                    lo = h1row.get("bearish_poi_low", np.nan)
                    if np.isfinite(hi) and np.isfinite(lo):
                        active_poi = {"name": "Bearish POI", "high": float(hi), "low": float(lo), "created": h1row["bar_close_time"]}
                        active_poi_key = (active_poi["created"], active_poi["name"], active_poi["high"], active_poi["low"])

                # A touch/retest does not consume the POI by itself. The A+
                # sequence still requires the market-shift and liquidity-sweep
                # confirmation before the POI is eligible for execution.

            # 15M market shift is the trigger that ends the internal pullback.
            if "15m" in changed:
                shift = bool(row15.get("bullish_choch" if h4_bias == "bullish" else "bearish_choch", False))
                if shift:
                    armed_direction = h4_bias
                    shift_time = ts
                    sweep_seen = False

                # Liquidity sweep must happen after the market shift.
                if armed_direction == h4_bias and shift_time is not None:
                    sweep = bool(row15.get("sell_side_sweep" if h4_bias == "bullish" else "buy_side_sweep", False))
                    if sweep and row15["bar_close_time"] > shift_time:
                        sweep_seen = True

            if active_poi is None or armed_direction != h4_bias or not sweep_seen:
                continue

            if active_poi_key == traded_poi_key:
                continue

            # 10M same-direction market shift is the single entry confirmation.
            if "10m" in changed:
                entry_shift = bool(row10.get("bullish_choch" if h4_bias == "bullish" else "bearish_choch", False))
                if entry_shift and row10["bar_close_time"] > shift_time:
                    entry_shift_seen = True

            if not entry_shift_seen:
                continue

            # M5 is the execution timeframe: after 10M confirmation, wait for
            # the next causal M5 close inside the active POI.
            if not (active_poi["low"] <= price <= active_poi["high"]):
                continue

            setup = self._setup(price, h4_bias, daily_bias, h4_bias, h1row, active_poi)
            if setup is None:
                continue

            signal_map[i] = setup
            traded_poi_key = active_poi_key
            active_poi = None
            active_poi_key = None
            armed_direction = None
            shift_time = None
            sweep_seen = False
            entry_shift_seen = False

        return signal_map, analysed
