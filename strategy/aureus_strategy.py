from strategy.market_structure import MarketStructure
from strategy.liquidity import LiquidityAnalyzer
from strategy.zones import ZoneAnalyzer
from strategy.confirmations import ConfirmationAnalyzer
from strategy.risk_management import RiskManager


class AureusStrategy:

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

    def prepare(self, df):

        df = df.copy()

        df, bias = self.market_structure.analyze(df)

        df = self.liquidity.analyze(df)

        df = self.zones.analyze(df)

        df = self.confirmations.analyze(df)

        return df, bias

    def score_candle(self, row):

        bullish_score = 0
        bearish_score = 0

        bullish_reasons = []
        bearish_reasons = []

        if row.get("sell_side_sweep", False):

            bullish_score += 2

            bullish_reasons.append(
                "Sell-side liquidity sweep"
            )

        if row.get("buy_side_sweep", False):

            bearish_score += 2

            bearish_reasons.append(
                "Buy-side liquidity sweep"
            )

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

        if row.get(
            "displacement",
            False
        ):

            close = row["close"]
            open_price = row["open"]

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
            "reasons": (
                bullish_reasons
                +
                bearish_reasons
            )
        }

    def generate_signal(
        self,
        df,
        index
    ):

        row = df.iloc[index]

        result = self.score_candle(row)

        return result

    def analyze(self, df):

        df, bias = self.prepare(df)

        signals = []

        for i in range(len(df)):

            signal = self.generate_signal(
                df,
                i
            )

            signals.append(
                signal["signal"]
            )

        df["aureus_signal"] = signals

        return df, bias
