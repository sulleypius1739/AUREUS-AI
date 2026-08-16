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

    A liquidity level must exist before price can sweep it.

    This prevents the backtest from using information that
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

    def add_columns(
        self,
        df
    ):

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
    # FIND EQUAL HIGHS
    # =========================================================

    def find_equal_highs(
        self,
        df
    ):
        """
        Detect equal highs using CONFIRMED swing highs.

        A new equal-high level is created when a newly confirmed
        swing high is sufficiently close to a previous confirmed
        swing high.

        We do NOT compare every candle against the previous
        three candles.

        This is important because normal market candles often
        have very similar highs.
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
        # We prefer confirmed swing highs.
        #
        # If the market structure analyzer has not been run,
        # fall back to calculating simple confirmed swings.
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

        # -----------------------------------------------------
        # Store previously confirmed swing highs.
        #
        # Each item:
        #
        # (confirmation_index, price)
        # -----------------------------------------------------

        previous_highs = []

        active_liquidity = None

        for i in range(length):

            # =================================================
            # NEW CONFIRMED SWING HIGH
            # =================================================

            if confirmed_highs[i]:

                swing_confirmation = i

                swing_index = max(
                    0,
                    i - self.swing_lookback
                )

                swing_price = highs[
                    swing_index
                ]

                # -------------------------------------------------
                # Remove very old reference swings.
                # -------------------------------------------------

                previous_highs = [
                    item
                    for item in previous_highs
                    if (
                        i - item[0]
                        <= self.liquidity_expiry
                    )
                ]

                matching_level = None

                # -------------------------------------------------
                # Look for a previous swing at approximately the
                # same price.
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

                # -------------------------------------------------
                # Equal high found.
                # -------------------------------------------------

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
                # Save this swing for future comparison.
                # -------------------------------------------------

                previous_highs.append(
                    (
                        i,
                        swing_price
                    )
                )

            # =================================================
            # PROPAGATE ACTIVE LIQUIDITY LEVEL
            # =================================================

            if active_liquidity is not None:

                if (
                    i
                    -
                    active_liquidity["created_at"]
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
        Detect equal lows using CONFIRMED swing lows.
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

        for i in range(length):

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

                previous_lows = [
                    item
                    for item in previous_lows
                    if (
                        i - item[0]
                        <= self.liquidity_expiry
                    )
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

                # -------------------------------------------------
                # Equal low found.
                # -------------------------------------------------

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

                if (
                    i
                    -
                    active_liquidity["created_at"]
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
    # FALLBACK SWING DETECTION
    # =========================================================

    def _create_fallback_swings(
        self,
        df
    ):
        """
        Fallback only.

        Normally MarketStructure should already have created
        confirmed_swing_high and confirmed_swing_low.
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
    # BUY-SIDE LIQUIDITY SWEEP
    # =========================================================

    def detect_buy_side_sweeps(
        self,
        df
    ):
        """
        Buy-side liquidity exists above highs.

        A bearish sweep occurs when:

            1. A liquidity level already exists.
            2. Current high trades above it.
            3. Current candle closes back below it.

        The liquidity level must have existed BEFORE the
        current candle.
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

        for i in range(
            len(df)
        ):

            current_level = levels[i]

            # -------------------------------------------------
            # Only activate a level if it existed before this
            # candle.
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
            # Need a previously established liquidity level.
            # -------------------------------------------------

            if (
                active_level is not None
                and
                level_created_at is not None
                and
                i > level_created_at
            ):

                expired = (
                    i
                    -
                    level_created_at
                    >
                    self.liquidity_expiry
                )

                if expired:

                    active_level = None

                    level_created_at = None

                    continue

                # -------------------------------------------------
                # Sweep:
                #
                # High takes the liquidity.
                # Close rejects back below it.
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

                    # ---------------------------------------------
                    # A swept level is consumed.
                    # ---------------------------------------------

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

        A bullish sweep occurs when:

            1. A liquidity level already exists.
            2. Current low trades below it.
            3. Current candle closes back above it.
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

        for i in range(
            len(df)
        ):

            current_level = levels[i]

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
                active_level is not None
                and
                level_created_at is not None
                and
                i > level_created_at
            ):

                expired = (
                    i
                    -
                    level_created_at
                    >
                    self.liquidity_expiry
                )

                if expired:

                    active_level = None

                    level_created_at = None

                    continue

                # -------------------------------------------------
                # Sweep:
                #
                # Low takes liquidity.
                # Close rejects back above it.
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

    def analyze(
        self,
        df
    ):

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
        # Detect sweeps
        # -----------------------------------------------------

        df = self.detect_buy_side_sweeps(
            df
        )

        df = self.detect_sell_side_sweeps(
            df
        )

        return df
