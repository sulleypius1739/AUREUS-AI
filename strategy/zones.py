import pandas as pd
import numpy as np


class ZoneAnalyzer:

    def __init__(self, fvg_min_size=0.0):
        self.fvg_min_size = fvg_min_size

    # =========================================================
    # ADD REQUIRED COLUMNS
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
    # SUPPORT / RESISTANCE
    # =========================================================

    def detect_support_resistance(self, df):

        df = df.copy()

        highs = df["high"].to_numpy()
        lows = df["low"].to_numpy()

        support = np.zeros(
            len(df),
            dtype=bool
        )

        resistance = np.zeros(
            len(df),
            dtype=bool
        )

        if len(df) >= 3:

            # Current candle compared with candle immediately
            # before and after it.

            support[1:-1] = (
                (lows[1:-1] < lows[:-2])
                &
                (lows[1:-1] < lows[2:])
            )

            resistance[1:-1] = (
                (highs[1:-1] > highs[:-2])
                &
                (highs[1:-1] > highs[2:])
            )

        df["support"] = support
        df["resistance"] = resistance

        return df

    # =========================================================
    # SUPPLY / DEMAND
    # =========================================================

    def detect_supply_demand(self, df):

        df = df.copy()

        opens = df["open"].to_numpy()
        closes = df["close"].to_numpy()

        bullish = closes > opens
        bearish = closes < opens

        demand = np.zeros(
            len(df),
            dtype=bool
        )

        supply = np.zeros(
            len(df),
            dtype=bool
        )

        # Previous candle bearish + current bullish
        if len(df) >= 2:

            demand[:-1] = (
                bearish[:-1]
                &
                bullish[1:]
            )

            # Previous candle bullish + current bearish
            supply[:-1] = (
                bullish[:-1]
                &
                bearish[1:]
            )

        df["demand"] = demand
        df["supply"] = supply

        return df

    # =========================================================
    # ORDER BLOCKS
    # =========================================================

    def detect_order_blocks(self, df):

        df = df.copy()

        opens = df["open"].to_numpy()
        closes = df["close"].to_numpy()

        highs = df["high"].to_numpy()
        lows = df["low"].to_numpy()

        bullish = closes > opens
        bearish = closes < opens

        bullish_order_block = np.zeros(
            len(df),
            dtype=bool
        )

        bearish_order_block = np.zeros(
            len(df),
            dtype=bool
        )

        if len(df) >= 2:

            # Last bearish candle before bullish displacement
            bullish_order_block[:-1] = (
                bearish[:-1]
                &
                bullish[1:]
                &
                (closes[1:] > highs[:-1])
            )

            # Last bullish candle before bearish displacement
            bearish_order_block[:-1] = (
                bullish[:-1]
                &
                bearish[1:]
                &
                (closes[1:] < lows[:-1])
            )

        df[
            "bullish_order_block"
        ] = bullish_order_block

        df[
            "bearish_order_block"
        ] = bearish_order_block

        return df

    # =========================================================
    # FAIR VALUE GAPS
    # =========================================================

    def detect_fvg(self, df):

        df = df.copy()

        highs = df["high"].to_numpy()
        lows = df["low"].to_numpy()

        bullish_fvg = np.zeros(
            len(df),
            dtype=bool
        )

        bearish_fvg = np.zeros(
            len(df),
            dtype=bool
        )

        if len(df) >= 3:

            # Bullish FVG:
            #
            # candle 3 low > candle 1 high
            #
            bullish_gap = (
                lows[2:]
                -
                highs[:-2]
            )

            bullish_fvg[2:] = (
                bullish_gap
                >=
                self.fvg_min_size
            )

            # Bearish FVG:
            #
            # candle 3 high < candle 1 low

            bearish_gap = (
                lows[:-2]
                -
                highs[2:]
            )

            bearish_fvg[2:] = (
                bearish_gap
                >=
                self.fvg_min_size
            )

        df["bullish_fvg"] = bullish_fvg
        df["bearish_fvg"] = bearish_fvg

        return df

    # =========================================================
    # DISPLACEMENT
    # =========================================================

    def detect_displacement(self, df):

        df = df.copy()

        highs = df["high"].to_numpy()
        lows = df["low"].to_numpy()

        candle_range = highs - lows

        displacement = np.zeros(
            len(df),
            dtype=bool
        )

        if len(df) >= 2:

            valid_previous = candle_range[:-1] > 0

            displacement[1:] = (
                valid_previous
                &
                (
                    candle_range[1:]
                    >=
                    candle_range[:-1] * 1.5
                )
            )

        df["displacement"] = displacement

        return df

    # =========================================================
    # COMPLETE ANALYSIS
    # =========================================================

    def analyze(self, df):

        df = self.add_columns(df)

        df = self.detect_support_resistance(df)

        df = self.detect_supply_demand(df)

        df = self.detect_order_blocks(df)

        df = self.detect_fvg(df)

        df = self.detect_displacement(df)

        return df
