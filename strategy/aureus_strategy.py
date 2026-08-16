from strategy.market_structure import MarketStructure
from strategy.liquidity import LiquidityAnalyzer
from strategy.zones import ZoneAnalyzer
from strategy.confirmations import ConfirmationAnalyzer
from strategy.risk_management import RiskManager


class AureusStrategy:
    """
    AUREUS AI core strategy.

    The strategy is built around:

        1. Market structure
        2. Liquidity
        3. Price zones
        4. Candle confirmation
        5. Confluence scoring

    IMPORTANT:
    The individual analyzers are responsible for creating
    their respective features. This class combines those
    features into a trading decision.
    """

    def __init__(
        self,
        minimum_score=3,
        risk_percent=1.0,
        minimum_rr=2.0
    ):

        self.minimum_score = minimum_score

        self.market_structure = MarketStructure()

        self.liquidity = LiquidityAnalyzer()

        self.zones = ZoneAnalyzer()

        self.confirmations = ConfirmationAnalyzer()

        self.risk = RiskManager(
            risk_percent=risk_percent,
            minimum_rr=minimum_rr
        )

    # =========================================================
    # PREPARE MARKET
    # =========================================================

    def prepare(self, df):

        df = df.copy()

        # -----------------------------------------------------
        # Basic validation
        # -----------------------------------------------------

        required_columns = [
            "open",
            "high",
            "low",
            "close"
        ]

        missing_columns = [
            column
            for column in required_columns
            if column not in df.columns
        ]

        if missing_columns:

            raise ValueError(
                "Missing required market columns: "
                + ", ".join(missing_columns)
            )

        # -----------------------------------------------------
        # Ensure numerical OHLC data
        # -----------------------------------------------------

        for column in required_columns:

            df[column] = (
                df[column]
                .astype(float)
            )

        # -----------------------------------------------------
        # Remove invalid OHLC rows
        # -----------------------------------------------------

        df = df.dropna(
            subset=required_columns
        ).copy()

        # -----------------------------------------------------
        # MARKET STRUCTURE
        # -----------------------------------------------------

        df, bias = (
            self.market_structure.analyze(df)
        )

        # -----------------------------------------------------
        # LIQUIDITY
        # -----------------------------------------------------

        df = self.liquidity.analyze(
            df
        )

        # -----------------------------------------------------
        # ZONES
        # -----------------------------------------------------

        df = self.zones.analyze(
            df
        )

        # -----------------------------------------------------
        # CANDLE CONFIRMATION
        # -----------------------------------------------------

        df = self.confirmations.analyze(
            df
        )

        return df, bias

    # =========================================================
    # UTILITY
    # =========================================================

    @staticmethod
    def _is_true(row, column):

        value = row.get(
            column,
            False
        )

        if value is None:

            return False

        try:

            return bool(value)

        except Exception:

            return False

    # =========================================================
    # SCORE CURRENT CANDLE
    # =========================================================

    def score_candle(
        self,
        row,
        bias=None
    ):
        """
        Determine whether the current candle contains a
        valid AUREUS setup.

        Scoring hierarchy:

        PRIMARY CONDITIONS
        ------------------
        Liquidity sweep      = 2 points

        SECONDARY CONDITIONS
        --------------------
        Order block          = 1 point
        Fair value gap       = 1 point
        Candle confirmation  = 1 point
        Displacement         = 1 point

        A trade requires the minimum score AND directional
        agreement.

        Market structure bias can be supplied as:

            bullish
            bearish
            neutral
        """

        bullish_score = 0
        bearish_score = 0

        bullish_reasons = []
        bearish_reasons = []

        # =====================================================
        # 1. LIQUIDITY
        # =====================================================

        bullish_sweep = self._is_true(
            row,
            "sell_side_sweep"
        )

        bearish_sweep = self._is_true(
            row,
            "buy_side_sweep"
        )

        if bullish_sweep:

            bullish_score += 2

            bullish_reasons.append(
                "Sell-side liquidity sweep"
            )

        if bearish_sweep:

            bearish_score += 2

            bearish_reasons.append(
                "Buy-side liquidity sweep"
            )

        # =====================================================
        # 2. ORDER BLOCK
        # =====================================================

        bullish_ob = self._is_true(
            row,
            "bullish_order_block"
        )

        bearish_ob = self._is_true(
            row,
            "bearish_order_block"
        )

        if bullish_ob:

            bullish_score += 1

            bullish_reasons.append(
                "Bullish order block"
            )

        if bearish_ob:

            bearish_score += 1

            bearish_reasons.append(
                "Bearish order block"
            )

        # =====================================================
        # 3. FAIR VALUE GAP
        # =====================================================

        bullish_fvg = self._is_true(
            row,
            "bullish_fvg"
        )

        bearish_fvg = self._is_true(
            row,
            "bearish_fvg"
        )

        if bullish_fvg:

            bullish_score += 1

            bullish_reasons.append(
                "Bullish fair value gap"
            )

        if bearish_fvg:

            bearish_score += 1

            bearish_reasons.append(
                "Bearish fair value gap"
            )

        # =====================================================
        # 4. CANDLE CONFIRMATION
        # =====================================================

        bullish_engulfing = self._is_true(
            row,
            "bullish_engulfing"
        )

        bearish_engulfing = self._is_true(
            row,
            "bearish_engulfing"
        )

        bullish_rejection = self._is_true(
            row,
            "bullish_rejection"
        )

        bearish_rejection = self._is_true(
            row,
            "bearish_rejection"
        )

        # -----------------------------------------------------
        # Bullish candle confirmation
        # -----------------------------------------------------

        if bullish_engulfing:

            bullish_score += 1

            bullish_reasons.append(
                "Bullish engulfing"
            )

        if bullish_rejection:

            bullish_score += 1

            bullish_reasons.append(
                "Bullish rejection"
            )

        # -----------------------------------------------------
        # Bearish candle confirmation
        # -----------------------------------------------------

        if bearish_engulfing:

            bearish_score += 1

            bearish_reasons.append(
                "Bearish engulfing"
            )

        if bearish_rejection:

            bearish_score += 1

            bearish_reasons.append(
                "Bearish rejection"
            )

        # =====================================================
        # 5. DISPLACEMENT
        # =====================================================

        displacement = self._is_true(
            row,
            "displacement"
        )

        if displacement:

            close = float(
                row["close"]
            )

            open_price = float(
                row["open"]
            )

            if close > open_price:

                bullish_score += 1

                bullish_reasons.append(
                    "Bullish displacement"
                )

            elif close < open_price:

                bearish_score += 1

                bearish_reasons.append(
                    "Bearish displacement"
                )

        # =====================================================
        # DETERMINE RAW DIRECTION
        # =====================================================

        bullish_candidate = (
            bullish_score >= self.minimum_score
            and
            bullish_score > bearish_score
        )

        bearish_candidate = (
            bearish_score >= self.minimum_score
            and
            bearish_score > bullish_score
        )

        # =====================================================
        # MARKET STRUCTURE FILTER
        # =====================================================
        #
        # IMPORTANT:
        #
        # We do not force a bias if the caller has not supplied
        # one. This keeps score_candle usable independently.
        #
        # If bias IS supplied:
        #
        # bullish bias → BUY setups preferred
        # bearish bias → SELL setups preferred
        #
        # Neutral → both directions remain possible.
        #
        # =====================================================

        if bias is not None:

            bias_text = str(
                bias
            ).lower()

            if (
                bias_text == "bullish"
                and
                bullish_candidate
            ):

                return {
                    "signal": "BUY",
                    "score": bullish_score,
                    "reasons": bullish_reasons
                }

            if (
                bias_text == "bearish"
                and
                bearish_candidate
            ):

                return {
                    "signal": "SELL",
                    "score": bearish_score,
                    "reasons": bearish_reasons
                }

            # -------------------------------------------------
            # If the setup conflicts with structure, WAIT.
            # -------------------------------------------------

            return {
                "signal": "WAIT",
                "score": max(
                    bullish_score,
                    bearish_score
                ),
                "reasons": (
                    bullish_reasons
                    +
                    bearish_reasons
                )
            }

        # =====================================================
        # NO STRUCTURAL FILTER SUPPLIED
        # =====================================================

        if bullish_candidate:

            return {
                "signal": "BUY",
                "score": bullish_score,
                "reasons": bullish_reasons
            }

        if bearish_candidate:

            return {
                "signal": "SELL",
                "score": bearish_score,
                "reasons": bearish_reasons
            }

        return {
            "signal": "WAIT",
            "score": max(
                bullish_score,
                bearish_score
            ),
            "reasons": (
                bullish_reasons
                +
                bearish_reasons
            )
        }

    # =========================================================
    # GENERATE SIGNAL
    # =========================================================

    def generate_signal(
        self,
        df,
        index,
        bias=None
    ):

        if index < 0 or index >= len(df):

            raise IndexError(
                "Signal index is outside the "
                "available dataframe."
            )

        row = df.iloc[index]

        return self.score_candle(
            row,
            bias=bias
        )

    # =========================================================
    # COMPLETE ANALYSIS
    # =========================================================

    def analyze(self, df):

        df, bias = self.prepare(
            df
        )

        signals = []
        scores = []
        reasons = []

        # -----------------------------------------------------
        # Generate signal for every available candle.
        #
        # NOTE:
        # The individual analyzers must not use future data.
        # We will audit that separately in their files.
        # -----------------------------------------------------

        for i in range(
            len(df)
        ):

            signal = self.generate_signal(
                df,
                i,
                bias=bias
            )

            signals.append(
                signal["signal"]
            )

            scores.append(
                signal["score"]
            )

            reasons.append(
                signal["reasons"]
            )

        # -----------------------------------------------------
        # Store strategy outputs
        # -----------------------------------------------------

        df["aureus_signal"] = signals

        df["aureus_score"] = scores

        df["aureus_reasons"] = reasons

        # -----------------------------------------------------
        # Store structural bias
        # -----------------------------------------------------

        df["aureus_bias"] = bias

        return df, bias
