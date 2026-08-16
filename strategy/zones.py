import pandas as pd


class ZoneAnalyzer:

    def __init__(self, fvg_min_size=0.0):

        self.fvg_min_size = fvg_min_size

    # =========================================================
    # PREPARE COLUMNS
    # =========================================================

    def add_columns(self, df):

        df = df.copy()

        columns = [

            "support",
            "resistance",

            "demand",
            "supply",

            "bullish_order_block",
            "bearish_order_block",

            "bullish_fvg",
            "bearish_fvg",

            "displacement"

        ]

        for column in columns:

            if column not in df.columns:

                df[column] = False

        return df

    # =========================================================
    # SUPPORT AND RESISTANCE
    # =========================================================

    def detect_support_resistance(self, df):

        df = df.copy()

        for i in range(1, len(df) - 1):

            current_low = df.iloc[i]["low"]
            previous_low = df.iloc[i - 1]["low"]
            next_low = df.iloc[i + 1]["low"]

            current_high = df.iloc[i]["high"]
            previous_high = df.iloc[i - 1]["high"]
            next_high = df.iloc[i + 1]["high"]

            # -------------------------------------------------
            # SUPPORT
            # -------------------------------------------------

            if (
                current_low < previous_low
                and
                current_low < next_low
            ):

                df.loc[
                    df.index[i],
                    "support"
                ] = True

            # -------------------------------------------------
            # RESISTANCE
            # -------------------------------------------------

            if (
                current_high > previous_high
                and
                current_high > next_high
            ):

                df.loc[
                    df.index[i],
                    "resistance"
                ] = True

        return df

    # =========================================================
    # SUPPLY AND DEMAND
    # =========================================================

    def detect_supply_demand(self, df):

        df = df.copy()

        for i in range(1, len(df)):

            previous = df.iloc[i - 1]
            current = df.iloc[i]

            previous_bearish = (
                previous["close"]
                <
                previous["open"]
            )

            previous_bullish = (
                previous["close"]
                >
                previous["open"]
            )

            current_bullish = (
                current["close"]
                >
                current["open"]
            )

            current_bearish = (
                current["close"]
                <
                current["open"]
            )

            # -------------------------------------------------
            # DEMAND
            # -------------------------------------------------
            #
            # Bearish candle followed by bullish movement.
            # This is a basic candidate definition.
            #
            # Later we will require displacement and
            # structural confirmation.
            # -------------------------------------------------

            if (
                previous_bearish
                and
                current_bullish
            ):

                df.loc[
                    df.index[i - 1],
                    "demand"
                ] = True

            # -------------------------------------------------
            # SUPPLY
            # -------------------------------------------------

            if (
                previous_bullish
                and
                current_bearish
            ):

                df.loc[
                    df.index[i - 1],
                    "supply"
                ] = True

        return df

    # =========================================================
    # ORDER BLOCKS
    # =========================================================

    def detect_order_blocks(self, df):

        df = df.copy()

        for i in range(1, len(df)):

            previous = df.iloc[i - 1]
            current = df.iloc[i]

            previous_bearish = (
                previous["close"]
                <
                previous["open"]
            )

            previous_bullish = (
                previous["close"]
                >
                previous["open"]
            )

            # -------------------------------------------------
            # BULLISH ORDER BLOCK
            # -------------------------------------------------
            #
            # Last bearish candle before bullish displacement
            # through the previous high.
            # -------------------------------------------------

            bullish_displacement = (
                current["close"]
                >
                previous["high"]
            )

            if (
                previous_bearish
                and
                bullish_displacement
            ):

                df.loc[
                    df.index[i - 1],
                    "bullish_order_block"
                ] = True

            # -------------------------------------------------
            # BEARISH ORDER BLOCK
            # -------------------------------------------------

            bearish_displacement = (
                current["close"]
                <
                previous["low"]
            )

            if (
                previous_bullish
                and
                bearish_displacement
            ):

                df.loc[
                    df.index[i - 1],
                    "bearish_order_block"
                ] = True

        return df

    # =========================================================
    # FAIR VALUE GAPS
    # =========================================================

    def detect_fvg(self, df):

        df = df.copy()

        for i in range(2, len(df)):

            first = df.iloc[i - 2]
            middle = df.iloc[i - 1]
            third = df.iloc[i]

            # -------------------------------------------------
            # BULLISH FVG
            # -------------------------------------------------
            #
            # Third candle low remains above first candle high.
            #
            #       First       Third
            #         │           │
            #       High         Low
            #          \         /
            #           \  GAP  /
            #
            # -------------------------------------------------

            bullish_gap = (
                third["low"]
                >
                first["high"]
            )

            if bullish_gap:

                gap_size = (
                    third["low"]
                    -
                    first["high"]
                )

                if gap_size >= self.fvg_min_size:

                    df.loc[
                        df.index[i],
                        "bullish_fvg"
                    ] = True

            # -------------------------------------------------
            # BEARISH FVG
            # -------------------------------------------------

            bearish_gap = (
                third["high"]
                <
                first["low"]
            )

            if bearish_gap:

                gap_size = (
                    first["low"]
                    -
                    third["high"]
                )

                if gap_size >= self.fvg_min_size:

                    df.loc[
                        df.index[i],
                        "bearish_fvg"
                    ] = True

        return df

    # =========================================================
    # DISPLACEMENT
    # =========================================================

    def detect_displacement(self, df):

        df = df.copy()

        for i in range(1, len(df)):

            current = df.iloc[i]
            previous = df.iloc[i - 1]

            current_range = (
                current["high"]
                -
                current["low"]
            )

            previous_range = (
                previous["high"]
                -
                previous["low"]
            )

            if previous_range <= 0:

                continue

            # -------------------------------------------------
            # Basic displacement definition:
            #
            # Current candle range >= 1.5 × previous range
            #
            # This will later be improved using ATR and
            # directional body size.
            # -------------------------------------------------

            if (
                current_range
                >=
                previous_range * 1.5
            ):

                df.loc[
                    df.index[i],
                    "displacement"
                ] = True

        return df

    # =========================================================
    # COMPLETE ZONE ANALYSIS
    # =========================================================

    def analyze(self, df):

        df = self.add_columns(df)

        df = self.detect_support_resistance(df)

        df = self.detect_supply_demand(df)

        df = self.detect_order_blocks(df)

        df = self.detect_fvg(df)

        df = self.detect_displacement(df)

        return df
