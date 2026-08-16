import numpy as np
import pandas as pd


class MarketStructure:
    """
    AUREUS Market Structure Analyzer

    Detects confirmed swing highs/lows and classifies them as:

        HH = Higher High
        HL = Higher Low
        LH = Lower High
        LL = Lower Low

    IMPORTANT:

    A swing is only known after `swing_length` candles have
    closed after the candidate swing.

    Example with swing_length = 3:

        candidate swing = candle 100
        confirmation    = candle 103

    The strategy is therefore only allowed to use that swing
    from candle 103 onward.
    """

    def __init__(self, swing_length=3):

        if swing_length < 1:
            raise ValueError(
                "swing_length must be >= 1"
            )

        self.swing_length = int(swing_length)

    # =========================================================
    # DETECT SWINGS
    # =========================================================

    def detect_swings(self, df):

        df = df.copy()

        n = self.swing_length
        length = len(df)

        highs = df["high"].to_numpy(dtype=float)
        lows = df["low"].to_numpy(dtype=float)

        candidate_swing_high = np.zeros(
            length,
            dtype=bool
        )

        candidate_swing_low = np.zeros(
            length,
            dtype=bool
        )

        confirmed_swing_high = np.zeros(
            length,
            dtype=bool
        )

        confirmed_swing_low = np.zeros(
            length,
            dtype=bool
        )

        # Store the actual price of the confirmed swing.
        confirmed_high_price = np.full(
            length,
            np.nan
        )

        confirmed_low_price = np.full(
            length,
            np.nan
        )

        # Store the original candle index where the swing
        # actually occurred.
        confirmed_high_index = np.full(
            length,
            np.nan
        )

        confirmed_low_index = np.full(
            length,
            np.nan
        )

        # =====================================================
        # FIND CANDIDATE SWINGS
        # =====================================================

        for i in range(
            n,
            length - n
        ):

            current_high = highs[i]
            current_low = lows[i]

            left_high = highs[
                i - n:i
            ]

            right_high = highs[
                i + 1:i + n + 1
            ]

            left_low = lows[
                i - n:i
            ]

            right_low = lows[
                i + 1:i + n + 1
            ]

            # -------------------------------------------------
            # SWING HIGH
            # -------------------------------------------------

            if (
                current_high > left_high.max()
                and
                current_high > right_high.max()
            ):

                candidate_swing_high[i] = True

            # -------------------------------------------------
            # SWING LOW
            # -------------------------------------------------

            if (
                current_low < left_low.min()
                and
                current_low < right_low.min()
            ):

                candidate_swing_low[i] = True

        # =====================================================
        # SHIFT SWINGS TO THEIR CONFIRMATION CANDLE
        # =====================================================

        for swing_index in range(length):

            confirmation_index = (
                swing_index + n
            )

            if confirmation_index >= length:
                continue

            # -------------------------------------------------
            # CONFIRMED HIGH
            # -------------------------------------------------

            if candidate_swing_high[swing_index]:

                confirmed_swing_high[
                    confirmation_index
                ] = True

                confirmed_high_price[
                    confirmation_index
                ] = highs[swing_index]

                confirmed_high_index[
                    confirmation_index
                ] = swing_index

            # -------------------------------------------------
            # CONFIRMED LOW
            # -------------------------------------------------

            if candidate_swing_low[swing_index]:

                confirmed_swing_low[
                    confirmation_index
                ] = True

                confirmed_low_price[
                    confirmation_index
                ] = lows[swing_index]

                confirmed_low_index[
                    confirmation_index
                ] = swing_index

        # -----------------------------------------------------
        # Store results
        # -----------------------------------------------------

        df["swing_high"] = candidate_swing_high
        df["swing_low"] = candidate_swing_low

        df["confirmed_swing_high"] = (
            confirmed_swing_high
        )

        df["confirmed_swing_low"] = (
            confirmed_swing_low
        )

        df["confirmed_high_price"] = (
            confirmed_high_price
        )

        df["confirmed_low_price"] = (
            confirmed_low_price
        )

        df["confirmed_high_index"] = (
            confirmed_high_index
        )

        df["confirmed_low_index"] = (
            confirmed_low_index
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

        highs = df["high"].to_numpy(dtype=float)
        lows = df["low"].to_numpy(dtype=float)

        confirmed_highs = (
            df["confirmed_swing_high"]
            .to_numpy(dtype=bool)
        )

        confirmed_lows = (
            df["confirmed_swing_low"]
            .to_numpy(dtype=bool)
        )

        confirmed_high_prices = (
            df["confirmed_high_price"]
            .to_numpy(dtype=float)
        )

        confirmed_low_prices = (
            df["confirmed_low_price"]
            .to_numpy(dtype=float)
        )

        previous_swing_high = None
        previous_swing_low = None

        # =====================================================
        # WALK FORWARD
        # =====================================================

        for i in range(length):

            high_structure = None
            low_structure = None

            # -------------------------------------------------
            # CONFIRMED HIGH
            # -------------------------------------------------

            if confirmed_highs[i]:

                current_high = (
                    confirmed_high_prices[i]
                )

                if previous_swing_high is not None:

                    if current_high > previous_swing_high:

                        high_structure = "HH"

                    elif current_high < previous_swing_high:

                        high_structure = "LH"

                previous_swing_high = current_high

            # -------------------------------------------------
            # CONFIRMED LOW
            # -------------------------------------------------

            if confirmed_lows[i]:

                current_low = (
                    confirmed_low_prices[i]
                )

                if previous_swing_low is not None:

                    if current_low > previous_swing_low:

                        low_structure = "HL"

                    elif current_low < previous_swing_low:

                        low_structure = "LL"

                previous_swing_low = current_low

            # -------------------------------------------------
            # Store structure
            #
            # Normally one classification occurs per candle.
            # If both occur, preserve both rather than silently
            # overwriting one.
            # -------------------------------------------------

            if (
                high_structure is not None
                and
                low_structure is not None
            ):

                structure[i] = (
                    high_structure
                    + "_"
                    + low_structure
                )

            elif high_structure is not None:

                structure[i] = high_structure

            elif low_structure is not None:

                structure[i] = low_structure

        df["structure"] = structure

        return df

    # =========================================================
    # DETERMINE ROLLING BIAS
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

        # =====================================================
        # WALK FORWARD
        # =====================================================

        for i in range(length):

            value = structure[i]

            if value is None:
                biases[i] = self._get_bias(
                    latest_high_structure,
                    latest_low_structure
                )
                continue

            # -------------------------------------------------
            # A candle can theoretically contain both.
            # -------------------------------------------------

            if "_" in str(value):

                parts = str(value).split("_")

                for part in parts:

                    if part in ["HH", "LH"]:
                        latest_high_structure = part

                    elif part in ["HL", "LL"]:
                        latest_low_structure = part

            else:

                if value in ["HH", "LH"]:

                    latest_high_structure = value

                elif value in ["HL", "LL"]:

                    latest_low_structure = value

            biases[i] = self._get_bias(
                latest_high_structure,
                latest_low_structure
            )

        return biases

    # =========================================================
    # BIAS HELPER
    # =========================================================

    @staticmethod
    def _get_bias(
        latest_high_structure,
        latest_low_structure
    ):

        if (
            latest_high_structure == "HH"
            and
            latest_low_structure == "HL"
        ):

            return "bullish"

        if (
            latest_high_structure == "LH"
            and
            latest_low_structure == "LL"
        ):

            return "bearish"

        return "neutral"

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
                + ", ".join(missing)
            )

        # -----------------------------------------------------
        # 1. Detect candidate and confirmed swings
        # -----------------------------------------------------

        df = self.detect_swings(df)

        # -----------------------------------------------------
        # 2. Classify only CONFIRMED swings
        # -----------------------------------------------------

        df = self.classify_structure(df)

        # -----------------------------------------------------
        # 3. Calculate rolling bias
        # -----------------------------------------------------

        biases = self.determine_bias(df)

        df["structure_bias"] = biases

        # -----------------------------------------------------
        # IMPORTANT:
        #
        # This is only the latest bias.
        #
        # The backtest should use df["structure_bias"].iloc[i]
        # for candle i, NOT this final value.
        # -----------------------------------------------------

        current_bias = (
            biases[-1]
            if len(biases) > 0
            else "neutral"
        )

        return df, current_bias
