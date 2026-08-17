import numpy as np
import pandas as pd


class LiquidityAnalyzer:
    """
    AUREUS V2 liquidity map.

    Focuses on practical, objective liquidity:
      - equal highs/lows from confirmed swings
      - confirmed swing liquidity
      - first clean sweep/reclaim event

    All liquidity becomes available only after the underlying swing is
    confirmed. Sweeps use the current candle's wick and close.
    """

    def __init__(
        self,
        swing_lookback=3,
        equal_tolerance=20.0,
        minimum_separation=3,
        liquidity_expiry=120,
    ):
        self.swing_lookback = int(swing_lookback)
        self.equal_tolerance = float(equal_tolerance)
        self.minimum_separation = int(minimum_separation)
        self.liquidity_expiry = int(liquidity_expiry)
        if self.swing_lookback < 1:
            raise ValueError("swing_lookback must be >= 1")
        if self.minimum_separation < 1:
            raise ValueError("minimum_separation must be >= 1")

    def add_columns(self, df):
        df = df.copy()
        bool_cols = [
            "equal_high", "equal_low",
            "buy_side_liquidity", "sell_side_liquidity",
            "buy_side_sweep", "sell_side_sweep",
            "buy_side_sweep_reclaim", "sell_side_sweep_reclaim",
        ]
        float_cols = [
            "equal_high_level", "equal_low_level",
            "buy_side_sweep_level", "sell_side_sweep_level",
        ]
        for c in bool_cols:
            if c not in df.columns:
                df[c] = False
        for c in float_cols:
            if c not in df.columns:
                df[c] = np.nan
        return df

    def _confirmed_prices(self, df, side):
        if side == "high":
            flag = "confirmed_swing_high"
            price = "swing_high_price"
        else:
            flag = "confirmed_swing_low"
            price = "swing_low_price"
        if flag not in df.columns:
            raise ValueError("LiquidityAnalyzer requires MarketStructure confirmation columns")
        return df[flag].to_numpy(dtype=bool), df[price].to_numpy(dtype=float)

    def _equal_levels(self, df, side):
        flags, prices = self._confirmed_prices(df, side)
        n = len(df)
        equal = np.zeros(n, dtype=bool)
        levels = np.full(n, np.nan)
        previous = []

        for i in range(n):
            previous = [x for x in previous if i - x[0] <= self.liquidity_expiry]
            if not flags[i] or not np.isfinite(prices[i]):
                continue
            current = float(prices[i])
            match = None
            for j, prev_price in reversed(previous):
                if i - j < self.minimum_separation:
                    continue
                if abs(current - prev_price) <= self.equal_tolerance:
                    match = (current + prev_price) / 2.0
                    break
            if match is not None:
                equal[i] = True
                levels[i] = match
            previous.append((i, current))

        return equal, levels

    def _sweep(self, df, side, equal_flag, equal_level):
        n = len(df)
        sweeps = np.zeros(n, dtype=bool)
        sweep_level = np.full(n, np.nan)
        active = []

        highs = df["high"].to_numpy(dtype=float)
        lows = df["low"].to_numpy(dtype=float)
        closes = df["close"].to_numpy(dtype=float)

        candidate_col = "candidate_high" if side == "high" else "candidate_low"
        if candidate_col in df.columns:
            candidate = df[candidate_col].to_numpy(dtype=float)
        else:
            _, candidate = self._confirmed_prices(df, side)

        last_candidate = np.nan

        for i in range(n):
            # Equal liquidity gets priority. Otherwise the latest known
            # structure level is available liquidity.
            if equal_flag[i] and np.isfinite(equal_level[i]):
                last_candidate = float(equal_level[i])
                active.append({"created_at": i, "level": last_candidate})
            elif np.isfinite(candidate[i]) and (not np.isfinite(last_candidate) or float(candidate[i]) != last_candidate):
                last_candidate = float(candidate[i])
                active.append({"created_at": i, "level": last_candidate})

            active = [
                p for p in active
                if i - p["created_at"] <= self.liquidity_expiry
            ]

            for p in list(active):
                if i <= p["created_at"]:
                    continue
                level = p["level"]
                if side == "high":
                    qualifies = highs[i] > level and closes[i] < level
                else:
                    qualifies = lows[i] < level and closes[i] > level
                if qualifies:
                    sweeps[i] = True
                    sweep_level[i] = level
                    active.remove(p)
                    break

        return sweeps, sweep_level

    def analyze(self, df):
        df = self.add_columns(df.copy())
        high_eq, high_level = self._equal_levels(df, "high")
        low_eq, low_level = self._equal_levels(df, "low")

        buy_sweep, buy_level = self._sweep(df, "high", high_eq, high_level)
        sell_sweep, sell_level = self._sweep(df, "low", low_eq, low_level)

        df["equal_high"] = high_eq
        df["equal_low"] = low_eq
        df["equal_high_level"] = high_level
        df["equal_low_level"] = low_level
        df["buy_side_liquidity"] = high_eq
        df["sell_side_liquidity"] = low_eq
        df["buy_side_sweep"] = buy_sweep
        df["sell_side_sweep"] = sell_sweep
        df["buy_side_sweep_reclaim"] = buy_sweep
        df["sell_side_sweep_reclaim"] = sell_sweep
        df["buy_side_sweep_level"] = buy_level
        df["sell_side_sweep_level"] = sell_level
        return df
