import pandas as pd
import numpy as np


class MarketStructure:

    def __init__(self, swing_length=3):
        if swing_length < 1:
            raise ValueError("swing_length must be >= 1")

        self.swing_length = int(swing_length)

    # =========================================================
    # DETECT SWING HIGHS / LOWS
    # =========================================================

    def detect_swings(self, df):

        df = df.copy()

        n = self.swing_length
        length = len(df)

        highs = pd.to_numeric(
            df["high"],
            errors="coerce"
        ).to_numpy(dtype=float)

        lows = pd.to_numeric(
            df["low"],
            errors="coerce"
        ).to_numpy(dtype=float)

        swing_high = np.zeros(
            length,
            dtype=bool
        )

        swing_low = np.zeros(
            length,
            dtype=bool
        )

        swing_high_confirmed = np.zeros(
            length,
            dtype=bool
        )

        swing_low_confirmed = np.zeros(
            length,
            dtype=bool
        )

        swing_high_price = np.full(
            length,
            np.nan
        )

        swing_low_price = np.full(
            length,
            np.nan
        )

        # -----------------------------------------------------
        # A swing at candle i is only known at i + n.
        #
        # Example with swing_length = 3:
        #
        # actual swing:       candle 100
        # confirmation:       candle 103
        #
        # Therefore all trading logic must use the confirmed
        # columns, NOT swing_high/swing_low at the anchor.
        # -----------------------------------------------------

        for i in range(
            n,
            length - n
        ):

            current_high = highs[i]

            left_highs = highs[
                i - n:i
            ]

            right_highs = highs[
                i + 1:i + n + 1
            ]

            # -------------------------------------------------
            # SWING HIGH
            # -------------------------------------------------

            if (
                np.isfinite(current_high)
                and
                len(left_highs) == n
                and
                len(right_highs) == n
                and
                current_high > np.max(left_highs)
                and
                current_high > np.max(right_highs)
            ):

                swing_high[i] = True

                confirmation_index = i + n

                if confirmation_index < length:

                    swing_high_confirmed[
                        confirmation_index
                    ] = True

                    swing_high_price[
                        confirmation_index
                    ] = current_high

            # -------------------------------------------------
            # SWING LOW
            # -------------------------------------------------

            current_low = lows[i]

            left_lows = lows[
                i - n:i
            ]

            right_lows = lows[
                i + 1:i + n + 1
            ]

            if (
                np.isfinite(current_low)
                and
                len(left_lows) == n
                and
                len(right_lows) == n
                and
                current_low < np.min(left_lows)
                and
                current_low < np.min(right_lows)
            ):

                swing_low[i] = True

                confirmation_index = i + n

                if confirmation_index < length:

                    swing_low_confirmed[
                        confirmation_index
                    ] = True

                    swing_low_price[
                        confirmation_index
                    ] = current_low

        df["swing_high"] = swing_high

        df["swing_low"] = swing_low

        df["swing_high_confirmed"] = (
            swing_high_confirmed
        )

        df["swing_low_confirmed"] = (
            swing_low_confirmed
        )

        df["swing_high_price"] = (
            swing_high_price
        )

        df["swing_low_price"] = (
            swing_low_price
        )

        return df

    # =========================================================
    # CLASSIFY STRUCTURE
    # =========================================================

    def classify_structure(self, df):

        df = df.copy()

        length = len(df)

        structure = np.full(
            length,
            None,
            dtype=object
        )

        swing_high_confirmed = (
            df[
                "swing_high_confirmed"
            ]
            .to_numpy(dtype=bool)
        )

        swing_low_confirmed = (
            df[
                "swing_low_confirmed"
            ]
            .to_numpy(dtype=bool)
        )

        swing_high_price = (
            df[
                "swing_high_price"
            ]
            .to_numpy(dtype=float)
        )

        swing_low_price = (
            df[
                "swing_low_price"
            ]
            .to_numpy(dtype=float)
        )

        previous_swing_high = None

        previous_swing_low = None

        # -----------------------------------------------------
        # Walk forward only.
        #
        # This prevents future-confirmed information from
        # appearing before it was actually available.
        # -----------------------------------------------------

        for i in range(length):

            # =================================================
            # HIGH STRUCTURE
            # =================================================

            if swing_high_confirmed[i]:

                current_high = (
                    swing_high_price[i]
                )

                if (
                    previous_swing_high
                    is not None
                    and
                    np.isfinite(current_high)
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

                if np.isfinite(current_high):

                    previous_swing_high = (
                        current_high
                    )

            # =================================================
            # LOW STRUCTURE
            # =================================================

            if swing_low_confirmed[i]:

                current_low = (
                    swing_low_price[i]
                )

                if (
                    previous_swing_low
                    is not None
                    and
                    np.isfinite(current_low)
                ):

                    if (
                        current_low
                        >
                        previous_swing_low
                    ):

                        # If nothing has already been written
                        # to this candle, store HL.
                        #
                        # If a high structure event happened
                        # on the same candle, preserve the first
                        # event rather than overwriting it.

                        if structure[i] is None:
                            structure[i] = "HL"

                    elif (
                        current_low
                        <
                        previous_swing_low
                    ):

                        if structure[i] is None:
                            structure[i] = "LL"

                if np.isfinite(current_low):

                    previous_swing_low = (
                        current_low
                    )

        df["structure"] = structure

        return df

    # =========================================================
    # ROLLING BIAS
    # =========================================================
    #
    # IMPORTANT:
    #
    # This bias is calculated progressively through the data.
    # It does NOT look at the final structure and apply that
    # answer backwards to earlier candles.
    #
    # At candle i, only structure confirmed at or before i
    # can influence the bias.
    # =========================================================

    def determine_bias(self, df):

        length = len(df)

        biases = np.full(
            length,
            "neutral",
            dtype=object
        )

        structure = (
            df["structure"]
            .to_numpy(dtype=object)
        )

        latest_high_structure = None

        latest_low_structure = None

        for i in range(length):

            value = structure[i]

            if value in (
                "HH",
                "LH"
            ):

                latest_high_structure = value

            elif value in (
                "HL",
                "LL"
            ):

                latest_low_structure = value

            if (
                latest_high_structure == "HH"
                and
                latest_low_structure == "HL"
            ):

                biases[i] = "bullish"

            elif (
                latest_high_structure == "LH"
                and
                latest_low_structure == "LL"
            ):

                biases[i] = "bearish"

            else:

                biases[i] = "neutral"

        return biases

    # =========================================================
    # COMPLETE ANALYSIS
    # =========================================================

    def analyze(self, df):

        df = df.copy()

        required_columns = [
            "high",
            "low"
        ]

        missing = [
            column
            for column in required_columns
            if column not in df.columns
        ]

        if missing:

            raise ValueError(
                "Missing required market structure "
                "columns: "
                +
                ", ".join(missing)
            )

        df = self.detect_swings(df)

        df = self.classify_structure(df)

        biases = self.determine_bias(df)

        df["structure_bias"] = biases

        current_bias = (
            biases[-1]
            if length_safe(df) > 0
            else "neutral"
        )

        return df, current_bias


def length_safe(df):

    return len(df)
