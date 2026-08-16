import pandas as pd
import numpy as np


class LiquidityAnalyzer:

    def __init__(
        self,
        swing_lookback=3,
        equal_tolerance=0.0002
    ):

        if swing_lookback < 1:
            raise ValueError(
                "swing_lookback must be >= 1"
            )

        if equal_tolerance < 0:
            raise ValueError(
                "equal_tolerance must be >= 0"
            )

        self.swing_lookback = int(
            swing_lookback
        )

        self.equal_tolerance = float(
            equal_tolerance
        )

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

        highs = df["high"].to_numpy(
            dtype=float
        )

        length = len(df)

        equal_high = np.zeros(
            length,
            dtype=bool
        )

        lookback = self.swing_lookback
        tolerance = self.equal_tolerance

        for i in range(
            lookback,
            length
        ):

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

        df["equal_high"] = (
            equal_high
        )

        return df

    # =========================================================
    # EQUAL LOWS
    # =========================================================

    def find_equal_lows(self, df):

        df = df.copy()

        lows = df["low"].to_numpy(
            dtype=float
        )

        length = len(df)

        equal_low = np.zeros(
            length,
            dtype=bool
        )

        lookback = self.swing_lookback
        tolerance = self.equal_tolerance

        for i in range(
            lookback,
            length
        ):

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

        df["equal_low"] = (
            equal_low
        )

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
    # A buy-side sweep occurs when:
    #
    # 1. Price has established buy-side liquidity.
    # 2. Price trades ABOVE that liquidity.
    # 3. Price CLOSES BACK BELOW that liquidity.
    #
    # This avoids treating a simple breakout as a sweep.
    # =========================================================

    def detect_buy_side_sweeps(
        self,
        df
    ):

        df = df.copy()

        highs = df["high"].to_numpy(
            dtype=float
        )

        closes = df["close"].to_numpy(
            dtype=float
        )

        equal_highs = df[
            "equal_high"
        ].to_numpy(
            dtype=bool
        )

        sweeps = np.zeros(
            len(df),
            dtype=bool
        )

        last_liquidity_high = None

        for i in range(len(df)):

            # -------------------------------------------------
            # Establish / update liquidity
            # -------------------------------------------------

            if equal_highs[i]:

                last_liquidity_high = (
                    highs[i]
                )

                continue

            # -------------------------------------------------
            # Detect sweep
            # -------------------------------------------------

            if (
                last_liquidity_high
                is not None
            ):

                swept_above = (
                    highs[i]
                    >
                    last_liquidity_high
                )

                closed_back_below = (
                    closes[i]
                    <
                    last_liquidity_high
                )

                if (
                    swept_above
                    and
                    closed_back_below
                ):

                    sweeps[i] = True

                    # Liquidity has been consumed.
                    last_liquidity_high = None

        df[
            "buy_side_sweep"
        ] = sweeps

        return df

    # =========================================================
    # SELL-SIDE LIQUIDITY SWEEPS
    # =========================================================
    #
    # A sell-side sweep occurs when:
    #
    # 1. Price has established sell-side liquidity.
    # 2. Price trades BELOW that liquidity.
    # 3. Price CLOSES BACK ABOVE that liquidity.
    #
    # This avoids treating a simple breakdown as a sweep.
    # =========================================================

    def detect_sell_side_sweeps(
        self,
        df
    ):

        df = df.copy()

        lows = df["low"].to_numpy(
            dtype=float
        )

        closes = df["close"].to_numpy(
            dtype=float
        )

        equal_lows = df[
            "equal_low"
        ].to_numpy(
            dtype=bool
        )

        sweeps = np.zeros(
            len(df),
            dtype=bool
        )

        last_liquidity_low = None

        for i in range(len(df)):

            # -------------------------------------------------
            # Establish / update liquidity
            # -------------------------------------------------

            if equal_lows[i]:

                last_liquidity_low = (
                    lows[i]
                )

                continue

            # -------------------------------------------------
            # Detect sweep
            # -------------------------------------------------

            if (
                last_liquidity_low
                is not None
            ):

                swept_below = (
                    lows[i]
                    <
                    last_liquidity_low
                )

                closed_back_above = (
                    closes[i]
                    >
                    last_liquidity_low
                )

                if (
                    swept_below
                    and
                    closed_back_above
                ):

                    sweeps[i] = True

                    # Liquidity has been consumed.
                    last_liquidity_low = None

        df[
            "sell_side_sweep"
        ] = sweeps

        return df

    # =========================================================
    # COMPLETE LIQUIDITY ANALYSIS
    # =========================================================

    def analyze(self, df):

        df = df.copy()

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
