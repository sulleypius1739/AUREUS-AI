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
        # CONFIRMATIONS
        # -----------------------------------------------------

        df = self.confirmations.analyze(df)

        return df, bias

    # =========================================================
    # GET CURRENT STRUCTURAL BIAS
    # =========================================================

    def get_bias(self, df, index):

        if "structure_bias" in df.columns:

            bias = df.iloc[index].get(
                "structure_bias",
                "neutral"
            )

            if bias in [
                "bullish",
                "bearish"
            ]:

                return bias

        # -----------------------------------------------------
        # Fallback:
        #
        # Reconstruct the latest confirmed structure from the
        # information available up to this candle.
        # -----------------------------------------------------

        latest_high = None
        latest_low = None

        for i in range(index + 1):

            structure = df.iloc[i].get(
                "structure",
                None
            )

            if structure in ["HH", "LH"]:

                latest_high = structure

            elif structure in ["HL", "LL"]:

                latest_low = structure

        if (
            latest_high == "HH"
            and
            latest_low == "HL"
        ):

            return "bullish"

        if (
            latest_high == "LH"
            and
            latest_low == "LL"
        ):

            return "bearish"

        return "neutral"

    # =========================================================
    # SCORE CANDLE
    # =========================================================

    def score_candle(
        self,
        df,
        index
    ):

        row = df.iloc[index]

        # =====================================================
        # CURRENT STRUCTURAL BIAS
        # =====================================================

        bias = self.get_bias(
            df,
            index
        )

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

        if structure in [
            "HH",
            "HL"
        ]:

            bullish_score += 1

            bullish_reasons.append(
                "Bullish market structure"
            )

        elif structure in [
            "LH",
            "LL"
        ]:

            bearish_score += 1

            bearish_reasons.append(
                "Bearish market structure"
            )

        # =====================================================
        # LIQUIDITY SWEEP
        # =====================================================
        #
        # This is now the CORE trigger.
        #
        # BUY:
        #   sell-side liquidity must be swept.
        #
        # SELL:
        #   buy-side liquidity must be swept.
        #
        # A trade cannot be created without this.
        # =====================================================

        bullish_sweep = bool(
            row.get(
                "sell_side_sweep",
                False
            )
        )

        bearish_sweep = bool(
            row.get(
                "buy_side_sweep",
                False
            )
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
        # ORDER BLOCK
        # =====================================================

        bullish_ob = bool(
            row.get(
                "bullish_order_block",
                False
            )
        )

        bearish_ob = bool(
            row.get(
                "bearish_order_block",
                False
            )
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
        # FAIR VALUE GAP
        # =====================================================

        bullish_fvg = bool(
            row.get(
                "bullish_fvg",
                False
            )
        )

        bearish_fvg = bool(
            row.get(
                "bearish_fvg",
                False
            )
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
        # CANDLE CONFIRMATION
        # =====================================================

        bullish_engulfing = bool(
            row.get(
                "bullish_engulfing",
                False
            )
        )

        bearish_engulfing = bool(
            row.get(
                "bearish_engulfing",
                False
            )
        )

        bullish_rejection = bool(
            row.get(
                "bullish_rejection",
                False
            )
        )

        bearish_rejection = bool(
            row.get(
                "bearish_rejection",
                False
            )
        )

        if bullish_engulfing:

            bullish_score += 1

            bullish_reasons.append(
                "Bullish engulfing"
            )

        if bearish_engulfing:

            bearish_score += 1

            bearish_reasons.append(
                "Bearish engulfing"
            )

        if bullish_rejection:

            bullish_score += 1

            bullish_reasons.append(
                "Bullish rejection"
            )

        if bearish_rejection:

            bearish_score += 1

            bearish_reasons.append(
                "Bearish rejection"
            )

        # =====================================================
        # DISPLACEMENT
        # =====================================================

        displacement = bool(
            row.get(
                "displacement",
                False
            )
        )

        bullish_displacement = False
        bearish_displacement = False

        if displacement:

            if row["close"] > row["open"]:

                bullish_displacement = True

                bullish_score += 1

                bullish_reasons.append(
                    "Bullish displacement"
                )

            elif row["close"] < row["open"]:

                bearish_displacement = True

                bearish_score += 1

                bearish_reasons.append(
                    "Bearish displacement"
                )

        # =====================================================
        # CONTEXT SCORE
        # =====================================================
        #
        # A liquidity sweep alone is not enough.
        #
        # We want evidence that price actually reacted.
        #
        # Bullish context:
        #
        #   order block OR FVG OR engulfing OR rejection
        #   OR displacement
        #
        # Bearish context:
        #
        #   same idea in the opposite direction.
        # =====================================================

        bullish_context = (
            bullish_ob
            or
            bullish_fvg
            or
            bullish_engulfing
            or
            bullish_rejection
            or
            bullish_displacement
        )

        bearish_context = (
            bearish_ob
            or
            bearish_fvg
            or
            bearish_engulfing
            or
            bearish_rejection
            or
            bearish_displacement
        )

        # =====================================================
        # FINAL DECISION
        # =====================================================
        #
        # IMPORTANT:
        #
        # We no longer allow:
        #
        #   OB + engulfing + displacement
        #
        # to automatically create a trade.
        #
        # A liquidity event is mandatory.
        #
        # We also don't allow trades against structural bias.
        # =====================================================

        # -----------------------------------------------------
        # BULLISH SETUP
        # -----------------------------------------------------

        bullish_valid = (
            bias == "bullish"
            and
            bullish_sweep
            and
            bullish_context
            and
            bullish_score >= self.minimum_score
            and
            bullish_score > bearish_score
        )

        # -----------------------------------------------------
        # BEARISH SETUP
        # -----------------------------------------------------

        bearish_valid = (
            bias == "bearish"
            and
            bearish_sweep
            and
            bearish_context
            and
            bearish_score >= self.minimum_score
            and
            bearish_score > bullish_score
        )

        # =====================================================
        # BUY
        # =====================================================

        if bullish_valid:

            return {
                "signal": "BUY",
                "score": bullish_score,
                "reasons": bullish_reasons
            }

        # =====================================================
        # SELL
        # =====================================================

        if bearish_valid:

            return {
                "signal": "SELL",
                "score": bearish_score,
                "reasons": bearish_reasons
            }

        # =====================================================
        # WAIT
        # =====================================================

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

    def analyze(
        self,
        df
    ):

        df, bias = self.prepare(df)

        signals = []

        scores = []

        reasons = []

        for i in range(
            len(df)
        ):

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
