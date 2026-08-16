import numpy as np
import pandas as pd


class MarketStructure:
    """
    AUREUS Market Structure Analyzer

    Detects confirmed swing highs/lows and classifies them as:

        HH = Higher High
        HL = Higher Low
        LH = Lower High
        LL = Lower Low

    IMPORTANT:
    A swing using `swing_length = 3` requires three candles
    AFTER the candidate candle to confirm it.

    Therefore:

        candidate swing at i
        confirmed at i + 3

    The confirmed swing information is shifted forward so that
    the strategy cannot use future information.
    """

    def __init__(
        self,
        swing_length=3
    ):

        if swing_length < 1:

            raise ValueError(
                "swing_length must be >= 1"
            )

        self.swing_length = int(
            swing_length
        )

    # =========================================================
    # DETECT CONFIRMED SWINGS
    # =========================================================

    def detect_swings(self, df):

        df = df.copy()

        n = self.swing_length

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

        length = len(df)

        # -----------------------------------------------------
        # Candidate swing arrays
        #
        # These describe WHERE the swing actually occurred.
        # -----------------------------------------------------

        candidate_swing_high = np.zeros(
            length,
            dtype=bool
        )

        candidate_swing_low = np.zeros(
            length,
            dtype=bool
        )

        # -----------------------------------------------------
        # Confirmed swing arrays
        #
        # These describe WHEN the strategy is allowed to know
        # about the swing.
        # -----------------------------------------------------

        confirmed_swing_high = np.zeros(
            length,
            dtype=bool
        )

        confirmed_swing_low = np.zeros(
            length,
            dtype=bool
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
            # Swing HIGH
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

                candidate_swing_high[i] = True

            # -------------------------------------------------
            # Swing LOW
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

                candidate_swing_low[i] = True

        # =====================================================
        # MOVE INFORMATION TO CONFIRMATION CANDLE
        # =====================================================
        #
        # Example:
        #
        # swing_length = 3
        #
        # Candle 100 is a swing high.
        #
        # We don't know this until candle 103 closes.
        #
        # Therefore:
        #
        # candidate swing:
        #     index 100
        #
        # confirmation:
        #     index 103
        #
        # =====================================================

        for i in range(
            length
        ):

            confirmation_index = (
                i + n
            )

            if (
                candidate_swing_high[i]
                and
                confirmation_index < length
            ):

                confirmed_swing_high[
                    confirmation_index
                ] = True

            if (
                candidate_swing_low[i]
                and
                confirmation_index < length
            ):

                confirmed_swing_low[
                    confirmation_index
                ] = True

        # -----------------------------------------------------
        # Store both pieces of information.
        #
        # The candidate columns describe the actual swing
        # location.
        #
        # The confirmed columns describe when the information
        # becomes available.
        # -----------------------------------------------------

        df[
            "swing_high"
        ] = candidate_swing_high

        df[
            "swing_low"
        ] = candidate_swing_low

        df[
            "confirmed_swing_high"
        ] = confirmed_swing_high

        df[
            "confirmed_swing_low"
        ] = confirmed_swing_low

        return df

    # =========================================================
    # CLASSIFY SWING STRUCTURE
    # =========================================================

    def classify_structure(
        self,
        df
    ):

        df = df.copy()

        length = len(df)

        structure = np.full(
            length,
            None,
            dtype=object
        )

        # -----------------------------------------------------
        # IMPORTANT
        #
        # We classify only when the swing becomes confirmed.
        #
        # The actual price being compared is the ORIGINAL
        # swing price, not the confirmation candle price.
        # -----------------------------------------------------

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

        confirmed_highs = (
            df[
                "confirmed_swing_high"
            ]
            .to_numpy(
                dtype=bool
            )
        )

        confirmed_lows = (
            df[
                "confirmed_swing_low"
            ]
            .to_numpy(
                dtype=bool
            )
        )

        n = self.swing_length

        previous_swing_high = None

        previous_swing_low = None

        # =====================================================
        # WALK FORWARD THROUGH TIME
        # =====================================================

        for confirmation_index in range(
            length
        ):

            # =================================================
            # CONFIRMED SWING HIGH
            # =================================================

            if confirmed_highs[
                confirmation_index
            ]:

                swing_index = (
                    confirmation_index
                    - n
                )

                if swing_index >= 0:

                    current_high = (
                        highs[
                            swing_index
                        ]
                    )

                    if (
                        previous_swing_high
                        is not None
                    ):

                        if (
                            current_high
                            >
                            previous_swing_high
                        ):

                            structure[
                                confirmation_index
                            ] = "HH"

                        elif (
                            current_high
                            <
                            previous_swing_high
                        ):

                            structure[
                                confirmation_index
                            ] = "LH"

                    previous_swing_high = (
                        current_high
                    )

            # =================================================
            # CONFIRMED SWING LOW
            # =================================================

            if confirmed_lows[
                confirmation_index
            ]:

                swing_index = (
                    confirmation_index
                    - n
                )

                if swing_index >= 0:

                    current_low = (
                        lows[
                            swing_index
                        ]
                    )

                    if (
                        previous_swing_low
                        is not None
                    ):

                        if (
                            current_low
                            >
                            previous_swing_low
                        ):

                            structure[
                                confirmation_index
                            ] = "HL"

                        elif (
                            current_low
                            <
                            previous_swing_low
                        ):

                            structure[
                                confirmation_index
                            ] = "LL"

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

    def determine_bias(
        self,
        df
    ):

        length = len(df)

        biases = np.full(
            length,
            "neutral",
            dtype=object
        )

        structure = (
            df["structure"]
            .to_numpy(
                dtype=object
            )
        )

        latest_high_structure = None

        latest_low_structure = None

        # =====================================================
        # WALK FORWARD
        # =====================================================
        #
        # At every candle we only use structure that has already
        # been confirmed.
        # =====================================================

        for i in range(
            length
        ):

            value = structure[i]

            if value in [
                "HH",
                "LH"
            ]:

                latest_high_structure = (
                    value
                )

            elif value in [
                "HL",
                "LL"
            ]:

                latest_low_structure = (
                    value
                )

            # -------------------------------------------------
            # Bullish structure
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
            # Bearish structure
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

    def analyze(
        self,
        df
    ):

        df = df.copy()

        # -----------------------------------------------------
        # Validate required columns
        # -----------------------------------------------------

        required_columns = [
            "high",
            "low"
        ]

        missing = [
            column
            for column in required_columns
            if column not in df.columns
        ]

        if missing:

            raise ValueError(
                "Missing required market structure "
                "columns: "
                +
                ", ".join(missing)
            )

        # -----------------------------------------------------
        # Detect swings
        # -----------------------------------------------------

        df = self.detect_swings(
            df
        )

        # -----------------------------------------------------
        # Classify structure
        # -----------------------------------------------------

        df = self.classify_structure(
            df
        )

        # -----------------------------------------------------
        # Rolling structural bias
        # -----------------------------------------------------

        biases = self.determine_bias(
            df
        )

        df[
            "structure_bias"
        ] = biases

        # -----------------------------------------------------
        # Current/latest bias
        #
        # Used by the rest of the existing strategy interface.
        # -----------------------------------------------------

        current_bias = (
            biases[-1]
            if len(biases) > 0
            else "neutral"
        )

        return df, current_bias
