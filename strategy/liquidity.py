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

    IMPORTANT:

    Liquidity is based primarily on CONFIRMED swing points.

    A liquidity level must exist BEFORE price can sweep it.

    This prevents the backtester from using information that
    would not have been available at the time of the trade.
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
        """
        Determines whether two prices are sufficiently close
        to represent the same liquidity level.

        Uses relative tolerance so the method is not tied to
        one particular instrument's price scale.
        """

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

        difference = abs(
            float(price1)
            -
            float(price2)
        )

        reference = max(
            abs(float(price1)),
            abs(float(price2)),
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
    # FALLBACK SWING DETECTION
    # =========================================================

    def _create_fallback_swings(
        self,
        df
    ):
        """
        Fallback swing detection.

        This is only used if MarketStructure has not already
        created confirmed_swing_high / confirmed_swing_low.

        A swing at candle i becomes known at:

            i + swing_lookback

        Therefore the fallback does NOT expose the swing early.
        """

        df = df.copy()

        n = self.swing_lookback

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

    def find_equal_highs(
        self,
        df
    ):
        """
        Detect equal highs using confirmed swing highs.

        A new buy-side liquidity level is created only when
        a newly confirmed swing high is sufficiently close to
        a previous confirmed swing high.

        The liquidity level is NOT considered swept on the
        candle where it is created.
        """

        df = df.copy()

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

        # -----------------------------------------------------
        # Use MarketStructure swings if available.
        # Otherwise create fallback confirmed swings.
        # -----------------------------------------------------

        if (
            "confirmed_swing_high"
            not in df.columns
        ):

            df = self._create_fallback_swings(
                df
            )

        confirmed_highs = (
            df[
                "confirmed_swing_high"
            ]
            .to_numpy(
                dtype=bool
            )
        )

        highs = (
            df["high"]
            .to_numpy(
                dtype=float
            )
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
                    <= self.liquidity_expiry
                )
            ]

            # =================================================
            # NEW CONFIRMED SWING HIGH
            # =================================================

            if confirmed_highs[i]:

                swing_index = max(
                    0,
                    i - self.swing_lookback
                )

                swing_price = highs[
                    swing_index
                ]

                matching_level = None

                # -------------------------------------------------
                # Compare this newly confirmed swing with older
                # confirmed swing highs.
                # -------------------------------------------------

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

                # =================================================
                # EQUAL HIGH FOUND
                # =================================================

                if matching_level is not None:

                    equal_high[i] = True

                    buy_side_liquidity[i] = True

                    active_liquidity = {
                        "price": matching_level,
                        "created_at": i
                    }

                    liquidity_level_high[i] = (
                        matching_level
                    )

                # -------------------------------------------------
                # Save the newly confirmed swing.
                # -------------------------------------------------

                previous_highs.append(
                    (
                        i,
                        swing_price
                    )
                )

            # =================================================
            # PROPAGATE ACTIVE LIQUIDITY
            # =================================================

            if active_liquidity is not None:

                age = (
                    i
                    -
                    active_liquidity["created_at"]
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
                            active_liquidity["price"]
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

    def find_equal_lows(
        self,
        df
    ):
        """
        Detect equal lows using confirmed swing lows.

        A new sell-side liquidity level is created only when
        a newly confirmed swing low is sufficiently close to
        a previous confirmed swing low.
        """

        df = df.copy()

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

        if (
            "confirmed_swing_low"
            not in df.columns
        ):

            df = self._create_fallback_swings(
                df
            )

        confirmed_lows = (
            df[
                "confirmed_swing_low"
            ]
            .to_numpy(
                dtype=bool
            )
        )

        lows = (
            df["low"]
            .to_numpy(
                dtype=float
            )
        )

        previous_lows = []

        active_liquidity = None

        # =====================================================
        # WALK FORWARD
        # =====================================================

        for i in range(length):

            # -------------------------------------------------
            # Remove expired reference swings.
            # -------------------------------------------------

            previous_lows = [
                item
                for item in previous_lows
                if (
                    i - item[0]
                    <= self.liquidity_expiry
                )
            ]

            # =================================================
            # NEW CONFIRMED SWING LOW
            # =================================================

            if confirmed_lows[i]:

                swing_index = max(
                    0,
                    i - self.swing_lookback
                )

                swing_price = lows[
                    swing_index
                ]

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

                # =================================================
                # EQUAL LOW FOUND
                # =================================================

                if matching_level is not None:

                    equal_low[i] = True

                    sell_side_liquidity[i] = True

                    active_liquidity = {
                        "price": matching_level,
                        "created_at": i
                    }

                    liquidity_level_low[i] = (
                        matching_level
                    )

                # -------------------------------------------------
                # Save newly confirmed swing.
                # -------------------------------------------------

                previous_lows.append(
                    (
                        i,
                        swing_price
                    )
                )

            # =================================================
            # PROPAGATE ACTIVE LIQUIDITY
            # =================================================

            if active_liquidity is not None:

                age = (
                    i
                    -
                    active_liquidity["created_at"]
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
                            active_liquidity["price"]
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
    # BUY-SIDE LIQUIDITY SWEEP
    # =========================================================

    def detect_buy_side_sweeps(
        self,
        df
    ):
        """
        Buy-side liquidity exists above highs.

        A bearish buy-side sweep occurs when:

            1. A liquidity level already exists.
            2. The current high trades ABOVE the level.
            3. The current candle closes BACK BELOW the level.

        The level must have existed BEFORE the current candle.
        """

        df = df.copy()

        highs = (
            df["high"]
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

        levels = (
            df[
                "liquidity_level_high"
            ]
            .to_numpy()
        )

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
            # A liquidity level becomes active.
            #
            # IMPORTANT:
            # We do not sweep it on the same candle.
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

            # -------------------------------------------------
            # Need an already-existing level.
            # -------------------------------------------------

            if (
                active_level is None
                or
                level_created_at is None
            ):

                continue

            # -------------------------------------------------
            # Never allow the creation candle to sweep itself.
            # -------------------------------------------------

            if i <= level_created_at:

                continue

            # -------------------------------------------------
            # Expire old liquidity.
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

            # =================================================
            # BUY-SIDE SWEEP
            # =================================================
            #
            # Price trades above liquidity and closes back
            # below it.
            # =================================================

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

                # -------------------------------------------------
                # Liquidity has been consumed.
                # -------------------------------------------------

                active_level = None

                level_created_at = None

        df[
            "buy_side_sweep"
        ] = sweeps

        return df

    # =========================================================
    # SELL-SIDE LIQUIDITY SWEEP
    # =========================================================

    def detect_sell_side_sweeps(
        self,
        df
    ):
        """
        Sell-side liquidity exists below lows.

        A bullish sell-side sweep occurs when:

            1. A liquidity level already exists.
            2. Current low trades BELOW the level.
            3. Current candle closes BACK ABOVE the level.

        The level must have existed BEFORE the current candle.
        """

        df = df.copy()

        lows = (
            df["low"]
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

        levels = (
            df[
                "liquidity_level_low"
            ]
            .to_numpy()
        )

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
            # Activate new liquidity.
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

            if (
                active_level is None
                or
                level_created_at is None
            ):

                continue

            # -------------------------------------------------
            # Do not allow same-candle sweep.
            # -------------------------------------------------

            if i <= level_created_at:

                continue

            # -------------------------------------------------
            # Expire old liquidity.
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

            # =================================================
            # SELL-SIDE SWEEP
            # =================================================
            #
            # Price trades below liquidity and closes back
            # above it.
            # =================================================

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

                # -------------------------------------------------
                # Liquidity has been consumed.
                # -------------------------------------------------

                active_level = None

                level_created_at = None

        df[
            "sell_side_sweep"
        ] = sweeps

        return df

    # =========================================================
    # COMPLETE LIQUIDITY ANALYSIS
    # =========================================================

    def analyze(
        self,
        df
    ):
        """
        Run the complete liquidity analysis.
        """

        df = self.add_columns(
            df
        )

        # -----------------------------------------------------
        # Equal highs / buy-side liquidity
        # -----------------------------------------------------

        df = self.find_equal_highs(
            df
        )

        # -----------------------------------------------------
        # Equal lows / sell-side liquidity
        # -----------------------------------------------------

        df = self.find_equal_lows(
            df
        )

        # -----------------------------------------------------
        # Detect buy-side sweeps
        # -----------------------------------------------------

        df = self.detect_buy_side_sweeps(
            df
        )

        # -----------------------------------------------------
        # Detect sell-side sweeps
        # -----------------------------------------------------

        df = self.detect_sell_side_sweeps(
            df
        )

        return df
