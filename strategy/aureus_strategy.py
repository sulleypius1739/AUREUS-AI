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
    # SCORE CANDLE
    # =========================================================

    def score_candle(self, df, index):

        row = df.iloc[index]

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

        if structure in ["HH", "HL"]:

            bullish_score += 1

            bullish_reasons.append(
                "Bullish market structure"
            )

        elif structure in ["LH", "LL"]:

            bearish_score += 1

            bearish_reasons.append(
                "Bearish market structure"
            )

        # =====================================================
        # LIQUIDITY SWEEP
        # =====================================================

        if row.get(
            "sell_side_sweep",
            False
        ):

            bullish_score += 2

            bullish_reasons.append(
                "Sell-side liquidity sweep"
            )

        if row.get(
            "buy_side_sweep",
            False
        ):

            bearish_score += 2

            bearish_reasons.append(
                "Buy-side liquidity sweep"
            )

        # =====================================================
        # ORDER BLOCK
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
        # FAIR VALUE GAP
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
        # CANDLE CONFIRMATION
        # =====================================================

        if row.get(
            "bullish_engulfing",
            False
        ):

            bullish_score += 1

            bullish_reasons.append(
                "Bullish engulfing"
            )

        if row.get(
            "bearish_engulfing",
            False
        ):

            bearish_score += 1

            bearish_reasons.append(
                "Bearish engulfing"
            )

        if row.get(
            "bullish_rejection",
            False
        ):

            bullish_score += 1

            bullish_reasons.append(
                "Bullish rejection"
            )

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

            if row["close"] > row["open"]:

                bullish_score += 1

                bullish_reasons.append(
                    "Bullish displacement"
                )

            elif row["close"] < row["open"]:

                bearish_score += 1

                bearish_reasons.append(
                    "Bearish displacement"
                )

        # =====================================================
        # FINAL DECISION
        # =====================================================

        if (
            bullish_score >= self.minimum_score
            and
            bullish_score > bearish_score
        ):

            return {
                "signal": "BUY",
                "score": bullish_score,
                "reasons": bullish_reasons
            }

        if (
            bearish_score >= self.minimum_score
            and
            bearish_score > bullish_score
        ):

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
