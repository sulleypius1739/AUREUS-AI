import numpy as np
import pandas as pd


class ZoneAnalyzer:
    """
    AUREUS Zone Analyzer

    Detects:

        - Support
        - Resistance
        - Demand
        - Supply
        - Bullish order blocks
        - Bearish order blocks
        - Bullish fair value gaps
        - Bearish fair value gaps
        - Bullish / bearish displacement

    IMPORTANT
    =========
    Every event must be knowable at the candle on which it is
    stored.

    No feature in this class may depend on an unfinished future
    candle.
    """

    def __init__(
        self,
        fvg_min_size=0.00005,
        displacement_multiplier=1.5,
        support_lookback=3
    ):

        self.fvg_min_size = float(
            fvg_min_size
        )

        self.displacement_multiplier = float(
            displacement_multiplier
        )

        self.support_lookback = int(
            support_lookback
        )

        if self.support_lookback < 1:
            raise ValueError(
                "support_lookback must be >= 1"
            )

    # =========================================================
    # ADD REQUIRED COLUMNS
    # =========================================================

    def add_columns(self, df):

        df = df.copy()

        boolean_columns = [
            "support",
            "resistance",
            "demand",
            "supply",
            "bullish_order_block",
            "bearish_order_block",
            "bullish_fvg",
            "bearish_fvg",
            "bullish_displacement",
            "bearish_displacement",
            "displacement"
        ]

        for column in boolean_columns:

            if column not in df.columns:
                df[column] = False

        return df

    # =========================================================
    # SUPPORT / RESISTANCE
    # =========================================================
    #
    # IMPORTANT:
    #
    # We cannot use:
    #
    #     low[i] < low[i+1]
    #
    # while making a decision at candle i.
    #
    # Instead, use confirmed swing information from
    # MarketStructure where available.
    # =========================================================

    def detect_support_resistance(self, df):

        df = df.copy()

        length = len(df)

        support = np.zeros(
            length,
            dtype=bool
        )

        resistance = np.zeros(
            length,
            dtype=bool
        )

        # -----------------------------------------------------
        # Preferred source: confirmed market structure.
        # -----------------------------------------------------

        if (
            "confirmed_swing_low"
            in df.columns
        ):

            support = (
                df[
                    "confirmed_swing_low"
                ]
                .to_numpy(
                    dtype=bool
                )
            )

        elif (
            "swing_low_confirmed"
            in df.columns
        ):

            support = (
                df[
                    "swing_low_confirmed"
                ]
                .to_numpy(
                    dtype=bool
                )
            )

        else:

            # -------------------------------------------------
            # Causal fallback.
            #
            # A local low is only marked after the required
            # candles to its right have completed.
            # -------------------------------------------------

            n = self.support_lookback

            lows = df[
                "low"
            ].to_numpy(
                dtype=float
            )

            for i in range(
                n,
                length - n
            ):

                candidate = lows[i]

                if (
                    candidate
                    <
                    lows[i - n:i].min()
                    and
                    candidate
                    <
                    lows[i + 1:i + n + 1].min()
                ):

                    confirmation_index = (
                        i + n
                    )

                    if confirmation_index < length:

                        support[
                            confirmation_index
                        ] = True

        # -----------------------------------------------------
        # Resistance
        # -----------------------------------------------------

        if (
            "confirmed_swing_high"
            in df.columns
        ):

            resistance = (
                df[
                    "confirmed_swing_high"
                ]
                .to_numpy(
                    dtype=bool
                )
            )

        elif (
            "swing_high_confirmed"
            in df.columns
        ):

            resistance = (
                df[
                    "swing_high_confirmed"
                ]
                .to_numpy(
                    dtype=bool
                )
            )

        else:

            n = self.support_lookback

            highs = df[
                "high"
            ].to_numpy(
                dtype=float
            )

            for i in range(
                n,
                length - n
            ):

                candidate = highs[i]

                if (
                    candidate
                    >
                    highs[i - n:i].max()
                    and
                    candidate
                    >
                    highs[i + 1:i + n + 1].max()
                ):

                    confirmation_index = (
                        i + n
                    )

                    if confirmation_index < length:

                        resistance[
                            confirmation_index
                        ] = True

        df[
            "support"
        ] = support

        df[
            "resistance"
        ] = resistance

        return df

    # =========================================================
    # DISPLACEMENT
    # =========================================================
    #
    # A displacement candle needs:
    #
    #     unusually large range
    #     +
    #     meaningful directional body
    #
    # Everything is calculated using the current candle and
    # previously available candles only.
    # =========================================================

    def detect_displacement(self, df):

        df = df.copy()

        opens = df[
            "open"
        ].to_numpy(
            dtype=float
        )

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

        closes = df[
            "close"
        ].to_numpy(
            dtype=float
        )

        length = len(df)

        bullish_displacement = np.zeros(
            length,
            dtype=bool
        )

        bearish_displacement = np.zeros(
            length,
            dtype=bool
        )

        displacement = np.zeros(
            length,
            dtype=bool
        )

        ranges = highs - lows

        for i in range(
            1,
            length
        ):

            previous_range = (
                ranges[i - 1]
            )

            current_range = (
                ranges[i]
            )

            if (
                previous_range <= 0
                or
                current_range <= 0
            ):

                continue

            body = abs(
                closes[i]
                -
                opens[i]
            )

            body_ratio = (
                body
                /
                current_range
            )

            # -------------------------------------------------
            # Require a meaningful body rather than a candle
            # with a huge wick and tiny body.
            # -------------------------------------------------

            if (
                current_range
                >=
                previous_range
                *
                self.displacement_multiplier
                and
                body_ratio >= 0.50
            ):

                displacement[i] = True

                if (
                    closes[i]
                    >
                    opens[i]
                ):

                    bullish_displacement[i] = True

                elif (
                    closes[i]
                    <
                    opens[i]
                ):

                    bearish_displacement[i] = True

        df[
            "bullish_displacement"
        ] = bullish_displacement

        df[
            "bearish_displacement"
        ] = bearish_displacement

        df[
            "displacement"
        ] = displacement

        return df

    # =========================================================
    # ORDER BLOCKS
    # =========================================================
    #
    # A bullish OB is the LAST bearish candle immediately before
    # a confirmed bullish displacement candle.
    #
    # A bearish OB is the LAST bullish candle immediately before
    # a confirmed bearish displacement candle.
    #
    # The OB becomes available on the displacement candle,
    # NOT before it.
    # =========================================================

    def detect_order_blocks(self, df):

        df = df.copy()

        opens = df[
            "open"
        ].to_numpy(
            dtype=float
        )

        closes = df[
            "close"
        ].to_numpy(
            dtype=float
        )

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

        length = len(df)

        bullish = closes > opens
        bearish = closes < opens

        bullish_order_block = np.zeros(
            length,
            dtype=bool
        )

        bearish_order_block = np.zeros(
            length,
            dtype=bool
        )

        # -----------------------------------------------------
        # Use our causal displacement columns if available.
        # -----------------------------------------------------

        if (
            "bullish_displacement"
            in df.columns
        ):

            bullish_disp = (
                df[
                    "bullish_displacement"
                ]
                .to_numpy(
                    dtype=bool
                )
            )

        else:

            bullish_disp = np.zeros(
                length,
                dtype=bool
            )

        if (
            "bearish_displacement"
            in df.columns
        ):

            bearish_disp = (
                df[
                    "bearish_displacement"
                ]
                .to_numpy(
                    dtype=bool
                )

        else:

            bearish_disp = np.zeros(
                length,
                dtype=bool
            )

        for i in range(
            1,
            length
        ):

            previous = i - 1

            # -------------------------------------------------
            # Bullish order block
            # -------------------------------------------------

            if (
                bullish_disp[i]
                and
                bearish[previous]
                and
                closes[i]
                >
                highs[previous]
            ):

                bullish_order_block[
                    previous
                ] = True

            # -------------------------------------------------
            # Bearish order block
            # -------------------------------------------------

            if (
                bearish_disp[i]
                and
                bullish[previous]
                and
                closes[i]
                <
                lows[previous]
            ):

                bearish_order_block[
                    previous
                ] = True

        # -----------------------------------------------------
        # IMPORTANT:
        #
        # The order block itself occurred on the previous
        # candle, but becomes KNOWABLE only on candle i.
        #
        # Therefore the original zone candle is useful for
        # plotting, but downstream trading logic must know when
        # it became available.
        #
        # We preserve the causal event column below.
        # -----------------------------------------------------

        bullish_ob_available = np.zeros(
            length,
            dtype=bool
        )

        bearish_ob_available = np.zeros(
            length,
            dtype=bool
        )

        for i in range(
            1,
            length
        ):

            if bullish_order_block[
                i - 1
            ]:

                bullish_ob_available[i] = True

            if bearish_order_block[
                i - 1
            ]:

                bearish_ob_available[i] = True

        df[
            "bullish_order_block"
        ] = bullish_order_block

        df[
            "bearish_order_block"
        ] = bearish_order_block

        df[
            "bullish_order_block_available"
        ] = bullish_ob_available

        df[
            "bearish_order_block_available"
        ] = bearish_ob_available

        return df

    # =========================================================
    # FAIR VALUE GAPS
    # =========================================================
    #
    # Bullish FVG:
    #
    #     low[i] > high[i-2]
    #
    # Bearish FVG:
    #
    #     high[i] < low[i-2]
    #
    # The FVG is known only AFTER candle i closes.
    #
    # Zero-size gaps do not qualify.
    # =========================================================

    def detect_fvg(self, df):

        df = df.copy()

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

        length = len(df)

        bullish_fvg = np.zeros(
            length,
            dtype=bool
        )

        bearish_fvg = np.zeros(
            length,
            dtype=bool
        )

        bullish_fvg_size = np.zeros(
            length,
            dtype=float
        )

        bearish_fvg_size = np.zeros(
            length,
            dtype=float
        )

        for i in range(
            2,
            length
        ):

            bullish_gap = (
                lows[i]
                -
                highs[i - 2]
            )

            bearish_gap = (
                lows[i - 2]
                -
                highs[i]
            )

            if (
                bullish_gap
                >
                self.fvg_min_size
            ):

                bullish_fvg[i] = True

                bullish_fvg_size[i] = (
                    bullish_gap
                )

            if (
                bearish_gap
                >
                self.fvg_min_size
            ):

                bearish_fvg[i] = True

                bearish_fvg_size[i] = (
                    bearish_gap
                )

        df[
            "bullish_fvg"
        ] = bullish_fvg

        df[
            "bearish_fvg"
        ] = bearish_fvg

        df[
            "bullish_fvg_size"
        ] = bullish_fvg_size

        df[
            "bearish_fvg_size"
        ] = bearish_fvg_size

        return df

    # =========================================================
    # SUPPLY / DEMAND
    # =========================================================
    #
    # We DO NOT define every candle colour change as a zone.
    #
    # Instead:
    #
    # bullish displacement
    #     +
    # prior bearish candle
    #     -> demand
    #
    # bearish displacement
    #     +
    # prior bullish candle
    #     -> supply
    #
    # The zone is therefore connected to meaningful directional
    # expansion.
    # =========================================================

    def detect_supply_demand(self, df):

        df = df.copy()

        opens = df[
            "open"
        ].to_numpy(
            dtype=float
        )

        closes = df[
            "close"
        ].to_numpy(
            dtype=float
        )

        length = len(df)

        bullish = closes > opens
        bearish = closes < opens

        demand = np.zeros(
            length,
            dtype=bool
        )

        supply = np.zeros(
            length,
            dtype=bool
        )

        bullish_disp = df[
            "bullish_displacement"
        ].to_numpy(
            dtype=bool
        )

        bearish_disp = df[
            "bearish_displacement"
        ].to_numpy(
            dtype=bool
        )

        # -----------------------------------------------------
        # Demand
        #
        # The prior bearish candle becomes demand after the
        # current bullish displacement confirms the move.
        # -----------------------------------------------------

        for i in range(
            1,
            length
        ):

            previous = i - 1

            if (
                bullish_disp[i]
                and
                bearish[previous]
            ):

                demand[
                    previous
                ] = True

            if (
                bearish_disp[i]
                and
                bullish[previous]
            ):

                supply[
                    previous
                ] = True

        demand_available = np.zeros(
            length,
            dtype=bool
        )

        supply_available = np.zeros(
            length,
            dtype=bool
        )

        for i in range(
            1,
            length
        ):

            if demand[i - 1]:

                demand_available[i] = True

            if supply[i - 1]:

                supply_available[i] = True

        df[
            "demand"
        ] = demand

        df[
            "supply"
        ] = supply

        df[
            "demand_available"
        ] = demand_available

        df[
            "supply_available"
        ] = supply_available

        return df

    # =========================================================
    # COMPLETE ANALYSIS
    # =========================================================

    def analyze(self, df):

        df = df.copy()

        required = [
            "open",
            "high",
            "low",
            "close"
        ]

        missing = [
            column
            for column in required
            if column not in df.columns
        ]

        if missing:

            raise ValueError(
                "Missing required zone columns: "
                +
                ", ".join(missing)
            )

        df = self.add_columns(
            df
        )

        # -----------------------------------------------------
        # Displacement first.
        # OB and supply/demand depend on it.
        # -----------------------------------------------------

        df = self.detect_displacement(
            df
        )

        # -----------------------------------------------------
        # Structure-derived support/resistance.
        # -----------------------------------------------------

        df = self.detect_support_resistance(
            df
        )

        # -----------------------------------------------------
        # Order blocks.
        # -----------------------------------------------------

        df = self.detect_order_blocks(
            df
        )

        # -----------------------------------------------------
        # FVG.
        # -----------------------------------------------------

        df = self.detect_fvg(
            df
        )

        # -----------------------------------------------------
        # Supply / demand.
        # -----------------------------------------------------

        df = self.detect_supply_demand(
            df
        )

        return df
