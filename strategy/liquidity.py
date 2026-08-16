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

    Liquidity is based on CONFIRMED swing points.

    A liquidity level must exist BEFORE price can sweep it.

    This class is designed for walk-forward backtesting and
    therefore avoids using future candles for the trading
    decision itself.
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
                    "liquidity_level"
                    in column
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

        price1 = float(price1)
        price2 = float(price2)

        difference = abs(
            price1 - price2
        )

        reference = max(
            abs(price1),
            abs(price2),
            1e-12
        )

        relative_difference = (
            difference / reference
        )

        return (
            relative_difference
            <=
            self.equal_tolerance
        )

    # =========================================================
    # CONFIRMED SWINGS
    # =========================================================

    def _ensure_confirmed_swings(
        self,
        df
    ):

        df = df.copy()

        required = [
            "confirmed_swing_high",
            "confirmed_swing_low"
        ]

        if all(
            column in df.columns
            for column in required
        ):

            return df

        length = len(df)

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

        confirmed_high = np.zeros(
            length,
            dtype=bool
        )

        confirmed_low = np.zeros(
            length,
            dtype=bool
        )

        n = self.swing_lookback

        # -----------------------------------------------------
        # A swing at candle i is only CONFIRMED at i + n.
        #
        # Therefore the trading system cannot use the swing
        # before i + n.
        # -----------------------------------------------------

        for i in range(
            n,
            length - n
        ):

            swing_high = (
                highs[i]
                >
                highs[i - n:i].max()
                and
                highs[i]
                >
                highs[i + 1:i + n + 1].max()
            )

            swing_low = (
                lows[i]
                <
                lows[i - n:i].min()
                and
                lows[i]
                <
                lows[i + 1:i + n + 1].min()
            )

            confirmation_index = i + n

            if (
                swing_high
                and
                confirmation_index < length
            ):

                confirmed_high[
                    confirmation_index
                ] = True

            if (
                swing_low
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

        df = self._ensure_confirmed_swings(
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

        confirmed = (
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
        # Each stored item is:
        #
        # {
        #     confirmation_index,
        #     swing_index,
        #     price
        # }
        # -----------------------------------------------------

        previous_swings = []

        active_levels = []

        for i in range(length):

            # =================================================
            # EXPIRE OLD LIQUIDITY
            # =================================================

            active_levels = [
                level
                for level in active_levels
                if (
                    i
                    -
                    level["created_at"]
                    <=
                    self.liquidity_expiry
                )
            ]

            previous_swings = [
                swing
                for swing in previous_swings
                if (
                    i
                    -
                    swing["confirmation_index"]
                    <=
                    self.liquidity_expiry
                )
            ]

            # =================================================
            # NEW CONFIRMED SWING HIGH
            # =================================================

            if confirmed[i]:

                swing_index = max(
                    0,
                    i - self.swing_lookback
                )

                swing_price = highs[
                    swing_index
                ]

                matching_price = None

                for previous in reversed(
                    previous_swings
                ):

                    if (
                        i
                        -
                        previous[
                            "confirmation_index"
                        ]
                        <
                        self.minimum_separation
                    ):

                        continue

                    if self._prices_are_equal(
                        swing_price,
                        previous["price"]
                    ):

                        matching_price = (
                            swing_price
                            +
                            previous["price"]
                        ) / 2.0

                        break

                # =============================================
                # CREATE NEW BUY-SIDE LIQUIDITY
                # =============================================

                if matching_price is not None:

                    equal_high[i] = True

                    buy_side_liquidity[i] = True

                    active_levels.append(
                        {
                            "price": matching_price,
                            "created_at": i
                        }
                    )

                previous_swings.append(
                    {
                        "confirmation_index": i,
                        "swing_index": swing_index,
                        "price": swing_price
                    }
                )

            # =================================================
            # EXPOSE THE MOST RECENT ACTIVE LEVEL
            # =================================================

            if active_levels:

                liquidity_level_high[i] = (
                    active_levels[-1]["price"]
                )

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

        df = self._ensure_confirmed_swings(
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

        confirmed = (
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

        previous_swings = []

        active_levels = []

        for i in range(length):

            # =================================================
            # EXPIRE OLD LIQUIDITY
            # =================================================

            active_levels = [
                level
                for level in active_levels
                if (
                    i
                    -
                    level["created_at"]
                    <=
                    self.liquidity_expiry
                )
            ]

            previous_swings = [
                swing
                for swing in previous_swings
                if (
                    i
                    -
                    swing["confirmation_index"]
                    <=
                    self.liquidity_expiry
                )
            ]

            # =================================================
            # NEW CONFIRMED SWING LOW
            # =================================================

            if confirmed[i]:

                swing_index = max(
                    0,
                    i - self.swing_lookback
                )

                swing_price = lows[
                    swing_index
                ]

                matching_price = None

                for previous in reversed(
                    previous_swings
                ):

                    if (
                        i
                        -
                        previous[
                            "confirmation_index"
                        ]
                        <
                        self.minimum_separation
                    ):

                        continue

                    if self._prices_are_equal(
                        swing_price,
                        previous["price"]
                    ):

                        matching_price = (
                            swing_price
                            +
                            previous["price"]
                        ) / 2.0

                        break

                # =============================================
                # CREATE NEW SELL-SIDE LIQUIDITY
                # =============================================

                if matching_price is not None:

                    equal_low[i] = True

                    sell_side_liquidity[i] = True

                    active_levels.append(
                        {
                            "price": matching_price,
                            "created_at": i
                        }
                    )

                previous_swings.append(
                    {
                        "confirmation_index": i,
                        "swing_index": swing_index,
                        "price": swing_price
                    }
                )

            # =================================================
            # EXPOSE MOST RECENT ACTIVE LEVEL
            # =================================================

            if active_levels:

                liquidity_level_low[i] = (
                    active_levels[-1]["price"]
                )

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
    # BUY-SIDE SWEEP
    # =========================================================

    def detect_buy_side_sweeps(
        self,
        df
    ):

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

        active_levels = []

        for i in range(len(df)):

            # -------------------------------------------------
            # Add level only if it was established BEFORE the
            # current candle.
            # -------------------------------------------------

            if (
                i > 0
                and
                not pd.isna(
                    levels[i - 1]
                )
            ):

                level = float(
                    levels[i - 1]
                )

                if not any(
                    self._prices_are_equal(
                        level,
                        existing["price"]
                    )
                    for existing in active_levels
                ):

                    active_levels.append(
                        {
                            "price": level,
                            "created_at": i - 1
                        }
                    )

            # -------------------------------------------------
            # Remove expired levels.
            # -------------------------------------------------

            active_levels = [
                level
                for level in active_levels
                if (
                    i
                    -
                    level["created_at"]
                    <=
                    self.liquidity_expiry
                )
            ]

            # -------------------------------------------------
            # Check all active buy-side liquidity.
            # -------------------------------------------------

            swept_level = None

            for level in reversed(
                active_levels
            ):

                price = level["price"]

                if (
                    highs[i] > price
                    and
                    closes[i] < price
                ):

                    sweeps[i] = True

                    swept_level = level

                    break

            # -------------------------------------------------
            # Remove consumed liquidity.
            # -------------------------------------------------

            if swept_level is not None:

                active_levels.remove(
                    swept_level
                )

        df[
            "buy_side_sweep"
        ] = sweeps

        return df

    # =========================================================
    # SELL-SIDE SWEEP
    # =========================================================

    def detect_sell_side_sweeps(
        self,
        df
    ):

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

        active_levels = []

        for i in range(len(df)):

            # -------------------------------------------------
            # Only activate levels known BEFORE current candle.
            # -------------------------------------------------

            if (
                i > 0
                and
                not pd.isna(
                    levels[i - 1]
                )
            ):

                level = float(
                    levels[i - 1]
                )

                if not any(
                    self._prices_are_equal(
                        level,
                        existing["price"]
                    )
                    for existing in active_levels
                ):

                    active_levels.append(
                        {
                            "price": level,
                            "created_at": i - 1
                        }
                    )

            # -------------------------------------------------
            # Expire old liquidity.
            # -------------------------------------------------

            active_levels = [
                level
                for level in active_levels
                if (
                    i
                    -
                    level["created_at"]
                    <=
                    self.liquidity_expiry
                )
            ]

            # -------------------------------------------------
            # Check sell-side liquidity.
            # -------------------------------------------------

            swept_level = None

            for level in reversed(
                active_levels
            ):

                price = level["price"]

                if (
                    lows[i] < price
                    and
                    closes[i] > price
                ):

                    sweeps[i] = True

                    swept_level = level

                    break

            # -------------------------------------------------
            # Consumed liquidity cannot be swept again.
            # -------------------------------------------------

            if swept_level is not None:

                active_levels.remove(
                    swept_level
                )

        df[
            "sell_side_sweep"
        ] = sweeps

        return df

    # =========================================================
    # COMPLETE ANALYSIS
    # =========================================================

    def analyze(
        self,
        df
    ):

        df = self.add_columns(
            df
        )

        df = self._ensure_confirmed_swings(
            df
        )

        df = self.find_equal_highs(
            df
        )

        df = self.find_equal_lows(
            df
        )

        df = self.detect_buy_side_sweeps(
            df
        )

        df = self.detect_sell_side_sweeps(
            df
        )

        return df
