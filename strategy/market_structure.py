import pandas as pd


class MarketStructure:

    def __init__(self, swing_length=3):
        self.swing_length = swing_length

    # =========================================================
    # DETECT SWING HIGHS AND SWING LOWS
    # =========================================================

    def detect_swings(self, df):

        df = df.copy()

        # Create columns
        df["swing_high"] = False
        df["swing_low"] = False

        n = self.swing_length

        # We need candles on both sides of the current candle
        for i in range(n, len(df) - n):

            current_high = df.iloc[i]["high"]
            current_low = df.iloc[i]["low"]

            left_highs = df.iloc[i-n:i]["high"]
            right_highs = df.iloc[i+1:i+n+1]["high"]

            left_lows = df.iloc[i-n:i]["low"]
            right_lows = df.iloc[i+1:i+n+1]["low"]

            # -------------------------------------------------
            # SWING HIGH
            # -------------------------------------------------
            #
            # Current high must be greater than every high
            # in the selected candles to the left and right.
            # -------------------------------------------------

            if (
                current_high > left_highs.max()
                and
                current_high > right_highs.max()
            ):

                df.loc[
                    df.index[i],
                    "swing_high"
                ] = True

            # -------------------------------------------------
            # SWING LOW
            # -------------------------------------------------
            #
            # Current low must be lower than every low
            # in the selected candles to the left and right.
            # -------------------------------------------------

            if (
                current_low < left_lows.min()
                and
                current_low < right_lows.min()
            ):

                df.loc[
                    df.index[i],
                    "swing_low"
                ] = True

        return df

    # =========================================================
    # CLASSIFY MARKET STRUCTURE
    # =========================================================

    def classify_structure(self, df):

        df = df.copy()

        df["structure"] = None

        previous_high = None
        previous_low = None

        # -----------------------------------------------------
        # PROCESS EACH CANDLE
        # -----------------------------------------------------

        for i in range(len(df)):

            row = df.iloc[i]

            # =================================================
            # SWING HIGH
            # =================================================

            if row["swing_high"]:

                current_high = row["high"]

                # We can only classify the high if we have
                # another previous swing high to compare it to.

                if previous_high is not None:

                    if current_high > previous_high:

                        df.loc[
                            df.index[i],
                            "structure"
                        ] = "HH"

                    elif current_high < previous_high:

                        df.loc[
                            df.index[i],
                            "structure"
                        ] = "LH"

                previous_high = current_high

            # =================================================
            # SWING LOW
            # =================================================

            if row["swing_low"]:

                current_low = row["low"]

                # Compare current swing low with previous
                # swing low.

                if previous_low is not None:

                    if current_low > previous_low:

                        df.loc[
                            df.index[i],
                            "structure"
                        ] = "HL"

                    elif current_low < previous_low:

                        df.loc[
                            df.index[i],
                            "structure"
                        ] = "LL"

                previous_low = current_low

        return df

    # =========================================================
    # DETERMINE MARKET BIAS
    # =========================================================

    def determine_bias(self, df):

        # Get classified swing highs
        highs = df[
            df["structure"].isin(
                ["HH", "LH"]
            )
        ]

        # Get classified swing lows
        lows = df[
            df["structure"].isin(
                ["HL", "LL"]
            )
        ]

        # Not enough information
        if (
            len(highs) == 0
            or
            len(lows) == 0
        ):

            return "neutral"

        # Most recent classified high
        recent_high = highs.iloc[-1]["structure"]

        # Most recent classified low
        recent_low = lows.iloc[-1]["structure"]

        # -----------------------------------------------------
        # BULLISH STRUCTURE
        # -----------------------------------------------------
        #
        # Higher High + Higher Low
        #
        # HH
        # HL
        #
        # -----------------------------------------------------

        if (
            recent_high == "HH"
            and
            recent_low == "HL"
        ):

            return "bullish"

        # -----------------------------------------------------
        # BEARISH STRUCTURE
        # -----------------------------------------------------
        #
        # Lower High + Lower Low
        #
        # LH
        # LL
        #
        # -----------------------------------------------------

        if (
            recent_high == "LH"
            and
            recent_low == "LL"
        ):

            return "bearish"

        # -----------------------------------------------------
        # MIXED STRUCTURE
        # -----------------------------------------------------

        return "neutral"

    # =========================================================
    # COMPLETE MARKET STRUCTURE ANALYSIS
    # =========================================================

    def analyze(self, df):

        # Step 1:
        # Find objective swing highs and lows.

        df = self.detect_swings(df)

        # Step 2:
        # Classify swings as:
        #
        # HH = Higher High
        # HL = Higher Low
        # LH = Lower High
        # LL = Lower Low

        df = self.classify_structure(df)

        # Step 3:
        # Determine overall structural bias.

        bias = self.determine_bias(df)

        return df, bias
