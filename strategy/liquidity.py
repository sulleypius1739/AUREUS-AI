import numpy as np
import pandas as pd


class LiquidityAnalyzer:
    """
    AUREUS Liquidity Analyzer

    Detects:

        - Equal highs
        - Equal lows
        - Buy-side liquidity
        - Sell-side liquidity
        - Buy-side liquidity sweeps
        - Sell-side liquidity sweeps

    IMPORTANT
    =========
    Liquidity is created from CONFIRMED swing points.

    A liquidity level cannot be swept on the same candle on which
    it is created.

    This is deliberately causal so the backtester cannot use
    information that would not have existed at that point in
    historical time.
    """

    def __init__(
        self,
        swing_lookback=3,
        equal_tolerance=0.0002,
        minimum_separation=3,
        liquidity_expiry=100
    ):

        self.swing_lookback = int(
            swing_lookback
        )

        self.equal_tolerance = float(
            equal_tolerance
        )

        self.minimum_separation = int(
            minimum_separation
        )

        self.liquidity_expiry = int(
            liquidity_expiry
        )

    # =========================================================
    # PREPARE COLUMNS
    # =========================================================

    def add_columns(self, df):

        df = df.copy()

        columns = [
            "equal_high",
            "equal_low",
            "buy_side_liquidity",
            "sell_side_liquidity",
            "buy_side_sweep",
            "sell_side_sweep",
            "liquidity_level_high",
            "liquidity_level_low"
        ]

        for column in columns:

            if column not in df.columns:

                if (
                    column
                    in [
                        "liquidity_level_high",
                        "liquidity_level_low"
                    ]
                ):

                    df[column] = np.nan

                else:

                    df[column] = False

        return df

    # =========================================================
    # PRICE EQUALITY
    # =========================================================

    def _prices_are_equal(
        self,
        price1,
        price2
    ):

        if (
            price1 is None
            or
            price2 is None
        ):

            return False

        if (
            pd.isna(price1)
            or
            pd.isna(price2)
        ):

            return False

        price1 = float(price1)
        price2 = float(price2)

        difference = abs(
            price1
            -
            price2
        )

        reference = max(
            abs(price1),
            abs(price2),
            1e-12
        )

        relative_difference = (
            difference
            /
            reference
        )

        return (
            relative_difference
            <=
            self.equal_tolerance
        )

    # =========================================================
    # ENSURE CONFIRMED SWINGS EXIST
    # =========================================================

    def _ensure_swing_columns(self, df):

        df = df.copy()

        # -----------------------------------------------------
        # Preferred canonical columns from MarketStructure.
        # -----------------------------------------------------

        if (
            "confirmed_swing_high"
            in df.columns
            and
            "confirmed_swing_low"
            in df.columns
        ):

            return df

        # -----------------------------------------------------
        # Compatibility with the alternate naming convention
        # that existed in the damaged version.
        # -----------------------------------------------------

        if (
            "swing_high_confirmed"
            in df.columns
        ):

            df[
                "confirmed_swing_high"
            ] = df[
                "swing_high_confirmed"
            ]

        if (
            "swing_low_confirmed"
            in df.columns
        ):

            df[
                "confirmed_swing_low"
            ] = df[
                "swing_low_confirmed"
            ]

        # -----------------------------------------------------
        # If MarketStructure was not run, create causal
        # fallback swings.
        #
        # This should normally NOT be necessary.
        # -----------------------------------------------------

        if (
            "confirmed_swing_high"
            not in df.columns
            or
            "confirmed_swing_low"
            not in df.columns
        ):

            df = self._create_fallback_swings(
                df
            )

        return df

    # =========================================================
    # FALLBACK SWINGS
    # =========================================================

    def _create_fallback_swings(self, df):

        df = df.copy()

        n = self.swing_lookback
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

        confirmed_high = np.zeros(
            length,
            dtype=bool
        )

        confirmed_low = np.zeros(
            length,
            dtype=bool
        )

        for i in range(
            n,
            length - n
        ):

            high_is_swing = (
                highs[i]
                >
                highs[
                    i - n:i
                ].max()
                and
                highs[i]
                >
                highs[
                    i + 1:i + n + 1
                ].max()
            )

            low_is_swing = (
                lows[i]
                <
                lows[
                    i - n:i
                ].min()
                and
                lows[i]
                <
                lows[
                    i + 1:i + n + 1
                ].min()
            )

            confirmation_index = (
                i + n
            )

            if (
                high_is_swing
                and
                confirmation_index < length
            ):

                confirmed_high[
                    confirmation_index
                ] = True

            if (
                low_is_swing
                and
                confirmation_index < length
            ):

                confirmed_low[
                    confirmation_index
                ] = True

        df[
            "confirmed_swing_high"
        ] = confirmed_high

        df[
            "confirmed_swing_low"
        ] = confirmed_low

        return df

    # =========================================================
    # FIND EQUAL HIGHS
    # =========================================================

    def find_equal_highs(self, df):

        df = df.copy()

        df = self._ensure_swing_columns(
            df
        )

        length = len(df)

        equal_high = np.zeros(
            length,
            dtype=bool
        )

        buy_side_liquidity = np.zeros(
            length,
            dtype=bool
        )

        liquidity_level_high = np.full(
            length,
            np.nan
        )

        confirmed_highs = df[
            "confirmed_swing_high"
        ].to_numpy(
            dtype=bool
        )

        # -----------------------------------------------------
        # Prefer the actual swing price saved by
        # MarketStructure.
        # -----------------------------------------------------

        if (
            "swing_high_price"
            in df.columns
        ):

            swing_prices = df[
                "swing_high_price"
            ].to_numpy(
                dtype=float
            )

        else:

            swing_prices = np.full(
                length,
                np.nan
            )

            highs = df[
                "high"
            ].to_numpy(
                dtype=float
            )

            for i in range(length):

                if confirmed_highs[i]:

                    swing_index = max(
                        0,
                        i - self.swing_lookback
                    )

                    swing_prices[i] = (
                        highs[
                            swing_index
                        ]
                    )

        previous_highs = []

        active_liquidity = None

        # =====================================================
        # WALK FORWARD
        # =====================================================

        for i in range(length):

            # -------------------------------------------------
            # Remove expired reference swings.
            # -------------------------------------------------

            previous_highs = [
                item
                for item in previous_highs
                if (
                    i - item[0]
                    <=
                    self.liquidity_expiry
                )
            ]

            # -------------------------------------------------
            # New confirmed swing high
            # -------------------------------------------------

            if confirmed_highs[i]:

                swing_price = (
                    swing_prices[i]
                )

                if not np.isnan(
                    swing_price
                ):

                    matching_level = None

                    # -----------------------------------------
                    # Search previous confirmed swing highs.
                    # -----------------------------------------

                    for (
                        previous_index,
                        previous_price
                    ) in reversed(
                        previous_highs
                    ):

                        if (
                            i - previous_index
                            <
                            self.minimum_separation
                        ):

                            continue

                        if self._prices_are_equal(
                            swing_price,
                            previous_price
                        ):

                            matching_level = (
                                (
                                    swing_price
                                    +
                                    previous_price
                                )
                                /
                                2.0
                            )

                            break

                    # -----------------------------------------
                    # Equal high found.
                    # -----------------------------------------

                    if (
                        matching_level
                        is not None
                    ):

                        equal_high[i] = True

                        buy_side_liquidity[i] = True

                        active_liquidity = {
                            "price": matching_level,
                            "created_at": i
                        }

                        liquidity_level_high[i] = (
                            matching_level
                        )

                    # -----------------------------------------
                    # Save this confirmed swing for future
                    # comparisons.
                    # -----------------------------------------

                    previous_highs.append(
                        (
                            i,
                            swing_price
                        )
                    )

            # -------------------------------------------------
            # Propagate active liquidity level.
            # -------------------------------------------------

            if (
                active_liquidity
                is not None
            ):

                age = (
                    i
                    -
                    active_liquidity[
                        "created_at"
                    ]
                )

                if (
                    age
                    <=
                    self.liquidity_expiry
                ):

                    if np.isnan(
                        liquidity_level_high[i]
                    ):

                        liquidity_level_high[i] = (
                            active_liquidity[
                                "price"
                            ]
                        )

                else:

                    active_liquidity = None

        df[
            "equal_high"
        ] = equal_high

        df[
            "buy_side_liquidity"
        ] = buy_side_liquidity

        df[
            "liquidity_level_high"
        ] = liquidity_level_high

        return df

    # =========================================================
    # FIND EQUAL LOWS
    # =========================================================

    def find_equal_lows(self, df):

        df = df.copy()

        df = self._ensure_swing_columns(
            df
        )

        length = len(df)

        equal_low = np.zeros(
            length,
            dtype=bool
        )

        sell_side_liquidity = np.zeros(
            length,
            dtype=bool
        )

        liquidity_level_low = np.full(
            length,
            np.nan
        )

        confirmed_lows = df[
            "confirmed_swing_low"
        ].to_numpy(
            dtype=bool
        )

        if (
            "swing_low_price"
            in df.columns
        ):

            swing_prices = df[
                "swing_low_price"
            ].to_numpy(
                dtype=float
            )

        else:

            swing_prices = np.full(
                length,
                np.nan
            )

            lows = df[
                "low"
            ].to_numpy(
                dtype=float
            )

            for i in range(length):

                if confirmed_lows[i]:

                    swing_index = max(
                        0,
                        i - self.swing_lookback
                    )

                    swing_prices[i] = (
                        lows[
                            swing_index
                        ]
                    )

        previous_lows = []

        active_liquidity = None

        # =====================================================
        # WALK FORWARD
        # =====================================================

        for i in range(length):

            previous_lows = [
                item
                for item in previous_lows
                if (
                    i - item[0]
                    <=
                    self.liquidity_expiry
                )
            ]

            # -------------------------------------------------
            # New confirmed swing low
            # -------------------------------------------------

            if confirmed_lows[i]:

                swing_price = (
                    swing_prices[i]
                )

                if not np.isnan(
                    swing_price
                ):

                    matching_level = None

                    for (
                        previous_index,
                        previous_price
                    ) in reversed(
                        previous_lows
                    ):

                        if (
                            i - previous_index
                            <
                            self.minimum_separation
                        ):

                            continue

                        if self._prices_are_equal(
                            swing_price,
                            previous_price
                        ):

                            matching_level = (
                                (
                                    swing_price
                                    +
                                    previous_price
                                )
                                /
                                2.0
                            )

                            break

                    # -----------------------------------------
                    # Equal low found.
                    # -----------------------------------------

                    if (
                        matching_level
                        is not None
                    ):

                        equal_low[i] = True

                        sell_side_liquidity[i] = True

                        active_liquidity = {
                            "price": matching_level,
                            "created_at": i
                        }

                        liquidity_level_low[i] = (
                            matching_level
                        )

                    previous_lows.append(
                        (
                            i,
                            swing_price
                        )
                    )

            # -------------------------------------------------
            # Propagate active liquidity.
            # -------------------------------------------------

            if (
                active_liquidity
                is not None
            ):

                age = (
                    i
                    -
                    active_liquidity[
                        "created_at"
                    ]
                )

                if (
                    age
                    <=
                    self.liquidity_expiry
                ):

                    if np.isnan(
                        liquidity_level_low[i]
                    ):

                        liquidity_level_low[i] = (
                            active_liquidity[
                                "price"
                            ]
                        )

                else:

                    active_liquidity = None

        df[
            "equal_low"
        ] = equal_low

        df[
            "sell_side_liquidity"
        ] = sell_side_liquidity

        df[
            "liquidity_level_low"
        ] = liquidity_level_low

        return df

    # =========================================================
    # BUY-SIDE LIQUIDITY SWEEPS
    # =========================================================

    def detect_buy_side_sweeps(self, df):

        df = df.copy()

        highs = df[
            "high"
        ].to_numpy(
            dtype=float
        )

        closes = df[
            "close"
        ].to_numpy(
            dtype=float
        )

        levels = df[
            "liquidity_level_high"
        ].to_numpy()

        sweeps = np.zeros(
            len(df),
            dtype=bool
        )

        active_level = None
        level_created_at = None

        # =====================================================
        # WALK FORWARD
        # =====================================================

        for i in range(len(df)):

            current_level = levels[i]

            # -------------------------------------------------
            # Activate a NEW level.
            #
            # It cannot be swept on this same candle.
            # -------------------------------------------------

            if (
                not pd.isna(
                    current_level
                )
                and
                active_level is None
            ):

                active_level = float(
                    current_level
                )

                level_created_at = i

                continue

            # -------------------------------------------------
            # Need a previously established level.
            # -------------------------------------------------

            if (
                active_level
                is None
                or
                level_created_at
                is None
            ):

                continue

            # -------------------------------------------------
            # Expiry.
            # -------------------------------------------------

            age = (
                i
                -
                level_created_at
            )

            if (
                age
                >
                self.liquidity_expiry
            ):

                active_level = None
                level_created_at = None

                continue

            # -------------------------------------------------
            # BUY-SIDE SWEEP
            #
            # Price trades ABOVE the level and closes BELOW it.
            # -------------------------------------------------

            if (
                highs[i]
                >
                active_level
                and
                closes[i]
                <
                active_level
            ):

                sweeps[i] = True

                # Level has been consumed.
                active_level = None
                level_created_at = None

        df[
            "buy_side_sweep"
        ] = sweeps

        return df

    # =========================================================
    # SELL-SIDE LIQUIDITY SWEEPS
    # =========================================================

    def detect_sell_side_sweeps(self, df):

        df = df.copy()

        lows = df[
            "low"
        ].to_numpy(
            dtype=float
        )

        closes = df[
            "close"
        ].to_numpy(
            dtype=float
        )

        levels = df[
            "liquidity_level_low"
        ].to_numpy()

        sweeps = np.zeros(
            len(df),
            dtype=bool
        )

        active_level = None
        level_created_at = None

        # =====================================================
        # WALK FORWARD
        # =====================================================

        for i in range(len(df)):

            current_level = levels[i]

            # -------------------------------------------------
            # Activate new level.
            #
            # Cannot be swept on creation candle.
            # -------------------------------------------------

            if (
                not pd.isna(
                    current_level
                )
                and
                active_level is None
            ):

                active_level = float(
                    current_level
                )

                level_created_at = i

                continue

            if (
                active_level
                is None
                or
                level_created_at
                is None
            ):

                continue

            # -------------------------------------------------
            # Expiry.
            # -------------------------------------------------

            age = (
                i
                -
                level_created_at
            )

            if (
                age
                >
                self.liquidity_expiry
            ):

                active_level = None
                level_created_at = None

                continue

            # -------------------------------------------------
            # SELL-SIDE SWEEP
            #
            # Price trades BELOW the level and closes ABOVE it.
            # -------------------------------------------------

            if (
                lows[i]
                <
                active_level
                and
                closes[i]
                >
                active_level
            ):

                sweeps[i] = True

                active_level = None
                level_created_at = None

        df[
            "sell_side_sweep"
        ] = sweeps

        return df

    # =========================================================
    # COMPLETE LIQUIDITY ANALYSIS
    # =========================================================

    def analyze(self, df):

        df = self.add_columns(
            df
        )

        # -----------------------------------------------------
        # Make sure MarketStructure's confirmed swing columns
        # are available.
        # -----------------------------------------------------

        df = self._ensure_swing_columns(
            df
        )

        # -----------------------------------------------------
        # Detect equal highs / buy-side liquidity.
        # -----------------------------------------------------

        df = self.find_equal_highs(
            df
        )

        # -----------------------------------------------------
        # Detect equal lows / sell-side liquidity.
        # -----------------------------------------------------

        df = self.find_equal_lows(
            df
        )

        # -----------------------------------------------------
        # Detect sweeps.
        # -----------------------------------------------------

        df = self.detect_buy_side_sweeps(
            df
        )

        df = self.detect_sell_side_sweeps(
            df
        )

        return df
