import numpy as np
import pandas as pd


class ConfirmationAnalyzer:
    """
    AUREUS candle confirmation engine.

    Detects:

        - Bullish engulfing
        - Bearish engulfing
        - Bullish rejection
        - Bearish rejection

    All confirmations are causal.

    A confirmation on candle i uses only:
        - candle i
        - candle i-1

    No future candles are used.
    """

    def __init__(
        self,
        rejection_wick_ratio=0.50,
        rejection_body_ratio=0.20,
        engulfing_body_multiplier=1.0
    ):

        self.rejection_wick_ratio = float(
            rejection_wick_ratio
        )

        self.rejection_body_ratio = float(
            rejection_body_ratio
        )

        self.engulfing_body_multiplier = float(
            engulfing_body_multiplier
        )

    # =========================================================
    # PREPARE COLUMNS
    # =========================================================

    def add_columns(
        self,
        df
    ):

        df = df.copy()

        columns = [
            "bullish_engulfing",
            "bearish_engulfing",
            "bullish_rejection",
            "bearish_rejection"
        ]

        for column in columns:

            df[column] = False

        return df

    # =========================================================
    # CANDLE CONFIRMATIONS
    # =========================================================

    def analyze_candles(
        self,
        df
    ):

        df = df.copy()

        df = self.add_columns(
            df
        )

        if len(df) < 2:

            return df

        # -----------------------------------------------------
        # Convert to numpy arrays.
        # This is considerably faster than df.iloc inside
        # a 57,600-candle loop.
        # -----------------------------------------------------

        opens = (
            df["open"]
            .to_numpy(
                dtype=float
            )
        )

        closes = (
            df["close"]
            .to_numpy(
                dtype=float
            )
        )

        highs = (
            df["high"]
            .to_numpy(
                dtype=float
            )
        )

        lows = (
            df["low"]
            .to_numpy(
                dtype=float
            )
        )

        # =====================================================
        # CURRENT / PREVIOUS CANDLE
        # =====================================================

        previous_open = opens[:-1]
        previous_close = closes[:-1]

        current_open = opens[1:]
        current_close = closes[1:]

        previous_body = np.abs(
            previous_close
            -
            previous_open
        )

        current_body = np.abs(
            current_close
            -
            current_open
        )

        # =====================================================
        # BULLISH / BEARISH CANDLES
        # =====================================================

        previous_bearish = (
            previous_close
            <
            previous_open
        )

        previous_bullish = (
            previous_close
            >
            previous_open
        )

        current_bullish = (
            current_close
            >
            current_open
        )

        current_bearish = (
            current_close
            <
            current_open
        )

        # =====================================================
        # BULLISH ENGULFING
        # =====================================================

        bullish_engulfing = (

            previous_bearish

            &

            current_bullish

            &

            (
                current_open
                <=
                previous_close
            )

            &

            (
                current_close
                >=
                previous_open
            )

            &

            (
                current_body
                >=
                previous_body
                *
                self.engulfing_body_multiplier
            )

        )

        # =====================================================
        # BEARISH ENGULFING
        # =====================================================

        bearish_engulfing = (

            previous_bullish

            &

            current_bearish

            &

            (
                current_open
                >=
                previous_close
            )

            &

            (
                current_close
                <=
                previous_open
            )

            &

            (
                current_body
                >=
                previous_body
                *
                self.engulfing_body_multiplier
            )

        )

        # =====================================================
        # CURRENT CANDLE RANGE
        # =====================================================

        current_high = highs[1:]

        current_low = lows[1:]

        candle_range = (
            current_high
            -
            current_low
        )

        # Prevent division by zero.

        valid_range = (
            candle_range > 0
        )

        # =====================================================
        # WICKS
        # =====================================================

        upper_wick = (
            current_high
            -
            np.maximum(
                current_open,
                current_close
            )
        )

        lower_wick = (
            np.minimum(
                current_open,
                current_close
            )
            -
            current_low
        )

        # =====================================================
        # BODY / RANGE
        # =====================================================

        body_ratio = np.divide(
            current_body,
            candle_range,
            out=np.zeros_like(
                current_body
            ),
            where=valid_range
        )

        lower_wick_ratio = np.divide(
            lower_wick,
            candle_range,
            out=np.zeros_like(
                lower_wick
            ),
            where=valid_range
        )

        upper_wick_ratio = np.divide(
            upper_wick,
            candle_range,
            out=np.zeros_like(
                upper_wick
            ),
            where=valid_range
        )

        # =====================================================
        # BULLISH REJECTION
        # =====================================================
        #
        # We want:
        #
        # 1. Large lower wick
        # 2. Meaningful candle body
        # 3. Candle closes in the upper portion
        #
        # This is more selective than simply saying:
        #
        # lower wick >= 50% of range
        #
        # =====================================================

        bullish_rejection = (

            valid_range

            &

            (
                lower_wick_ratio
                >=
                self.rejection_wick_ratio
            )

            &

            (
                body_ratio
                >=
                self.rejection_body_ratio
            )

            &

            (
                current_close
                >
                current_open
            )

        )

        # =====================================================
        # BEARISH REJECTION
        # =====================================================

        bearish_rejection = (

            valid_range

            &

            (
                upper_wick_ratio
                >=
                self.rejection_wick_ratio
            )

            &

            (
                body_ratio
                >=
                self.rejection_body_ratio
            )

            &

            (
                current_close
                <
                current_open
            )

        )

        # =====================================================
        # WRITE RESULTS
        # =====================================================

        bullish_engulfing_full = np.zeros(
            len(df),
            dtype=bool
        )

        bearish_engulfing_full = np.zeros(
            len(df),
            dtype=bool
        )

        bullish_rejection_full = np.zeros(
            len(df),
            dtype=bool
        )

        bearish_rejection_full = np.zeros(
            len(df),
            dtype=bool
        )

        bullish_engulfing_full[1:] = (
            bullish_engulfing
        )

        bearish_engulfing_full[1:] = (
            bearish_engulfing
        )

        bullish_rejection_full[1:] = (
            bullish_rejection
        )

        bearish_rejection_full[1:] = (
            bearish_rejection
        )

        df[
            "bullish_engulfing"
        ] = bullish_engulfing_full

        df[
            "bearish_engulfing"
        ] = bearish_engulfing_full

        df[
            "bullish_rejection"
        ] = bullish_rejection_full

        df[
            "bearish_rejection"
        ] = bearish_rejection_full

        return df

    # =========================================================
    # COMPLETE ANALYSIS
    # =========================================================

    def analyze(
        self,
        df
    ):

        return self.analyze_candles(
            df
        )
