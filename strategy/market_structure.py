import pandas as pd


class MarketStructure:

    def __init__(self, swing_length=3):

        self.swing_length = swing_length


    def detect_swings(self, df):

        df = df.copy()

        df["swing_high"] = False
        df["swing_low"] = False

        n = self.swing_length

        for i in range(n, len(df) - n):

            current_high = df.iloc[i]["high"]
            current_low = df.iloc[i]["low"]

            left_highs = df.iloc[i-n:i]["high"]
            right_highs = df.iloc[i+1:i+n+1]["high"]

            left_lows = df.iloc[i-n:i]["low"]
            right_lows = df.iloc[i+1:i+n+1]["low"]

            # Swing High
            if (
                current_high > left_highs.max()
                and
                current_high > right_highs.max()
            ):

                df.iloc[
                    i,
                    df.columns.get_loc("swing_high")
                ] = True


            # Swing Low
            if (
                current_low < left_lows.min()
                and
                current_low < right_lows.min()
            ):

                df.iloc[
                    i,
                    df.columns.get_loc("swing_low")
                ] = True

        return df


    def classify_structure(self, df):

        df = df.copy()

        df["structure"] = None

        previous_high = None
        previous_low = None

        for i in range(len(df)):

            row = df.iloc[i]

            # -------------------------
            # SWING HIGH
            # -------------------------

            if row["swing_high"]:

                current_high = row["high"]

                if previous_high is not None:

                    if current_high > previous_high:

                        df.iloc[
                            i,
                            df.columns.get_loc("structure")
                        ] = "HH"

                    elif current_high < previous_high:

                        df.iloc[
                            i,
                            df.columns.get_loc("structure")
                        ] = "LH"

                previous_high = current_high


            # -------------------------
            # SWING LOW
            # -------------------------

            if row["swing_low"]:

                current_low = row["low"]

                if previous_low is not None:

                    if current_low > previous_low:

                        df.iloc[
                            i,
                            df.columns.get_loc("structure")
                        ] = "HL"

                    elif current_low < previous_low:

                        df.iloc[
                            i,
                            df.columns.get_loc("structure")
                        ] = "LL"

                previous_low = current_low

        return df


    def determine_bias(self, df):

        highs = df[
            df["structure"].isin(["HH", "LH"])
        ]

        lows = df[
            df["structure"].isin(["HL", "LL"])
        ]

        if len(highs) == 0 or len(lows) == 0:

            return "neutral"


        recent_high = highs.iloc[-1]["structure"]
        recent_low = lows.iloc[-1]["structure"]


        if (
            recent_high == "HH"
            and
            recent_low == "HL"
        ):

            return "bullish"


        if (
            recent_high == "LH"
            and
            recent_low == "LL"
        ):

            return "bearish"


        return "neutral"


    def analyze(self, df):

        df = self.detect_swings(df)

        df = self.classify_structure(df)

        bias = self.determine_bias(df)

        return df, bias
