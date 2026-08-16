import numpy as np


class MarketStructure:
    """
    AUREUS Market Structure Analyzer

    Detects:

        - Swing highs
        - Swing lows
        - Confirmed swing highs
        - Confirmed swing lows
        - HH = Higher High
        - HL = Higher Low
        - LH = Lower High
        - LL = Lower Low
        - Rolling structural bias

    IMPORTANT
    =========
    A swing at candle i requires `swing_length` candles AFTER
    candle i before it can be confirmed.

    Example with swing_length = 3:

        Actual swing:       candle 100
        Confirmation:       candle 103

    Therefore the strategy is only allowed to use the swing
    from candle 103 onward.

    This prevents future-information leakage.
    """

    def __init__(self, swing_length=3):

        if swing_length < 1:
            raise ValueError(
                "swing_length must be >= 1"
            )

        self.swing_length = int(
            swing_length
        )

    # =========================================================
    # DETECT SWINGS
    # =========================================================

    def detect_swings(self, df):

        df = df.copy()

        required = [
            "high",
            "low"
        ]

        missing = [
            column
            for column in required
            if column not in df.columns
        ]

        if missing:
            raise ValueError(
                "Missing required market structure columns: "
                + ", ".join(missing)
            )

        n = self.swing_length
        length = len(df)

        highs = df[
            "high"
        ].to_numpy(
            dtype=float
        )

        lows = df[
            "low"
        ].to_numpy(
            dtype=float
        )

        # -----------------------------------------------------
        # Anchor/event columns
        #
        # These identify where the swing actually occurred.
        # They are NOT causal trading signals.
        # -----------------------------------------------------

        swing_high = np.zeros(
            length,
            dtype=bool
        )

        swing_low = np.zeros(
            length,
            dtype=bool
        )

        # -----------------------------------------------------
        # Confirmation columns
        #
        # These identify when the swing becomes known.
        # These ARE the columns downstream modules should use.
        # -----------------------------------------------------

        confirmed_swing_high = np.zeros(
            length,
            dtype=bool
        )

        confirmed_swing_low = np.zeros(
            length,
            dtype=bool
        )

        # -----------------------------------------------------
        # Store the original swing price at the confirmation
        # candle.
        # -----------------------------------------------------

        swing_high_price = np.full(
            length,
            np.nan
        )

        swing_low_price = np.full(
            length,
            np.nan
        )

        # =====================================================
        # FIND CANDIDATE SWINGS
        # =====================================================

        for i in range(
            n,
            length - n
        ):

            current_high = highs[i]

            current_low = lows[i]

            left_high = highs[
                i - n:i
            ]

            right_high = highs[
                i + 1:i + n + 1
            ]

            left_low = lows[
                i - n:i
            ]

            right_low = lows[
                i + 1:i + n + 1
            ]

            # -------------------------------------------------
            # SWING HIGH
            # -------------------------------------------------

            if (
                current_high
                >
                left_high.max()
                and
                current_high
                >
                right_high.max()
            ):

                swing_high[i] = True

                confirmation_index = (
                    i + n
                )

                if confirmation_index < length:

                    confirmed_swing_high[
                        confirmation_index
                    ] = True

                    swing_high_price[
                        confirmation_index
                    ] = current_high

            # -------------------------------------------------
            # SWING LOW
            # -------------------------------------------------

            if (
                current_low
                <
                left_low.min()
                and
                current_low
                <
                right_low.min()
            ):

                swing_low[i] = True

                confirmation_index = (
                    i + n
                )

                if confirmation_index < length:

                    confirmed_swing_low[
                        confirmation_index
                    ] = True

                    swing_low_price[
                        confirmation_index
                    ] = current_low

        # =====================================================
        # SAVE COLUMNS
        # =====================================================

        df[
            "swing_high"
        ] = swing_high

        df[
            "swing_low"
        ] = swing_low

        df[
            "confirmed_swing_high"
        ] = confirmed_swing_high

        df[
            "confirmed_swing_low"
        ] = confirmed_swing_low

        df[
            "swing_high_price"
        ] = swing_high_price

        df[
            "swing_low_price"
        ] = swing_low_price

        return df

    # =========================================================
    # CLASSIFY STRUCTURE
    # =========================================================

    def classify_structure(self, df):

        df = df.copy()

        length = len(df)

        structure = np.full(
            length,
            None,
            dtype=object
        )

        confirmed_highs = df[
            "confirmed_swing_high"
        ].to_numpy(
            dtype=bool
        )

        confirmed_lows = df[
            "confirmed_swing_low"
        ].to_numpy(
            dtype=bool
        )

        high_prices = df[
            "swing_high_price"
        ].to_numpy(
            dtype=float
        )

        low_prices = df[
            "swing_low_price"
        ].to_numpy(
            dtype=float
        )

        previous_swing_high = None
        previous_swing_low = None

        # =====================================================
        # WALK FORWARD THROUGH TIME
        # =====================================================

        for i in range(length):

            # -------------------------------------------------
            # CONFIRMED HIGH
            # -------------------------------------------------

            if confirmed_highs[i]:

                current_high = (
                    high_prices[i]
                )

                if (
                    not np.isnan(current_high)
                ):

                    if (
                        previous_swing_high
                        is not None
                    ):

                        if (
                            current_high
                            >
                            previous_swing_high
                        ):

                            structure[i] = "HH"

                        elif (
                            current_high
                            <
                            previous_swing_high
                        ):

                            structure[i] = "LH"

                    previous_swing_high = (
                        current_high
                    )

            # -------------------------------------------------
            # CONFIRMED LOW
            # -------------------------------------------------

            if confirmed_lows[i]:

                current_low = (
                    low_prices[i]
                )

                if (
                    not np.isnan(current_low)
                ):

                    if (
                        previous_swing_low
                        is not None
                    ):

                        if (
                            current_low
                            >
                            previous_swing_low
                        ):

                            structure[i] = "HL"

                        elif (
                            current_low
                            <
                            previous_swing_low
                        ):

                            structure[i] = "LL"

                    previous_swing_low = (
                        current_low
                    )

        df[
            "structure"
        ] = structure

        return df

    # =========================================================
    # DETERMINE ROLLING BIAS
    # =========================================================

    def determine_bias(self, df):

        length = len(df)

        biases = np.full(
            length,
            "neutral",
            dtype=object
        )

        structure = df[
            "structure"
        ].to_numpy(
            dtype=object
        )

        latest_high_structure = None
        latest_low_structure = None

        # =====================================================
        # WALK FORWARD
        # =====================================================
        #
        # At candle i, only structure confirmed by candle i
        # can affect the bias.
        #
        # Therefore this is causal.
        # =====================================================

        for i in range(length):

            value = structure[i]

            if value in [
                "HH",
                "LH"
            ]:

                latest_high_structure = value

            elif value in [
                "HL",
                "LL"
            ]:

                latest_low_structure = value

            # -------------------------------------------------
            # BULLISH
            # -------------------------------------------------

            if (
                latest_high_structure
                == "HH"
                and
                latest_low_structure
                == "HL"
            ):

                biases[i] = "bullish"

            # -------------------------------------------------
            # BEARISH
            # -------------------------------------------------

            elif (
                latest_high_structure
                == "LH"
                and
                latest_low_structure
                == "LL"
            ):

                biases[i] = "bearish"

            else:

                biases[i] = "neutral"

        return biases

    # =========================================================
    # COMPLETE ANALYSIS
    # =========================================================

    def analyze(self, df):

        df = df.copy()

        # -----------------------------------------------------
        # Validate
        # -----------------------------------------------------

        required = [
            "high",
            "low"
        ]

        missing = [
            column
            for column in required
            if column not in df.columns
        ]

        if missing:

            raise ValueError(
                "Missing required market structure columns: "
                + ", ".join(missing)
            )

        # -----------------------------------------------------
        # Detect swings
        # -----------------------------------------------------

        df = self.detect_swings(
            df
        )

        # -----------------------------------------------------
        # Classify HH / HL / LH / LL
        # -----------------------------------------------------

        df = self.classify_structure(
            df
        )

        # -----------------------------------------------------
        # Rolling causal bias
        # -----------------------------------------------------

        biases = self.determine_bias(
            df
        )

        df[
            "structure_bias"
        ] = biases

        # -----------------------------------------------------
        # Final diagnostic bias
        #
        # This is simply the last known bias and is useful for
        # the runner's summary output.
        # -----------------------------------------------------

        if len(biases) > 0:

            current_bias = biases[-1]

        else:

            current_bias = "neutral"

        return df, current_bias
