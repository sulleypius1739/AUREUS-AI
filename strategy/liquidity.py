import pandas as pd
import numpy as np


class LiquidityAnalyzer:

    def __init__(
        self,
        swing_lookback=3,
        equal_tolerance=0.0002,
        liquidity_expiry=200
    ):
        # swing_lookback kept for backward compatibility with
        # any external callers, but is no longer used directly —
        # equal highs/lows now come from confirmed swings, not
        # a fixed raw-candle window.
        self.swing_lookback = swing_lookback
        self.equal_tolerance = equal_tolerance
        self.liquidity_expiry = liquidity_expiry

    def add_columns(self, df):
        df = df.copy()

        bool_columns = [
            "equal_high",
            "equal_low",
            "buy_side_liquidity",
            "sell_side_liquidity",
            "buy_side_sweep",
            "sell_side_sweep"
        ]

        for column in bool_columns:
            if column not in df.columns:
                df[column] = False

        level_columns = [
            "equal_high_level",
            "equal_low_level"
        ]

        for column in level_columns:
            if column not in df.columns:
                df[column] = np.nan

        return df

    # =========================================================
    # EQUAL HIGHS
    # =========================================================
    #
    # CRITICAL FIX
    # ------------
    # Previously this compared every candle's raw high against
    # the last 3 raw candle highs — detecting minor chop, not
    # real liquidity pools.
    #
    # Now: a liquidity level requires TWO CONFIRMED swing highs
    # (from market_structure.py) within tolerance of each
    # other. The level only becomes "live" at the index where
    # the SECOND swing confirms — never before.
    # =========================================================

    def find_equal_highs(self, df):
        df = df.copy()
        length = len(df)

        if "swing_high_confirmed" not in df.columns:
            raise ValueError(
                "LiquidityAnalyzer requires market structure "
                "columns (swing_high_confirmed, swing_high_price). "
                "Run MarketStructure.analyze() before LiquidityAnalyzer."
            )

        swing_high_confirmed = df["swing_high_confirmed"].to_numpy()
        swing_high_price = df["swing_high_price"].to_numpy()

        equal_high = np.zeros(length, dtype=bool)
        equal_high_level = np.full(length, np.nan)

        recent_highs = []  # list of (confirmed_index, price)

        for i in range(length):

            if swing_high_confirmed[i]:

                price = swing_high_price[i]

                recent_highs = [
                    (idx, p)
                    for idx, p in recent_highs
                    if i - idx <= self.liquidity_expiry
                ]

                matched_price = None

                for idx, p in recent_highs:

                    relative_difference = (
                        abs(p - price) / max(abs(price), 1e-12)
                    )

                    if relative_difference <= self.equal_tolerance:
                        matched_price = p
                        break

                if matched_price is not None:
                    equal_high[i] = True
                    equal_high_level[i] = (matched_price + price) / 2

                recent_highs.append((i, price))

        df["equal_high"] = equal_high
        df["equal_high_level"] = equal_high_level

        return df

    # =========================================================
    # EQUAL LOWS
    # =========================================================
    #
    # Same causal fix, mirrored for lows.
    # =========================================================

    def find_equal_lows(self, df):
        df = df.copy()
        length = len(df)

        if "swing_low_confirmed" not in df.columns:
            raise ValueError(
                "LiquidityAnalyzer requires market structure "
                "columns (swing_low_confirmed, swing_low_price). "
                "Run MarketStructure.analyze() before LiquidityAnalyzer."
            )

        swing_low_confirmed = df["swing_low_confirmed"].to_numpy()
        swing_low_price = df["swing_low_price"].to_numpy()

        equal_low = np.zeros(length, dtype=bool)
        equal_low_level = np.full(length, np.nan)

        recent_lows = []

        for i in range(length):

            if swing_low_confirmed[i]:

                price = swing_low_price[i]

                recent_lows = [
                    (idx, p)
                    for idx, p in recent_lows
                    if i - idx <= self.liquidity_expiry
                ]

                matched_price = None

                for idx, p in recent_lows:

                    relative_difference = (
                        abs(p - price) / max(abs(price), 1e-12)
                    )

                    if relative_difference <= self.equal_tolerance:
                        matched_price = p
                        break

                if matched_price is not None:
                    equal_low[i] = True
                    equal_low_level[i] = (matched_price + price) / 2

                recent_lows.append((i, price))

        df["equal_low"] = equal_low
        df["equal_low_level"] = equal_low_level

        return df

    def identify_buy_side_liquidity(self, df):
        df = df.copy()
        df["buy_side_liquidity"] = df["equal_high"]
        return df

    def identify_sell_side_liquidity(self, df):
        df = df.copy()
        df["sell_side_liquidity"] = df["equal_low"]
        return df

    # =========================================================
    # BUY-SIDE LIQUIDITY SWEEP
    # =========================================================
    #
    # Price trades above a previously CONFIRMED equal-high
    # liquidity level, then closes back below it. Uses
    # equal_high_level — the real liquidity price — not
    # whatever the flagged candle's raw high happened to be.
    # =========================================================

    def detect_buy_side_sweeps(self, df):
        df = df.copy()
        length = len(df)

        highs = df["high"].to_numpy()
        closes = df["close"].to_numpy()
        equal_highs = df["equal_high"].to_numpy()
        equal_high_level = df["equal_high_level"].to_numpy()

        sweeps = np.zeros(length, dtype=bool)

        last_liquidity_high = None

        for i in range(length):

            if equal_highs[i]:
                last_liquidity_high = equal_high_level[i]

            if last_liquidity_high is not None:

                if (
                    highs[i] > last_liquidity_high
                    and closes[i] < last_liquidity_high
                ):
                    sweeps[i] = True
                    last_liquidity_high = None

        df["buy_side_sweep"] = sweeps
        return df

    # =========================================================
    # SELL-SIDE LIQUIDITY SWEEP
    # =========================================================

    def detect_sell_side_sweeps(self, df):
        df = df.copy()
        length = len(df)

        lows = df["low"].to_numpy()
        closes = df["close"].to_numpy()
        equal_lows = df["equal_low"].to_numpy()
        equal_low_level = df["equal_low_level"].to_numpy()

        sweeps = np.zeros(length, dtype=bool)

        last_liquidity_low = None

        for i in range(length):

            if equal_lows[i]:
                last_liquidity_low = equal_low_level[i]

            if last_liquidity_low is not None:

                if (
                    lows[i] < last_liquidity_low
                    and closes[i] > last_liquidity_low
                ):
                    sweeps[i] = True
                    last_liquidity_low = None

        df["sell_side_sweep"] = sweeps
        return df

    def analyze(self, df):
        df = self.add_columns(df)
        df = self.find_equal_highs(df)
        df = self.find_equal_lows(df)
        df = self.identify_buy_side_liquidity(df)
        df = self.identify_sell_side_liquidity(df)
        df = self.detect_buy_side_sweeps(df)
        df = self.detect_sell_side_sweeps(df)
        return df
