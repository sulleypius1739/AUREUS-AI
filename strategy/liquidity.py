import pandas as pd


class LiquidityAnalyzer:

    def __init__(self, tolerance=0.001):

        # Percentage tolerance used when determining
        # whether two highs/lows are approximately equal.
        self.tolerance = tolerance


    # =========================================================
    # EQUAL HIGHS
    # =========================================================

    def find_equal_highs(self, df):

        df = df.copy()

        df["equal_high"] = False

        swing_highs = df[
            df["swing_high"] == True
        ]

        indices = swing_highs.index.tolist()

        for i in range(len(indices)):

            for j in range(i + 1, len(indices)):

                idx1 = indices[i]
                idx2 = indices[j]

                high1 = df.loc[idx1, "high"]
                high2 = df.loc[idx2, "high"]

                difference = abs(high1 - high2)

                average = (high1 + high2) / 2

                if average == 0:
                    continue

                percentage_difference = (
                    difference / average
                )

                if percentage_difference <= self.tolerance:

                    df.loc[idx1, "equal_high"] = True
                    df.loc[idx2, "equal_high"] = True

        return df


    # =========================================================
    # EQUAL LOWS
    # =========================================================

    def find_equal_lows(self, df):

        df = df.copy()

        df["equal_low"] = False

        swing_lows = df[
            df["swing_low"] == True
        ]

        indices = swing_lows.index.tolist()

        for i in range(len(indices)):

            for j in range(i + 1, len(indices)):

                idx1 = indices[i]
                idx2 = indices[j]

                low1 = df.loc[idx1, "low"]
                low2 = df.loc[idx2, "low"]

                difference = abs(low1 - low2)

                average = (low1 + low2) / 2

                if average == 0:
                    continue

                percentage_difference = (
                    difference / average
                )

                if percentage_difference <= self.tolerance:

                    df.loc[idx1, "equal_low"] = True
                    df.loc[idx2, "equal_low"] = True

        return df


    # =========================================================
    # PREVIOUS SWING LEVELS
    # =========================================================

    def identify_liquidity_levels(self, df):

        df = df.copy()

        df["buy_side_liquidity"] = False
        df["sell_side_liquidity"] = False

        # Buy-side liquidity normally sits above highs.
        df.loc[
            df["swing_high"] == True,
            "buy_side_liquidity"
        ] = True

        # Sell-side liquidity normally sits below lows.
        df.loc[
            df["swing_low"] == True,
            "sell_side_liquidity"
        ] = True

        # Equal highs strengthen the potential
        # buy-side liquidity pool.
        df.loc[
            df["equal_high"] == True,
            "buy_side_liquidity"
        ] = True

        # Equal lows strengthen the potential
        # sell-side liquidity pool.
        df.loc[
            df["equal_low"] == True,
            "sell_side_liquidity"
        ] = True

        return df


    # =========================================================
    # LIQUIDITY SWEEPS
    # =========================================================

    def detect_sweeps(self, df):

        df = df.copy()

        df["buy_side_sweep"] = False
        df["sell_side_sweep"] = False

        last_swing_high = None
        last_swing_low = None

        for i in range(len(df)):

            row = df.iloc[i]

            current_high = row["high"]
            current_low = row["low"]
            current_close = row["close"]


            # -------------------------------------------------
            # UPDATE MOST RECENT SWING HIGH
            # -------------------------------------------------

            if row["swing_high"]:

                last_swing_high = current_high


            # -------------------------------------------------
            # UPDATE MOST RECENT SWING LOW
            # -------------------------------------------------

            if row["swing_low"]:

                last_swing_low = current_low


            # -------------------------------------------------
            # BUY-SIDE LIQUIDITY SWEEP
            # -------------------------------------------------
            #
            # Price trades above a previous swing high
            # but closes back below it.
            #
            # This is a basic objective definition of
            # a potential buy-side liquidity sweep.
            # -------------------------------------------------

            if last_swing_high is not None:

                if (
                    current_high > last_swing_high
                    and
                    current_close < last_swing_high
                ):

                    df.iloc[
                        i,
                        df.columns.get_loc(
                            "buy_side_sweep"
                        )
                    ] = True


            # -------------------------------------------------
            # SELL-SIDE LIQUIDITY SWEEP
            # -------------------------------------------------
            #
            # Price trades below a previous swing low
            # but closes back above it.
            # -------------------------------------------------

            if last_swing_low is not None:

                if (
                    current_low < last_swing_low
                    and
                    current_close > last_swing_low
                ):

                    df.iloc[
                        i,
                        df.columns.get_loc(
                            "sell_side_sweep"
                        )
                    ] = True

        return df


    # =========================================================
    # COMPLETE ANALYSIS
    # =========================================================

    def analyze(self, df):

        df = self.find_equal_highs(df)

        df = self.find_equal_lows(df)

        df = self.identify_liquidity_levels(df)

        df = self.detect_sweeps(df)

        return df
