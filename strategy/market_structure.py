import pandas as pd
import numpy as np


class MarketStructure:

    def __init__(self, swing_length=3):

        self.swing_length = swing_length

    # =========================================================
    # DETECT SWING HIGHS / LOWS
    # =========================================================

    def detect_swings(self, df):

        df = df.copy()

        n = self.swing_length

        highs = df["high"].to_numpy()
        lows = df["low"].to_numpy()

        swing_high = np.zeros(
            len(df),
            dtype=bool
        )

        swing_low = np.zeros(
            len(df),
            dtype=bool
        )

        # -----------------------------------------------------
        # A swing high must be higher than the n candles
        # before and after it.
        # -----------------------------------------------------

        for i in range(n, len(df) - n):

            current_high = highs[i]

            left_high = highs[
                i - n:i
            ]

            right_high = highs[
                i + 1:i + n + 1
            ]

            if (
                current_high > left_high.max()
                and
                current_high > right_high.max()
            ):

                swing_high[i] = True

            # -------------------------------------------------
            # Swing low
            # -------------------------------------------------

            current_low = lows[i]

            left_low = lows[
                i - n:i
            ]

            right_low = lows[
                i + 1:i + n + 1
            ]

            if (
                current_low < left_low.min()
                and
                current_low < right_low.min()
            ):

                swing_low[i] = True

        df["swing_high"] = swing_high

        df["swing_low"] = swing_low

        return df

    # =========================================================
    # CLASSIFY SWING STRUCTURE
    # =========================================================

    def classify_structure(self, df):

        df = df.copy()

        structure = np.full(
            len(df),
            None,
            dtype=object
        )

        highs = df["high"].to_numpy()

        lows = df["low"].to_numpy()

        swing_highs = df[
            "swing_high"
        ].to_numpy()

        swing_lows = df[
            "swing_low"
        ].to_numpy()

        previous_swing_high = None

        previous_swing_low = None

        # -----------------------------------------------------
        # We iterate over numpy arrays rather than doing
        # df.iloc[i] on every candle.
        # This is dramatically faster.
        # -----------------------------------------------------

        for i in range(len(df)):

            # ================================================
            # SWING HIGH
            # ================================================

            if swing_highs[i]:

                current_high = highs[i]

                if (
                    previous_swing_high
                    is not None
                ):

                    if (
                        current_high
                        >
                        previous_swing_high
                    ):

                        structure[i] = "HH"

                    elif (
                        current_high
                        <
                        previous_swing_high
                    ):

                        structure[i] = "LH"

                previous_swing_high = current_high

            # ================================================
            # SWING LOW
            # ================================================

            if swing_lows[i]:

                current_low = lows[i]

                if (
                    previous_swing_low
                    is not None
                ):

                    if (
                        current_low
                        >
                        previous_swing_low
                    ):

                        structure[i] = "HL"

                    elif (
                        current_low
                        <
                        previous_swing_low
                    ):

                        structure[i] = "LL"

                previous_swing_low = current_low

        df["structure"] = structure

        return df

    # =========================================================
    # DETERMINE BIAS
    # =========================================================

    def determine_bias(self, df):

        structure = df[
            "structure"
        ].dropna()

        if len(structure) < 2:

            return "neutral"

        # -----------------------------------------------------
        # Find the most recent classified high
        # -----------------------------------------------------

        recent_high = None

        recent_low = None

        for value in reversed(
            structure.to_numpy()
        ):

            if (
                recent_high is None
                and
                value in ["HH", "LH"]
            ):

                recent_high = value

            if (
                recent_low is None
                and
                value in ["HL", "LL"]
            ):

                recent_low = value

            if (
                recent_high is not None
                and
                recent_low is not None
            ):

                break

        # -----------------------------------------------------
        # Bullish
        # -----------------------------------------------------

        if (
            recent_high == "HH"
            and
            recent_low == "HL"
        ):

            return "bullish"

        # -----------------------------------------------------
        # Bearish
        # -----------------------------------------------------

        if (
            recent_high == "LH"
            and
            recent_low == "LL"
        ):

            return "bearish"

        return "neutral"

    # =========================================================
    # COMPLETE ANALYSIS
    # =========================================================

    def analyze(self, df):

        df = self.detect_swings(df)

        df = self.classify_structure(df)

        bias = self.determine_bias(df)

        return df, bias
