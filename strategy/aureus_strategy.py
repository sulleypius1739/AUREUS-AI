from strategy.market_structure import MarketStructure
from strategy.liquidity import LiquidityAnalyzer
from strategy.zones import ZoneAnalyzer
from strategy.confirmations import ConfirmationAnalyzer
from strategy.risk_management import RiskManager


class AureusStrategy:
    """
    AUREUS Trading Strategy

    Combines:

        1. Market structure
        2. Liquidity sweeps
        3. Order blocks
        4. Fair value gaps
        5. Candlestick confirmations
        6. Displacement

    The strategy produces:

        BUY
        SELL
        WAIT

    Important:
    The individual analyzers are responsible for creating
    information that is available at each candle.

    This class only combines that information into a signal.
    """

    def __init__(
        self,
        minimum_score=3,
        risk_percent=1.0,
        minimum_rr=2.0
    ):

        self.minimum_score = int(
            minimum_score
        )

        self.risk_percent = float(
            risk_percent
        )

        self.minimum_rr = float(
            minimum_rr
        )

        # =====================================================
        # ANALYZERS
        # =====================================================

        self.market_structure = MarketStructure(
            swing_length=3
        )

        self.liquidity = LiquidityAnalyzer(
            swing_lookback=5,
            equal_tolerance=0.0001
        )

        self.zones = ZoneAnalyzer(
            fvg_min_size=0.00005
        )

        self.confirmations = ConfirmationAnalyzer()

        self.risk = RiskManager(
            risk_percent=risk_percent,
            minimum_rr=minimum_rr
        )

    # =========================================================
    # PREPARE MARKET
    # =========================================================

    def prepare(
        self,
        df
    ):
        """
        Run all AUREUS analysis modules.

        Order matters:

            Market Structure
                    ↓
            Liquidity
                    ↓
            Zones
                    ↓
            Confirmations
        """

        df = df.copy()

        # -----------------------------------------------------
        # MARKET STRUCTURE
        # -----------------------------------------------------

        df, bias = (
            self.market_structure.analyze(
                df
            )
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
        # CANDLE CONFIRMATIONS
        # -----------------------------------------------------

        df = self.confirmations.analyze(
            df
        )

        return df, bias

    # =========================================================
    # SAFE BOOLEAN
    # =========================================================

    @staticmethod
    def _is_true(
        value
    ):
        """
        Safely convert analyzer values into booleans.

        Handles:

            True
            False
            numpy.bool_
            1
            0
            None
            NaN
        """

        if value is None:
            return False

        try:

            if value != value:
                return False

        except Exception:

            pass

        return bool(
            value
        )

    # =========================================================
    # SCORE CANDLE
    # =========================================================

    def score_candle(
        self,
        row
    ):
        """
        Score one candle.

        Scoring:

        MARKET STRUCTURE
            +1 bullish
            +1 bearish

        LIQUIDITY SWEEP
            +2 bullish
            +2 bearish

        ORDER BLOCK
            +1 bullish
            +1 bearish

        FAIR VALUE GAP
            +1 bullish
            +1 bearish

        CANDLE CONFIRMATION
            +1 bullish engulfing
            +1 bearish engulfing

            +1 bullish rejection
            +1 bearish rejection

        DISPLACEMENT
            +1 bullish
            +1 bearish

        A trade is allowed only when:

            score >= minimum_score

        and:

            bullish_score > bearish_score

        or:

            bearish_score > bullish_score
        """

        bullish_score = 0
        bearish_score = 0

        bullish_reasons = []
        bearish_reasons = []

        # =====================================================
        # MARKET STRUCTURE
        # =====================================================

        structure = row.get(
            "structure",
            None
        )

        structure_bias = row.get(
            "structure_bias",
            "neutral"
        )

        # -----------------------------------------------------
        # Bullish structure
        # -----------------------------------------------------

        if structure in (
            "HH",
            "HL"
        ):

            bullish_score += 1

            if structure == "HH":

                bullish_reasons.append(
                    "Higher high"
                )

            else:

                bullish_reasons.append(
                    "Higher low"
                )

        # -----------------------------------------------------
        # Bearish structure
        # -----------------------------------------------------

        elif structure in (
            "LH",
            "LL"
        ):

            bearish_score += 1

            if structure == "LH":

                bearish_reasons.append(
                    "Lower high"
                )

            else:

                bearish_reasons.append(
                    "Lower low"
                )

        # -----------------------------------------------------
        # Structural bias
        #
        # Bias is supporting context rather than another full
        # point. This prevents double-counting HH/HL and LH/LL.
        # -----------------------------------------------------

        if structure_bias == "bullish":

            bullish_reasons.insert(
                0,
                "Bullish market structure"
            )

        elif structure_bias == "bearish":

            bearish_reasons.insert(
                0,
                "Bearish market structure"
            )

        # =====================================================
        # SELL-SIDE LIQUIDITY SWEEP
        # =====================================================

        if self._is_true(
            row.get(
                "sell_side_sweep",
                False
            )
        ):

            bullish_score += 2

            bullish_reasons.append(
                "Sell-side liquidity sweep"
            )

        # =====================================================
        # BUY-SIDE LIQUIDITY SWEEP
        # =====================================================

        if self._is_true(
            row.get(
                "buy_side_sweep",
                False
            )
        ):

            bearish_score += 2

            bearish_reasons.append(
                "Buy-side liquidity sweep"
            )

        # =====================================================
        # BULLISH ORDER BLOCK
        # =====================================================

        if self._is_true(
            row.get(
                "bullish_order_block",
                False
            )
        ):

            bullish_score += 1

            bullish_reasons.append(
                "Bullish order block"
            )

        # =====================================================
        # BEARISH ORDER BLOCK
        # =====================================================

        if self._is_true(
            row.get(
                "bearish_order_block",
                False
            )
        ):

            bearish_score += 1

            bearish_reasons.append(
                "Bearish order block"
            )

        # =====================================================
        # BULLISH FAIR VALUE GAP
        # =====================================================

        if self._is_true(
            row.get(
                "bullish_fvg",
                False
            )
        ):

            bullish_score += 1

            bullish_reasons.append(
                "Bullish fair value gap"
            )

        # =====================================================
        # BEARISH FAIR VALUE GAP
        # =====================================================

        if self._is_true(
            row.get(
                "bearish_fvg",
                False
            )
        ):

            bearish_score += 1

            bearish_reasons.append(
                "Bearish fair value gap"
            )

        # =====================================================
        # BULLISH ENGULFING
        # =====================================================

        if self._is_true(
            row.get(
                "bullish_engulfing",
                False
            )
        ):

            bullish_score += 1

            bullish_reasons.append(
                "Bullish engulfing"
            )

        # =====================================================
        # BEARISH ENGULFING
        # =====================================================

        if self._is_true(
            row.get(
                "bearish_engulfing",
                False
            )
        ):

            bearish_score += 1

            bearish_reasons.append(
                "Bearish engulfing"
            )

        # =====================================================
        # BULLISH REJECTION
        # =====================================================

        if self._is_true(
            row.get(
                "bullish_rejection",
                False
            )
        ):

            bullish_score += 1

            bullish_reasons.append(
                "Bullish rejection"
            )

        # =====================================================
        # BEARISH REJECTION
        # =====================================================

        if self._is_true(
            row.get(
                "bearish_rejection",
                False
            )
        ):

            bearish_score += 1

            bearish_reasons.append(
                "Bearish rejection"
            )

        # =====================================================
        # DISPLACEMENT
        # =====================================================

        if self._is_true(
            row.get(
                "displacement",
                False
            )
        ):

            close = row.get(
                "close",
                None
            )

            open_price = row.get(
                "open",
                None
            )

            if (
                close is not None
                and
                open_price is not None
            ):

                # -------------------------------------------------
                # Bullish displacement
                # -------------------------------------------------

                if close > open_price:

                    bullish_score += 1

                    bullish_reasons.append(
                        "Bullish displacement"
                    )

                # -------------------------------------------------
                # Bearish displacement
                # -------------------------------------------------

                elif close < open_price:

                    bearish_score += 1

                    bearish_reasons.append(
                        "Bearish displacement"
                    )

        # =====================================================
        # DETERMINE FINAL SIGNAL
        # =====================================================

        # -----------------------------------------------------
        # BUY
        # -----------------------------------------------------

        if (
            bullish_score
            >=
            self.minimum_score
            and
            bullish_score
            >
            bearish_score
        ):

            return {
                "signal": "BUY",
                "score": bullish_score,
                "reasons": bullish_reasons
            }

        # -----------------------------------------------------
        # SELL
        # -----------------------------------------------------

        if (
            bearish_score
            >=
            self.minimum_score
            and
            bearish_score
            >
            bullish_score
        ):

            return {
                "signal": "SELL",
                "score": bearish_score,
                "reasons": bearish_reasons
            }

        # -----------------------------------------------------
        # WAIT
        # -----------------------------------------------------

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
        index
    ):
        """
        Generate a signal for exactly one candle.

        The existing BacktestEngine calls this method as:

            generate_signal(df, index)

        Therefore this interface must remain unchanged.
        """

        # -----------------------------------------------------
        # Invalid index
        # -----------------------------------------------------

        if (
            index < 0
            or
            index >= len(df)
        ):

            return {
                "signal": "WAIT",
                "score": 0,
                "reasons": []
            }

        # -----------------------------------------------------
        # First candle cannot provide useful confirmation.
        # -----------------------------------------------------

        if index < 1:

            return {
                "signal": "WAIT",
                "score": 0,
                "reasons": []
            }

        row = df.iloc[
            index
        ]

        return self.score_candle(
            row
        )

    # =========================================================
    # COMPLETE ANALYSIS
    # =========================================================

    def analyze(
        self,
        df
    ):
        """
        Run the complete AUREUS analysis and generate a signal
        for every candle.
        """

        df, bias = self.prepare(
            df
        )

        signals = []
        scores = []
        reasons = []

        # -----------------------------------------------------
        # Walk forward through the prepared data.
        # -----------------------------------------------------

        for i in range(
            len(df)
        ):

            signal = self.generate_signal(
                df,
                i
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
        # Store results.
        # -----------------------------------------------------

        df[
            "aureus_signal"
        ] = signals

        df[
            "aureus_score"
        ] = scores

        df[
            "aureus_reasons"
        ] = reasons

        return df, bias
