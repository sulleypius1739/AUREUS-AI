from strategy.market_structure import MarketStructure
from strategy.liquidity import LiquidityAnalyzer
from strategy.zones import ZoneAnalyzer
from strategy.confirmations import ConfirmationAnalyzer
from strategy.risk_management import RiskManager


class AureusStrategy:

    def __init__(
        self,
        minimum_score=4,
        risk_percent=1.0,
        minimum_rr=2.0
    ):

        self.minimum_score = minimum_score

        # =====================================================
        # AUREUS COMPONENTS
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

    def prepare(self, df):

        df = df.copy()

        # -----------------------------------------------------
        # MARKET STRUCTURE
        # -----------------------------------------------------
        #
        # This creates:
        #
        # swing_high
        # swing_low
        # confirmed_swing_high
        # confirmed_swing_low
        # structure
        # structure_bias
        #
        # IMPORTANT:
        # MarketStructure already handles confirmation delay.
        # Therefore we can safely use structure_bias for each
        # candle.
        # -----------------------------------------------------

        df, bias = self.market_structure.analyze(df)

        # -----------------------------------------------------
        # LIQUIDITY
        # -----------------------------------------------------

        df = self.liquidity.analyze(df)

        # -----------------------------------------------------
        # ZONES
        # -----------------------------------------------------

        df = self.zones.analyze(df)

        # -----------------------------------------------------
        # CANDLE CONFIRMATIONS
        # -----------------------------------------------------

        df = self.confirmations.analyze(df)

        return df, bias

    # =========================================================
    # GET CURRENT BIAS
    # =========================================================

    def get_bias(self, df, index):

        # -----------------------------------------------------
        # IMPORTANT PERFORMANCE FIX
        # -----------------------------------------------------
        #
        # DO NOT loop through the DataFrame here.
        #
        # MarketStructure already calculated a rolling
        # structure_bias column for every candle.
        #
        # We simply read the bias belonging to the current
        # candle.
        # -----------------------------------------------------

        if index < 0 or index >= len(df):

            return "neutral"

        bias = df.iloc[index]["structure_bias"]

        if bias in (
            "bullish",
            "bearish",
            "neutral"
        ):

            return bias

        return "neutral"

    # =========================================================
    # SCORE CANDLE
    # =========================================================

    def score_candle(self, df, index):

        # -----------------------------------------------------
        # Safety
        # -----------------------------------------------------

        if index < 0 or index >= len(df):

            return {
                "signal": "WAIT",
                "score": 0,
                "reasons": []
            }

        row = df.iloc[index]

        bullish_score = 0
        bearish_score = 0

        bullish_reasons = []
        bearish_reasons = []

        # =====================================================
        # MARKET STRUCTURAL BIAS
        # =====================================================
        #
        # We use the already calculated rolling bias.
        #
        # This is much better than recalculating it for every
        # candle.
        # =====================================================

        bias = row.get(
            "structure_bias",
            "neutral"
        )

        # -----------------------------------------------------
        # Bullish structural bias
        # -----------------------------------------------------

        if bias == "bullish":

            bullish_score += 1

            bullish_reasons.append(
                "Bullish market structure"
            )

        # -----------------------------------------------------
        # Bearish structural bias
        # -----------------------------------------------------

        elif bias == "bearish":

            bearish_score += 1

            bearish_reasons.append(
                "Bearish market structure"
            )

        # =====================================================
        # CURRENT STRUCTURE EVENT
        # =====================================================

        structure = row.get(
            "structure",
            None
        )

        if structure == "HH":

            bullish_score += 1

            bullish_reasons.append(
                "Higher high"
            )

        elif structure == "HL":

            bullish_score += 1

            bullish_reasons.append(
                "Higher low"
            )

        elif structure == "LH":

            bearish_score += 1

            bearish_reasons.append(
                "Lower high"
            )

        elif structure == "LL":

            bearish_score += 1

            bearish_reasons.append(
                "Lower low"
            )

        # =====================================================
        # LIQUIDITY SWEEPS
        # =====================================================

        # -----------------------------------------------------
        # Sell-side liquidity sweep
        #
        # Price takes lows and closes back above.
        #
        # This is bullish.
        # -----------------------------------------------------

        if row.get(
            "sell_side_sweep",
            False
        ):

            bullish_score += 2

            bullish_reasons.append(
                "Sell-side liquidity sweep"
            )

        # -----------------------------------------------------
        # Buy-side liquidity sweep
        #
        # Price takes highs and closes back below.
        #
        # This is bearish.
        # -----------------------------------------------------

        if row.get(
            "buy_side_sweep",
            False
        ):

            bearish_score += 2

            bearish_reasons.append(
                "Buy-side liquidity sweep"
            )

        # =====================================================
        # ORDER BLOCKS
        # =====================================================

        if row.get(
            "bullish_order_block",
            False
        ):

            bullish_score += 1

            bullish_reasons.append(
                "Bullish order block"
            )

        if row.get(
            "bearish_order_block",
            False
        ):

            bearish_score += 1

            bearish_reasons.append(
                "Bearish order block"
            )

        # =====================================================
        # FAIR VALUE GAPS
        # =====================================================

        if row.get(
            "bullish_fvg",
            False
        ):

            bullish_score += 1

            bullish_reasons.append(
                "Bullish fair value gap"
            )

        if row.get(
            "bearish_fvg",
            False
        ):

            bearish_score += 1

            bearish_reasons.append(
                "Bearish fair value gap"
            )

        # =====================================================
        # BULLISH ENGULFING
        # =====================================================

        if row.get(
            "bullish_engulfing",
            False
        ):

            bullish_score += 1

            bullish_reasons.append(
                "Bullish engulfing"
            )

        # =====================================================
        # BEARISH ENGULFING
        # =====================================================

        if row.get(
            "bearish_engulfing",
            False
        ):

            bearish_score += 1

            bearish_reasons.append(
                "Bearish engulfing"
            )

        # =====================================================
        # BULLISH REJECTION
        # =====================================================

        if row.get(
            "bullish_rejection",
            False
        ):

            bullish_score += 1

            bullish_reasons.append(
                "Bullish rejection"
            )

        # =====================================================
        # BEARISH REJECTION
        # =====================================================

        if row.get(
            "bearish_rejection",
            False
        ):

            bearish_score += 1

            bearish_reasons.append(
                "Bearish rejection"
            )

        # =====================================================
        # DISPLACEMENT
        # =====================================================

        if row.get(
            "displacement",
            False
        ):

            close = float(
                row["close"]
            )

            open_price = float(
                row["open"]
            )

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
        # STRUCTURAL BIAS FILTER
        # =====================================================
        #
        # This is important.
        #
        # AUREUS should not blindly take a BUY when the
        # structural bias is bearish, or a SELL when it is
        # bullish.
        #
        # We therefore use structure as a directional filter.
        # -----------------------------------------------------

        if bias == "bullish":

            bearish_score = 0
            bearish_reasons = []

        elif bias == "bearish":

            bullish_score = 0
            bullish_reasons = []

        # =====================================================
        # FINAL DECISION
        # =====================================================

        # -----------------------------------------------------
        # BUY
        # -----------------------------------------------------

        if (
            bias == "bullish"
            and
            bullish_score >= self.minimum_score
            and
            bullish_score > bearish_score
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
            bias == "bearish"
            and
            bearish_score >= self.minimum_score
            and
            bearish_score > bullish_score
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
            "reasons":
                bullish_reasons
                +
                bearish_reasons
        }

    # =========================================================
    # GENERATE SIGNAL
    # =========================================================

    def generate_signal(
        self,
        df,
        index
    ):

        if index < 1:

            return {
                "signal": "WAIT",
                "score": 0,
                "reasons": []
            }

        return self.score_candle(
            df,
            index
        )

    # =========================================================
    # COMPLETE ANALYSIS
    # =========================================================

    def analyze(self, df):

        df, bias = self.prepare(df)

        signals = []
        scores = []
        reasons = []

        # -----------------------------------------------------
        # Generate signals sequentially.
        #
        # This is O(n), rather than repeatedly recalculating
        # market structure.
        # -----------------------------------------------------

        for i in range(len(df)):

            result = self.generate_signal(
                df,
                i
            )

            signals.append(
                result["signal"]
            )

            scores.append(
                result["score"]
            )

            reasons.append(
                result["reasons"]
            )

        df["aureus_signal"] = signals

        df["aureus_score"] = scores

        df["aureus_reasons"] = reasons

        return df, bias
