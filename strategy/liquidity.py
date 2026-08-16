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

        highs = pd.to_numeric(
            df["high"],
            errors="coerce"
        ).to_numpy(dtype=float)

        equal_high = np.zeros(
            len(df),
            dtype=bool
        )

        lookback = self.swing_lookback

        tolerance = self.equal_tolerance

        for i in range(
            lookback,
            len(df)
        ):

            current_high = highs[i]

            if not np.isfinite(
                current_high
            ):
                continue

            previous_highs = highs[
                i - lookback:i
            ]

            valid_previous = (
                previous_highs[
                    np.isfinite(
                        previous_highs
                    )
                ]
            )

            if len(valid_previous) == 0:
                continue

            difference = np.abs(
                valid_previous
                -
                current_high
            )

            relative_difference = (
                difference
                /
                max(
                    abs(current_high),
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

        lows = pd.to_numeric(
            df["low"],
            errors="coerce"
        ).to_numpy(dtype=float)

        equal_low = np.zeros(
            len(df),
            dtype=bool
        )

        lookback = self.swing_lookback

        tolerance = self.equal_tolerance

        for i in range(
            lookback,
            len(df)
        ):

            current_low = lows[i]

            if not np.isfinite(
                current_low
            ):
                continue

            previous_lows = lows[
                i - lookback:i
            ]

            valid_previous = (
                previous_lows[
                    np.isfinite(
                        previous_lows
                    )
                ]
            )

            if len(valid_previous) == 0:
                continue

            difference = np.abs(
                valid_previous
                -
                current_low
            )

            relative_difference = (
                difference
                /
                max(
                    abs(current_low),
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
            .astype(bool)
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
            .astype(bool)
        )

        return df

    # =========================================================
    # BUY-SIDE LIQUIDITY SWEEP
    # =========================================================
    #
    # Buy-side liquidity sits above highs.
    #
    # A bearish buy-side sweep occurs when:
    #
    # 1. Price trades ABOVE the liquidity level.
    # 2. The candle CLOSES BACK BELOW the level.
    #
    # This prevents simply calling every breakout a sweep.
    # =========================================================

    def detect_buy_side_sweeps(
        self,
        df
    ):

        df = df.copy()

        highs = pd.to_numeric(
            df["high"],
            errors="coerce"
        ).to_numpy(dtype=float)

        closes = pd.to_numeric(
            df["close"],
            errors="coerce"
        ).to_numpy(dtype=float)

        equal_highs = (
            df["equal_high"]
            .to_numpy(dtype=bool)
        )

        sweeps = np.zeros(
            len(df),
            dtype=bool
        )

        last_liquidity_high = None

        for i in range(
            len(df)
        ):

            # -------------------------------------------------
            # Register new liquidity
            # -------------------------------------------------

            if equal_highs[i]:

                if np.isfinite(
                    highs[i]
                ):

                    last_liquidity_high = (
                        highs[i]
                    )

                # Do not allow the same candle that creates
                # liquidity to immediately sweep itself.
                continue

            # -------------------------------------------------
            # Test for sweep
            # -------------------------------------------------

            if (
                last_liquidity_high
                is not None
                and
                np.isfinite(highs[i])
                and
                np.isfinite(closes[i])
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

                    last_liquidity_high = None

        df["buy_side_sweep"] = (
            sweeps
        )

        return df

    # =========================================================
    # SELL-SIDE LIQUIDITY SWEEP
    # =========================================================
    #
    # Sell-side liquidity sits below lows.
    #
    # A bullish sell-side sweep occurs when:
    #
    # 1. Price trades BELOW the liquidity level.
    # 2. The candle CLOSES BACK ABOVE the level.
    # =========================================================

    def detect_sell_side_sweeps(
        self,
        df
    ):

        df = df.copy()

        lows = pd.to_numeric(
            df["low"],
            errors="coerce"
        ).to_numpy(dtype=float)

        closes = pd.to_numeric(
            df["close"],
            errors="coerce"
        ).to_numpy(dtype=float)

        equal_lows = (
            df["equal_low"]
            .to_numpy(dtype=bool)
        )

        sweeps = np.zeros(
            len(df),
            dtype=bool
        )

        last_liquidity_low = None

        for i in range(
            len(df)
        ):

            # -------------------------------------------------
            # Register new liquidity
            # -------------------------------------------------

            if equal_lows[i]:

                if np.isfinite(
                    lows[i]
                ):

                    last_liquidity_low = (
                        lows[i]
                    )

                # Do not allow the same candle to sweep itself.
                continue

            # -------------------------------------------------
            # Test for sweep
            # -------------------------------------------------

            if (
                last_liquidity_low
                is not None
                and
                np.isfinite(lows[i])
                and
                np.isfinite(closes[i])
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

                    last_liquidity_low = None

        df["sell_side_sweep"] = (
            sweeps
        )

        return df

    # =========================================================
    # COMPLETE LIQUIDITY ANALYSIS
    # =========================================================

    def analyze(self, df):

        df = df.copy()

        required_columns = [
            "high",
            "low",
            "close"
        ]

        missing = [
            column
            for column in required_columns
            if column not in df.columns
        ]

        if missing:

            raise ValueError(
                "Missing required liquidity "
                "columns: "
                +
                ", ".join(missing)
            )

        df = self.add_columns(
            df
        )

        df = self.find_equal_highs(
            df
        )

        df = self.find_equal_lows(
            df
        )

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
