import pandas as pd
import numpy as np


class LiquidityAnalyzer:

    def __init__(
        self,
        swing_lookback=3,
        equal_tolerance=0.0002
    ):

        self.swing_lookback = swing_lookback
        self.equal_tolerance = equal_tolerance

    # =========================================================
    # PREPARE COLUMNS
    # =========================================================

    def add_columns(self, df):

        df = df.copy()

        columns = [
            "equal_high",
            "equal_low",
            "buy_side_liquidity",
            "sell_side_liquidity",
            "buy_side_sweep",
            "sell_side_sweep"
        ]

        for column in columns:

            if column not in df.columns:

                df[column] = False

        return df

    # =========================================================
    # EQUAL HIGHS
    # =========================================================

    def find_equal_highs(self, df):

        df = df.copy()

        highs = df["high"].to_numpy()

        equal_high = np.zeros(
            len(df),
            dtype=bool
        )

        lookback = self.swing_lookback

        tolerance = self.equal_tolerance

        for i in range(lookback, len(df)):

            current_high = highs[i]

            previous_highs = highs[
                i - lookback:i
            ]

            difference = np.abs(
                previous_highs
                -
                current_high
            )

            relative_difference = (
                difference
                /
                np.maximum(
                    np.abs(current_high),
                    1e-12
                )
            )

            if np.any(
                relative_difference
                <=
                tolerance
            ):

                equal_high[i] = True

        df["equal_high"] = equal_high

        return df

    # =========================================================
    # EQUAL LOWS
    # =========================================================

    def find_equal_lows(self, df):

        df = df.copy()

        lows = df["low"].to_numpy()

        equal_low = np.zeros(
            len(df),
            dtype=bool
        )

        lookback = self.swing_lookback

        tolerance = self.equal_tolerance

        for i in range(lookback, len(df)):

            current_low = lows[i]

            previous_lows = lows[
                i - lookback:i
            ]

            difference = np.abs(
                previous_lows
                -
                current_low
            )

            relative_difference = (
                difference
                /
                np.maximum(
                    np.abs(current_low),
                    1e-12
                )
            )

            if np.any(
                relative_difference
                <=
                tolerance
            ):

                equal_low[i] = True

        df["equal_low"] = equal_low

        return df

    # =========================================================
    # BUY-SIDE LIQUIDITY
    # =========================================================

    def identify_buy_side_liquidity(
        self,
        df
    ):

        df = df.copy()

        df["buy_side_liquidity"] = (
            df["equal_high"]
        )

        return df

    # =========================================================
    # SELL-SIDE LIQUIDITY
    # =========================================================

    def identify_sell_side_liquidity(
        self,
        df
    ):

        df = df.copy()

        df["sell_side_liquidity"] = (
            df["equal_low"]
        )

        return df

    # =========================================================
    # BUY-SIDE LIQUIDITY SWEEP
    # =========================================================
    #
    # Price trades above a previous liquidity high and then
    # closes back below that level.
    #
    # This is a basic sweep definition.
    # =========================================================

    def detect_buy_side_sweeps(
        self,
        df
    ):

        df = df.copy()

        highs = df["high"].to_numpy()
        closes = df["close"].to_numpy()

        equal_highs = df[
            "equal_high"
        ].to_numpy()

        sweeps = np.zeros(
            len(df),
            dtype=bool
        )

        last_liquidity_high = None

        for i in range(len(df)):

            if equal_highs[i]:

                last_liquidity_high = highs[i]

            if (
                last_liquidity_high
                is not None
            ):

                if (
                    highs[i]
                    >
                    last_liquidity_high
                    and
                    closes[i]
                    <
                    last_liquidity_high
                ):

                    sweeps[i] = True

                    last_liquidity_high = None

        df[
            "buy_side_sweep"
        ] = sweeps

        return df

    # =========================================================
    # SELL-SIDE LIQUIDITY SWEEP
    # =========================================================
    #
    # Price trades below a previous liquidity low and then
    # closes back above that level.
    # =========================================================

    def detect_sell_side_sweeps(
        self,
        df
    ):

        df = df.copy()

        lows = df["low"].to_numpy()
        closes = df["close"].to_numpy()

        equal_lows = df[
            "equal_low"
        ].to_numpy()

        sweeps = np.zeros(
            len(df),
            dtype=bool
        )

        last_liquidity_low = None

        for i in range(len(df)):

            if equal_lows[i]:

                last_liquidity_low = lows[i]

            if (
                last_liquidity_low
                is not None
            ):

                if (
                    lows[i]
                    <
                    last_liquidity_low
                    and
                    closes[i]
                    >
                    last_liquidity_low
                ):

                    sweeps[i] = True

                    last_liquidity_low = None

        df[
            "sell_side_sweep"
        ] = sweeps

        return df

    # =========================================================
    # COMPLETE LIQUIDITY ANALYSIS
    # =========================================================

    def analyze(self, df):

        df = self.add_columns(df)

        df = self.find_equal_highs(df)

        df = self.find_equal_lows(df)

        df = self.identify_buy_side_liquidity(
            df
        )

        df = self.identify_sell_side_liquidity(
            df
        )

        df = self.detect_buy_side_sweeps(
            df
        )

        df = self.detect_sell_side_sweeps(
            df
        )

        return df
