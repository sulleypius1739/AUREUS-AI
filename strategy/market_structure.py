import pandas as pd
import numpy as np


class MarketStructure:

    def __init__(self, swing_length=3):
        self.swing_length = swing_length

    # =========================================================
    # DETECT SWING HIGHS / LOWS
    # =========================================================
    #
    # CAUSALITY
    # ---------
    # A swing high/low at index i can only be confirmed once
    # `swing_length` candles AFTER i exist. We store TWO sets
    # of columns:
    #
    #   swing_high / swing_low
    #       True at the ANCHOR index (event time) — the actual
    #       candle that turned out to be the swing. Useful for
    #       labeling/plotting only. NEVER usable for a live
    #       trading decision at that index — it wasn't
    #       knowable yet.
    #
    #   swing_high_confirmed / swing_low_confirmed
    #       True at the CONFIRMATION index (i + swing_length) —
    #       the earliest point this swing is actually knowable.
    #       This is what all downstream causal logic must use.
    #
    #   swing_high_price / swing_low_price
    #       The swing's price, stored at the CONFIRMATION index.
    # =========================================================

    def detect_swings(self, df):

        df = df.copy()

        n = self.swing_length
        length = len(df)

        highs = df["high"].to_numpy()
        lows = df["low"].to_numpy()

        swing_high = np.zeros(length, dtype=bool)
        swing_low = np.zeros(length, dtype=bool)

        swing_high_confirmed = np.zeros(length, dtype=bool)
        swing_low_confirmed = np.zeros(length, dtype=bool)

        swing_high_price = np.full(length, np.nan)
        swing_low_price = np.full(length, np.nan)

        for i in range(n, length - n):

            current_high = highs[i]
            left_high = highs[i - n:i]
            right_high = highs[i + 1:i + n + 1]

            if (
                current_high > left_high.max()
                and current_high > right_high.max()
            ):
                swing_high[i] = True
                confirm_index = i + n
                if confirm_index < length:
                    swing_high_confirmed[confirm_index] = True
                    swing_high_price[confirm_index] = current_high

            current_low = lows[i]
            left_low = lows[i - n:i]
            right_low = lows[i + 1:i + n + 1]

            if (
                current_low < left_low.min()
                and current_low < right_low.min()
            ):
                swing_low[i] = True
                confirm_index = i + n
                if confirm_index < length:
                    swing_low_confirmed[confirm_index] = True
                    swing_low_price[confirm_index] = current_low

        df["swing_high"] = swing_high
        df["swing_low"] = swing_low
        df["swing_high_confirmed"] = swing_high_confirmed
        df["swing_low_confirmed"] = swing_low_confirmed
        df["swing_high_price"] = swing_high_price
        df["swing_low_price"] = swing_low_price

        return df

    # =========================================================
    # CLASSIFY SWING STRUCTURE
    # =========================================================
    #
    # Uses ONLY the confirmed swing columns. The structure
    # label at index i reflects what was actually knowable at
    # index i — not what the anchor candle later turned out
    # to represent.
    # =========================================================

    def classify_structure(self, df):

        df = df.copy()
        length = len(df)

        structure = np.full(length, None, dtype=object)

        swing_high_confirmed = df["swing_high_confirmed"].to_numpy()
        swing_low_confirmed = df["swing_low_confirmed"].to_numpy()
        swing_high_price = df["swing_high_price"].to_numpy()
        swing_low_price = df["swing_low_price"].to_numpy()

        previous_swing_high = None
        previous_swing_low = None

        for i in range(length):

            if swing_high_confirmed[i]:

                current_high = swing_high_price[i]

                if previous_swing_high is not None:

                    if current_high > previous_swing_high:
                        structure[i] = "HH"

                    elif current_high < previous_swing_high:
                        structure[i] = "LH"

                previous_swing_high = current_high

            if swing_low_confirmed[i]:

                current_low = swing_low_price[i]

                if previous_swing_low is not None:

                    if current_low > previous_swing_low:
                        structure[i] = "HL"

                    elif current_low < previous_swing_low:
                        structure[i] = "LL"

                previous_swing_low = current_low

        df["structure"] = structure

        return df

    # =========================================================
    # DETERMINE BIAS
    # =========================================================
    #
    # NOTE: this remains a single end-of-data summary bias,
    # used only for the printed diagnostic line. It is NOT
    # used per-candle for trade decisions in aureus_strategy.py
    # today. A rolling, causal, per-candle bias is a genuine
    # future improvement but is deliberately not implemented
    # here — it's a scoring/architecture change, not a bug fix,
    # and belongs in a separate pass.
    # =========================================================

    def determine_bias(self, df):

        structure = df["structure"].dropna()

        if len(structure) < 2:
            return "neutral"

        recent_high = None
        recent_low = None

        for value in reversed(structure.to_numpy()):

            if recent_high is None and value in ["HH", "LH"]:
                recent_high = value

            if recent_low is None and value in ["HL", "LL"]:
                recent_low = value

            if recent_high is not None and recent_low is not None:
                break

        if recent_high == "HH" and recent_low == "HL":
            return "bullish"

        if recent_high == "LH" and recent_low == "LL":
            return "bearish"

        return "neutral"

    def analyze(self, df):
        df = self.detect_swings(df)
        df = self.classify_structure(df)
        bias = self.determine_bias(df)
        return df, bias
