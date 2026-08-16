import pandas as pd
import numpy as np


class MarketStructure:

    def __init__(self, swing_length=3):

        if swing_length < 1:
            raise ValueError(
                "swing_length must be >= 1"
            )

        self.swing_length = int(
            swing_length
        )

    # =========================================================
    # DETECT SWINGS
    # =========================================================

    def detect_swings(self, df):

        df = df.copy()

        n = self.swing_length
        length = len(df)

        highs = df["high"].to_numpy(
            dtype=float
        )

        lows = df["low"].to_numpy(
            dtype=float
        )

        # -----------------------------------------------------
        # Swing information
        # -----------------------------------------------------

        swing_high = np.zeros(
            length,
            dtype=bool
        )

        swing_low = np.zeros(
            length,
            dtype=bool
        )

        # -----------------------------------------------------
        # Confirmation information
        #
        # These are the columns that downstream strategy
        # logic should use.
        # -----------------------------------------------------

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

        # =====================================================
        # FIND SWINGS
        # =====================================================

        for i in range(
            n,
            length - n
        ):

            # -------------------------------------------------
            # HIGH
            # -------------------------------------------------

            current_high = highs[i]

            left_highs = highs[
                i - n:i
            ]

            right_highs = highs[
                i + 1:i + n + 1
            ]

            if (
                current_high > left_highs.max()
                and
                current_high > right_highs.max()
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
            # LOW
            # -------------------------------------------------

            current_low = lows[i]

            left_lows = lows[
                i - n:i
            ]

            right_lows = lows[
                i + 1:i + n + 1
            ]

            if (
                current_low < left_lows.min()
                and
                current_low < right_lows.min()
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

        # =====================================================
        # SAVE RESULTS
        # =====================================================

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

        confirmed_highs = (
            df[
                "swing_high_confirmed"
            ].to_numpy(
                dtype=bool
            )
        )

        confirmed_lows = (
            df[
                "swing_low_confirmed"
            ].to_numpy(
                dtype=bool
            )
        )

        high_prices = (
            df[
                "swing_high_price"
            ].to_numpy(
                dtype=float
            )
        )

        low_prices = (
            df[
                "swing_low_price"
            ].to_numpy(
                dtype=float
            )
        )

        previous_swing_high = None
        previous_swing_low = None

        # =====================================================
        # WALK FORWARD
        # =====================================================

        for i in range(length):

            # -------------------------------------------------
            # CONFIRMED HIGH
            # -------------------------------------------------

            if confirmed_highs[i]:

                current_high = high_prices[i]

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

                previous_swing_high = (
                    current_high
                )

            # -------------------------------------------------
            # CONFIRMED LOW
            # -------------------------------------------------

            if confirmed_lows[i]:

                current_low = low_prices[i]

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

                previous_swing_low = (
                    current_low
                )

        df["structure"] = structure

        return df

    # =========================================================
    # DETERMINE FINAL STRUCTURAL BIAS
    # =========================================================

    def determine_bias(self, df):

        structure = (
            df["structure"]
            .dropna()
            .to_numpy(
                dtype=object
            )
        )

        if len(structure) < 2:
            return "neutral"

        latest_high_structure = None
        latest_low_structure = None

        # -----------------------------------------------------
        # Search backwards for the latest confirmed high
        # and latest confirmed low structure.
        # -----------------------------------------------------

        for value in reversed(structure):

            if (
                latest_high_structure
                is None
                and
                value in ["HH", "LH"]
            ):

                latest_high_structure = value

            if (
                latest_low_structure
                is None
                and
                value in ["HL", "LL"]
            ):

                latest_low_structure = value

            if (
                latest_high_structure
                is not None
                and
                latest_low_structure
                is not None
            ):

                break

        # -----------------------------------------------------
        # BULLISH
        # -----------------------------------------------------

        if (
            latest_high_structure == "HH"
            and
            latest_low_structure == "HL"
        ):

            return "bullish"

        # -----------------------------------------------------
        # BEARISH
        # -----------------------------------------------------

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

        # -----------------------------------------------------
        # Validate columns
        # -----------------------------------------------------

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

        # -----------------------------------------------------
        # Detect swings
        # -----------------------------------------------------

        df = self.detect_swings(df)

        # -----------------------------------------------------
        # Classify structure
        # -----------------------------------------------------

        df = self.classify_structure(df)

        # -----------------------------------------------------
        # Determine final bias
        # -----------------------------------------------------

        bias = self.determine_bias(df)

        return df, bias
