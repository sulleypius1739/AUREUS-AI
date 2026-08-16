import numpy as np
import pandas as pd


class ZoneAnalyzer:
    """
    AUREUS Zone Analyzer

    Detects:

        - Confirmed support
        - Confirmed resistance
        - Demand
        - Supply
        - Bullish order blocks
        - Bearish order blocks
        - Bullish fair value gaps
        - Bearish fair value gaps
        - Displacement

    IMPORTANT
    ---------

    Every signal produced here is causal.

    A candle is never labelled using information from a candle
    that occurs AFTER the candle being analysed.

    This is essential for historical backtesting.
    """

    def __init__(
        self,
        swing_length=3,
        fvg_min_size=0.0,
        fvg_atr_fraction=0.10,
        displacement_atr_multiplier=1.5,
        zone_expiry=100
    ):

        self.swing_length = int(
            swing_length
        )

        self.fvg_min_size = float(
            fvg_min_size
        )

        self.fvg_atr_fraction = float(
            fvg_atr_fraction
        )

        self.displacement_atr_multiplier = float(
            displacement_atr_multiplier
        )

        self.zone_expiry = int(
            zone_expiry
        )

    # =========================================================
    # ADD REQUIRED COLUMNS
    # =========================================================

    def add_columns(
        self,
        df
    ):

        df = df.copy()

        columns = [

            "support",

            "resistance",

            "demand",

            "supply",

            "bullish_order_block",

            "bearish_order_block",

            "bullish_fvg",

            "bearish_fvg",

            "displacement",

            "bullish_fvg_level",

            "bearish_fvg_level",

            "bullish_order_block_high",

            "bullish_order_block_low",

            "bearish_order_block_high",

            "bearish_order_block_low"

        ]

        for column in columns:

            if column not in df.columns:

                if (
                    column.endswith("_level")
                    or
                    column.endswith("_high")
                    or
                    column.endswith("_low")
                ):

                    df[column] = np.nan

                else:

                    df[column] = False

        return df

    # =========================================================
    # ATR
    # =========================================================

    def calculate_atr(
        self,
        df,
        period=14
    ):
        """
        Causal ATR.

        Uses only current and previous candles.
        """

        high = (
            df["high"]
            .astype(float)
        )

        low = (
            df["low"]
            .astype(float)
        )

        close = (
            df["close"]
            .astype(float)
        )

        previous_close = (
            close.shift(1)
        )

        true_range = pd.concat(
            [
                high - low,

                (high - previous_close).abs(),

                (low - previous_close).abs()

            ],
            axis=1
        ).max(
            axis=1
        )

        atr = (
            true_range
            .rolling(
                period,
                min_periods=period
            )
            .mean()
        )

        return atr

    # =========================================================
    # CONFIRMED SUPPORT / RESISTANCE
    # =========================================================

    def detect_support_resistance(
        self,
        df
    ):
        """
        Detect swing support/resistance without look-ahead bias.

        A swing at candle i is only confirmed after
        swing_length candles have passed.

        Therefore the signal is placed on the CONFIRMATION
        candle, not on the original swing candle.
        """

        df = df.copy()

        length = len(df)

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

        support = np.zeros(
            length,
            dtype=bool
        )

        resistance = np.zeros(
            length,
            dtype=bool
        )

        # -----------------------------------------------------
        # We cannot confirm a swing until n candles AFTER it
        # have occurred.
        # -----------------------------------------------------

        for swing_index in range(
            n,
            length - n
        ):

            swing_high = highs[
                swing_index
            ]

            swing_low = lows[
                swing_index
            ]

            left_high = highs[
                swing_index - n:
                swing_index
            ]

            right_high = highs[
                swing_index + 1:
                swing_index + n + 1
            ]

            left_low = lows[
                swing_index - n:
                swing_index
            ]

            right_low = lows[
                swing_index + 1:
                swing_index + n + 1
            ]

            is_resistance = (
                swing_high
                >
                left_high.max()
                and
                swing_high
                >
                right_high.max()
            )

            is_support = (
                swing_low
                <
                left_low.min()
                and
                swing_low
                <
                right_low.min()
            )

            confirmation_index = (
                swing_index + n
            )

            if (
                is_resistance
                and
                confirmation_index < length
            ):

                resistance[
                    confirmation_index
                ] = True

            if (
                is_support
                and
                confirmation_index < length
            ):

                support[
                    confirmation_index
                ] = True

        df["support"] = support

        df["resistance"] = resistance

        return df

    # =========================================================
    # DEMAND / SUPPLY
    # =========================================================

    def detect_supply_demand(
        self,
        df
    ):
        """
        Detects simple displacement-based demand/supply.

        Demand:

            previous candle bearish
            +
            current candle bullish
            +
            current candle closes above previous high

        Supply:

            previous candle bullish
            +
            current candle bearish
            +
            current candle closes below previous low

        The signal is placed on the CURRENT candle.

        Therefore no future candle is required.
        """

        df = df.copy()

        length = len(df)

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

        demand = np.zeros(
            length,
            dtype=bool
        )

        supply = np.zeros(
            length,
            dtype=bool
        )

        if length >= 2:

            previous_bearish = (
                closes[:-1]
                <
                opens[:-1]
            )

            current_bullish = (
                closes[1:]
                >
                opens[1:]
            )

            bullish_break = (
                closes[1:]
                >
                highs[:-1]
            )

            demand[1:] = (
                previous_bearish
                &
                current_bullish
                &
                bullish_break
            )

            previous_bullish = (
                closes[:-1]
                >
                opens[:-1]
            )

            current_bearish = (
                closes[1:]
                <
                opens[1:]
            )

            bearish_break = (
                closes[1:]
                <
                lows[:-1]
            )

            supply[1:] = (
                previous_bullish
                &
                current_bearish
                &
                bearish_break
            )

        df["demand"] = demand

        df["supply"] = supply

        return df

    # =========================================================
    # ORDER BLOCKS
    # =========================================================

    def detect_order_blocks(
        self,
        df
    ):
        """
        Detect order blocks using the candle immediately before
        a confirmed displacement candle.

        IMPORTANT:

        The ORDER BLOCK EVENT is placed on the displacement
        candle.

        We do NOT put the flag on the previous candle because
        doing so would allow the backtest to see the future.

        Bullish OB:

            previous candle bearish
            +
            current candle bullish
            +
            current candle closes above previous high

        Bearish OB:

            previous candle bullish
            +
            current candle bearish
            +
            current candle closes below previous low
        """

        df = df.copy()

        length = len(df)

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

        bullish = (
            closes
            >
            opens
        )

        bearish = (
            closes
            <
            opens
        )

        bullish_order_block = np.zeros(
            length,
            dtype=bool
        )

        bearish_order_block = np.zeros(
            length,
            dtype=bool
        )

        bullish_ob_high = np.full(
            length,
            np.nan
        )

        bullish_ob_low = np.full(
            length,
            np.nan
        )

        bearish_ob_high = np.full(
            length,
            np.nan
        )

        bearish_ob_low = np.full(
            length,
            np.nan
        )

        if length >= 2:

            # =================================================
            # BULLISH ORDER BLOCK
            # =================================================

            bullish_condition = (
                bearish[:-1]
                &
                bullish[1:]
                &
                (
                    closes[1:]
                    >
                    highs[:-1]
                )
            )

            bullish_order_block[1:] = (
                bullish_condition
            )

            bullish_ob_high[1:] = np.where(
                bullish_condition,
                highs[:-1],
                np.nan
            )

            bullish_ob_low[1:] = np.where(
                bullish_condition,
                lows[:-1],
                np.nan
            )

            # =================================================
            # BEARISH ORDER BLOCK
            # =================================================

            bearish_condition = (
                bullish[:-1]
                &
                bearish[1:]
                &
                (
                    closes[1:]
                    <
                    lows[:-1]
                )
            )

            bearish_order_block[1:] = (
                bearish_condition
            )

            bearish_ob_high[1:] = np.where(
                bearish_condition,
                highs[:-1],
                np.nan
            )

            bearish_ob_low[1:] = np.where(
                bearish_condition,
                lows[:-1],
                np.nan
            )

        df[
            "bullish_order_block"
        ] = bullish_order_block

        df[
            "bearish_order_block"
        ] = bearish_order_block

        df[
            "bullish_order_block_high"
        ] = bullish_ob_high

        df[
            "bullish_order_block_low"
        ] = bullish_ob_low

        df[
            "bearish_order_block_high"
        ] = bearish_ob_high

        df[
            "bearish_order_block_low"
        ] = bearish_ob_low

        return df

    # =========================================================
    # FAIR VALUE GAPS
    # =========================================================

    def detect_fvg(
        self,
        df
    ):
        """
        Three-candle Fair Value Gap.

        Bullish FVG:

            current low > high two candles ago

        Bearish FVG:

            current high < low two candles ago

        The FVG is only known once the current candle closes.

        A minimum ATR-relative gap is used so tiny numerical
        differences are not treated as meaningful FVGs.
        """

        df = df.copy()

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

        atr = (
            self.calculate_atr(
                df
            )
            .to_numpy()
        )

        bullish_fvg = np.zeros(
            length,
            dtype=bool
        )

        bearish_fvg = np.zeros(
            length,
            dtype=bool
        )

        bullish_fvg_level = np.full(
            length,
            np.nan
        )

        bearish_fvg_level = np.full(
            length,
            np.nan
        )

        if length >= 3:

            # =================================================
            # BULLISH FVG
            # =================================================

            bullish_gap = (
                lows[2:]
                -
                highs[:-2]
            )

            required_gap = np.maximum(
                self.fvg_min_size,
                np.nan_to_num(
                    atr[2:],
                    nan=0.0
                )
                *
                self.fvg_atr_fraction
            )

            bullish_condition = (
                bullish_gap
                >=
                required_gap
            )

            bullish_fvg[2:] = (
                bullish_condition
            )

            bullish_fvg_level[2:] = np.where(
                bullish_condition,
                highs[:-2],
                np.nan
            )

            # =================================================
            # BEARISH FVG
            # =================================================

            bearish_gap = (
                lows[:-2]
                -
                highs[2:]
            )

            bearish_condition = (
                bearish_gap
                >=
                required_gap
            )

            bearish_fvg[2:] = (
                bearish_condition
            )

            bearish_fvg_level[2:] = np.where(
                bearish_condition,
                lows[:-2],
                np.nan
            )

        df[
            "bullish_fvg"
        ] = bullish_fvg

        df[
            "bearish_fvg"
        ] = bearish_fvg

        df[
            "bullish_fvg_level"
        ] = bullish_fvg_level

        df[
            "bearish_fvg_level"
        ] = bearish_fvg_level

        return df

    # =========================================================
    # DISPLACEMENT
    # =========================================================

    def detect_displacement(
        self,
        df
    ):
        """
        Detect meaningful displacement.

        The old version compared only:

            current range >= previous range * 1.5

        That can classify a candle as displacement simply because
        the previous candle happened to be unusually small.

        We instead compare current range with a rolling ATR.

        This produces a much more stable definition.
        """

        df = df.copy()

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

        candle_range = (
            highs
            -
            lows
        )

        body = np.abs(
            closes
            -
            opens
        )

        atr = (
            self.calculate_atr(
                df
            )
            .to_numpy()
        )

        displacement = np.zeros(
            len(df),
            dtype=bool
        )

        valid_atr = (
            np.isfinite(atr)
            &
            (atr > 0)
        )

        large_range = (
            candle_range
            >=
            (
                atr
                *
                self.displacement_atr_multiplier
            )
        )

        # Require a meaningful body as well.
        #
        # This prevents a huge wick from automatically becoming
        # displacement.

        meaningful_body = (
            body
            >=
            candle_range * 0.50
        )

        displacement = (
            valid_atr
            &
            large_range
            &
            meaningful_body
        )

        df[
            "displacement"
        ] = displacement

        return df

    # =========================================================
    # COMPLETE ANALYSIS
    # =========================================================

    def analyze(
        self,
        df
    ):

        df = df.copy()

        # -----------------------------------------------------
        # Make sure data is ordered chronologically.
        # -----------------------------------------------------

        if "Date" in df.columns:

            dates = pd.to_datetime(
                df["Date"],
                errors="coerce"
            )

            df = (
                df.assign(
                    _parsed_date=dates
                )
                .sort_values(
                    "_parsed_date"
                )
                .drop(
                    columns="_parsed_date"
                )
                .reset_index(
                    drop=True
                )
            )

        # -----------------------------------------------------
        # Required columns
        # -----------------------------------------------------

        df = self.add_columns(
            df
        )

        # -----------------------------------------------------
        # ATR is used by FVG/displacement.
        # -----------------------------------------------------

        df = self.detect_support_resistance(
            df
        )

        df = self.detect_supply_demand(
            df
        )

        df = self.detect_order_blocks(
            df
        )

        df = self.detect_fvg(
            df
        )

        df = self.detect_displacement(
            df
        )

        return df
