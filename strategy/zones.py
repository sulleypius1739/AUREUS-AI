import pandas as pd
import numpy as np


class ZoneAnalyzer:

    def __init__(self, fvg_min_size=0.0):
        self.fvg_min_size = fvg_min_size

    def add_columns(self, df):
        df = df.copy()

        bool_columns = [
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

        for column in bool_columns:
            if column not in df.columns:
                df[column] = False

        level_columns = [
            "bullish_order_block_level",
            "bearish_order_block_level"
        ]

        for column in level_columns:
            if column not in df.columns:
                df[column] = np.nan

        return df

    # =========================================================
    # SUPPORT / RESISTANCE
    # =========================================================
    #
    # CAUSALITY FIX
    # -------------
    # A local low/high at candle i can only be confirmed once
    # candle i+1 closes (we need i+1's low/high to know i was
    # a local extreme). The flag is now stored at i+1, not i.
    #
    # NOTE: these columns are currently unused in
    # aureus_strategy.py's scoring — this fix matters for
    # diagnostic accuracy today, and prevents a latent
    # look-ahead bug if these are ever wired into scoring later.
    # =========================================================

    def detect_support_resistance(self, df):

        df = df.copy()
        length = len(df)

        highs = df["high"].to_numpy()
        lows = df["low"].to_numpy()

        support = np.zeros(length, dtype=bool)
        resistance = np.zeros(length, dtype=bool)

        if length >= 3:

            cond_support = (
                (lows[1:-1] < lows[:-2])
                & (lows[1:-1] < lows[2:])
            )

            cond_resistance = (
                (highs[1:-1] > highs[:-2])
                & (highs[1:-1] > highs[2:])
            )

            # cond_*[k] corresponds to original candle i = k+1,
            # only knowable once candle i+1 = k+2 closes.
            support[2:2 + len(cond_support)] = cond_support
            resistance[2:2 + len(cond_resistance)] = cond_resistance

        df["support"] = support
        df["resistance"] = resistance

        return df

    # =========================================================
    # SUPPLY / DEMAND
    # =========================================================
    #
    # Same causality fix. Unused in scoring today — see note
    # above.
    # =========================================================

    def detect_supply_demand(self, df):

        df = df.copy()
        length = len(df)

        opens = df["open"].to_numpy()
        closes = df["close"].to_numpy()

        bullish = closes > opens
        bearish = closes < opens

        demand = np.zeros(length, dtype=bool)
        supply = np.zeros(length, dtype=bool)

        if length >= 2:

            cond_demand = bearish[:-1] & bullish[1:]
            cond_supply = bullish[:-1] & bearish[1:]

            # cond_*[k] corresponds to anchor candle i = k,
            # confirmed at i+1 = k+1.
            demand[1:] = cond_demand
            supply[1:] = cond_supply

        df["demand"] = demand
        df["supply"] = supply

        return df

    # =========================================================
    # ORDER BLOCKS
    # =========================================================
    #
    # CRITICAL FIX — this was the confirmed, LIVE look-ahead
    # bug that was corrupting real backtested trades.
    #
    # The anchor candle (last opposite-colour candle) is at
    # index i. The block only becomes valid once candle i+1
    # closes with the required displacement — the flag is now
    # stored at i+1 (confirmation), not i (anchor).
    #
    # The ANCHOR candle's own low/high is stored separately as
    # the structural level, since that's the price a stop-loss
    # should reference — NOT the confirmation candle's low/high.
    # =========================================================

    def detect_order_blocks(self, df):

        df = df.copy()
        length = len(df)

        opens = df["open"].to_numpy()
        closes = df["close"].to_numpy()
        highs = df["high"].to_numpy()
        lows = df["low"].to_numpy()

        bullish = closes > opens
        bearish = closes < opens

        bullish_order_block = np.zeros(length, dtype=bool)
        bearish_order_block = np.zeros(length, dtype=bool)

        bullish_order_block_level = np.full(length, np.nan)
        bearish_order_block_level = np.full(length, np.nan)

        if length >= 2:

            cond_bull = (
                bearish[:-1]
                & bullish[1:]
                & (closes[1:] > highs[:-1])
            )

            cond_bear = (
                bullish[:-1]
                & bearish[1:]
                & (closes[1:] < lows[:-1])
            )

            # Flag stored at the CONFIRMATION candle (i+1) —
            # this is the fix.
            bullish_order_block[1:] = cond_bull
            bearish_order_block[1:] = cond_bear

            # Level = the ANCHOR candle's low/high, stored
            # alongside the confirmation flag.
            bullish_order_block_level[1:] = np.where(
                cond_bull, lows[:-1], np.nan
            )

            bearish_order_block_level[1:] = np.where(
                cond_bear, highs[:-1], np.nan
            )

        df["bullish_order_block"] = bullish_order_block
        df["bearish_order_block"] = bearish_order_block
        df["bullish_order_block_level"] = bullish_order_block_level
        df["bearish_order_block_level"] = bearish_order_block_level

        return df

    # =========================================================
    # FAIR VALUE GAPS
    # =========================================================
    #
    # Already causal — bullish_fvg[i] uses lows[i] (candle 3,
    # the current candle) and highs[i-2] (candle 1, already
    # happened). No change needed.
    # =========================================================

    def detect_fvg(self, df):

        df = df.copy()
        length = len(df)

        highs = df["high"].to_numpy()
        lows = df["low"].to_numpy()

        bullish_fvg = np.zeros(length, dtype=bool)
        bearish_fvg = np.zeros(length, dtype=bool)

        if length >= 3:

            bullish_gap = lows[2:] - highs[:-2]
            bullish_fvg[2:] = bullish_gap >= self.fvg_min_size

            bearish_gap = lows[:-2] - highs[2:]
            bearish_fvg[2:] = bearish_gap >= self.fvg_min_size

        df["bullish_fvg"] = bullish_fvg
        df["bearish_fvg"] = bearish_fvg

        return df

    # =========================================================
    # DISPLACEMENT
    # =========================================================
    #
    # Already causal — displacement[i] compares candle_range[i]
    # (current) against candle_range[i-1] (previous). No change
    # needed.
    # =========================================================

    def detect_displacement(self, df):

        df = df.copy()
        length = len(df)

        highs = df["high"].to_numpy()
        lows = df["low"].to_numpy()

        candle_range = highs - lows

        displacement = np.zeros(length, dtype=bool)

        if length >= 2:

            valid_previous = candle_range[:-1] > 0

            displacement[1:] = (
                valid_previous
                & (candle_range[1:] >= candle_range[:-1] * 1.5)
            )

        df["displacement"] = displacement

        return df

    def analyze(self, df):
        df = self.add_columns(df)
        df = self.detect_support_resistance(df)
        df = self.detect_supply_demand(df)
        df = self.detect_order_blocks(df)
        df = self.detect_fvg(df)
        df = self.detect_displacement(df)
        return df
