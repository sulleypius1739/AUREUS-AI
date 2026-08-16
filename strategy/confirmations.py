import numpy as np
import pandas as pd


class ConfirmationAnalyzer:

    def __init__(
        self,
        rejection_wick_ratio=1.5
    ):
        self.rejection_wick_ratio = rejection_wick_ratio

    # =========================================================
    # PREPARE COLUMNS
    # =========================================================

    def add_columns(self, df):

        df = df.copy()

        columns = [
            "bullish_engulfing",
            "bearish_engulfing",
            "bullish_rejection",
            "bearish_rejection",
            "displacement"
        ]

        for column in columns:

            if column not in df.columns:
                df[column] = False

        return df

    # =========================================================
    # ENGULFING PATTERNS
    # =========================================================

    def detect_engulfing(self, df):

        df = df.copy()

        opens = df["open"].to_numpy(dtype=float)
        closes = df["close"].to_numpy(dtype=float)

        bullish = np.zeros(len(df), dtype=bool)
        bearish = np.zeros(len(df), dtype=bool)

        for i in range(1, len(df)):

            previous_open = opens[i - 1]
            previous_close = closes[i - 1]

            current_open = opens[i]
            current_close = closes[i]

            # Previous candle bearish,
            # current candle bullish and engulfs it.
            if (
                previous_close < previous_open
                and
                current_close > current_open
                and
                current_open <= previous_close
                and
                current_close >= previous_open
            ):
                bullish[i] = True

            # Previous candle bullish,
            # current candle bearish and engulfs it.
            elif (
                previous_close > previous_open
                and
                current_close < current_open
                and
                current_open >= previous_close
                and
                current_close <= previous_open
            ):
                bearish[i] = True

        df["bullish_engulfing"] = bullish
        df["bearish_engulfing"] = bearish

        return df

    # =========================================================
    # REJECTION CANDLES
    # =========================================================

    def detect_rejection(self, df):

        df = df.copy()

        opens = df["open"].to_numpy(dtype=float)
        highs = df["high"].to_numpy(dtype=float)
        lows = df["low"].to_numpy(dtype=float)
        closes = df["close"].to_numpy(dtype=float)

        bullish = np.zeros(len(df), dtype=bool)
        bearish = np.zeros(len(df), dtype=bool)

        ratio = self.rejection_wick_ratio

        for i in range(len(df)):

            body = abs(closes[i] - opens[i])

            # Prevent a zero-body candle from causing
            # division problems.
            body = max(body, 1e-12)

            upper_wick = (
                highs[i]
                -
                max(opens[i], closes[i])
            )

            lower_wick = (
                min(opens[i], closes[i])
                -
                lows[i]
            )

            # Bullish rejection:
            # large lower wick relative to body.
            if (
                lower_wick >= body * ratio
                and
                lower_wick > upper_wick
            ):
                bullish[i] = True

            # Bearish rejection:
            # large upper wick relative to body.
            if (
                upper_wick >= body * ratio
                and
                upper_wick > lower_wick
            ):
                bearish[i] = True

        df["bullish_rejection"] = bullish
        df["bearish_rejection"] = bearish

        return df

    # =========================================================
    # DISPLACEMENT
    # =========================================================

    def detect_displacement(self, df):

        df = df.copy()

        opens = df["open"].to_numpy(dtype=float)
        highs = df["high"].to_numpy(dtype=float)
        lows = df["low"].to_numpy(dtype=float)
        closes = df["close"].to_numpy(dtype=float)

        displacement = np.zeros(len(df), dtype=bool)

        if len(df) < 2:
            df["displacement"] = displacement
            return df

        ranges = highs - lows

        # Use only previous candles to determine whether
        # the current candle is unusually large.
        for i in range(1, len(df)):

            previous_range = ranges[i - 1]

            current_range = ranges[i]

            if previous_range <= 0:
                continue

            body = abs(closes[i] - opens[i])

            # Current candle must have both:
            # 1. a larger-than-previous range
            # 2. a meaningful body
            if (
                current_range >= previous_range * 1.5
                and
                body >= current_range * 0.5
            ):
                displacement[i] = True

        df["displacement"] = displacement

        return df

    # =========================================================
    # COMPLETE ANALYSIS
    # =========================================================

    def analyze(self, df):

        df = df.copy()

        df = self.add_columns(df)

        df = self.detect_engulfing(df)

        df = self.detect_rejection(df)

        df = self.detect_displacement(df)

        return df
