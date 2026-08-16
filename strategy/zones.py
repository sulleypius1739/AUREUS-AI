import pandas as pd


class ZoneAnalyzer:

    def __init__(self, fvg_min_size=0.0):
        self.fvg_min_size = fvg_min_size

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
            df[column] = False

        return df

    def detect_support_resistance(self, df):

        df = df.copy()

        for i in range(1, len(df) - 1):

            if (
                df.iloc[i]["low"] < df.iloc[i-1]["low"]
                and
                df.iloc[i]["low"] < df.iloc[i+1]["low"]
            ):
                df.iloc[
                    i,
                    df.columns.get_loc("support")
                ] = True

            if (
                df.iloc[i]["high"] > df.iloc[i-1]["high"]
                and
                df.iloc[i]["high"] > df.iloc[i+1]["high"]
            ):
                df.iloc[
                    i,
                    df.columns.get_loc("resistance")
                ] = True

        return df

    def detect_supply_demand(self, df):

        df = df.copy()

        for i in range(1, len(df)):

            previous = df.iloc[i-1]
            current = df.iloc[i]

            previous_bearish = (
                previous["close"] < previous["open"]
            )

            previous_bullish = (
                previous["close"] > previous["open"]
            )

            current_bullish = (
                current["close"] > current["open"]
            )

            current_bearish = (
                current["close"] < current["open"]
            )

            if previous_bearish and current_bullish:

                df.iloc[
                    i-1,
                    df.columns.get_loc("demand")
                ] = True

            if previous_bullish and current_bearish:

                df.iloc[
                    i-1,
                    df.columns.get_loc("supply")
                ] = True

        return df

    def detect_order_blocks(self, df):

        df = df.copy()

        for i in range(1, len(df)):

            previous = df.iloc[i-1]
            current = df.iloc[i]

            previous_bearish = (
                previous["close"] < previous["open"]
            )

            previous_bullish = (
                previous["close"] > previous["open"]
            )

            bullish_move = (
                current["close"] > previous["high"]
            )

            bearish_move = (
                current["close"] < previous["low"]
            )

            if previous_bearish and bullish_move:

                df.iloc[
                    i-1,
                    df.columns.get_loc(
                        "bullish_order_block"
                    )
                ] = True

            if previous_bullish and bearish_move:

                df.iloc[
                    i-1,
                    df.columns.get_loc(
                        "bearish_order_block"
                    )
                ] = True

        return df

    def detect_fvg(self, df):

        df = df.copy()

        for i in range(2, len(df)):

            candle_1 = df.iloc[i-2]
            candle_3 = df.iloc[i]

            bullish_gap = (
                candle_1["high"] <
                candle_3["low"]
            )

            bearish_gap = (
                candle_1["low"] >
                candle_3["high"]
            )

            if bullish_gap:

                gap_size = (
                    candle_3["low"]
                    - candle_1["high"]
                )

                if gap_size >= self.fvg_min_size:

                    df.iloc[
                        i,
                        df.columns.get_loc(
                            "bullish_fvg"
                        )
                    ] = True

            if bearish_gap:

                gap_size = (
                    candle_1["low"]
                    - candle_3["high"]
                )

                if gap_size >= self.fvg_min_size:

                    df.iloc[
                        i,
                        df.columns.get_loc(
                            "bearish_fvg"
                        )
                    ] = True

        return df

    def detect_displacement(self, df):

        df = df.copy()

        for i in range(1, len(df)):

            current = df.iloc[i]

            candle_range = (
                current["high"] - current["low"]
            )

            previous_range = (
                df.iloc[i-1]["high"]
                -
                df.iloc[i-1]["low"]
            )

            if (
                previous_range > 0
                and
                candle_range >= previous_range * 1.5
            ):

                df.iloc[
                    i,
                    df.columns.get_loc(
                        "displacement"
                    )
                ] = True

        return df

    def analyze(self, df):

        df = self.add_columns(df)

        df = self.detect_support_resistance(df)
        df = self.detect_supply_demand(df)
        df = self.detect_order_blocks(df)
        df = self.detect_fvg(df)
        df = self.detect_displacement(df)

        return df
