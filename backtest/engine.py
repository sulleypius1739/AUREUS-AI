import pandas as pd

from strategy.market_structure import MarketStructure
from strategy.liquidity import LiquidityAnalyzer
from strategy.zones import ZoneAnalyzer
from strategy.confirmations import ConfirmationAnalyzer
from strategy.risk_management import RiskManager


class BacktestEngine:

    def __init__(
        self,
        starting_balance=10000,
        risk_percent=1.0,
        minimum_rr=2.0
    ):

        self.starting_balance = starting_balance
        self.balance = starting_balance

        self.market_structure = MarketStructure()
        self.liquidity = LiquidityAnalyzer()
        self.zones = ZoneAnalyzer()
        self.confirmations = ConfirmationAnalyzer()

        self.risk = RiskManager(
            risk_percent=risk_percent,
            minimum_rr=minimum_rr
        )

        self.trades = []

    # =========================================================
    # PREPARE DATA
    # =========================================================

    def prepare_data(self, df):

        required = [
            "open",
            "high",
            "low",
            "close"
        ]

        for column in required:

            if column not in df.columns:

                raise ValueError(
                    f"Missing required column: {column}"
                )

        df = df.copy()

        df.columns = [
            str(column).lower().strip()
            for column in df.columns
        ]

        # Market structure
        df, bias = self.market_structure.analyze(df)

        # Liquidity
        df = self.liquidity.analyze(df)

        # Zones
        df = self.zones.analyze(df)

        # Candlestick confirmations
        df = self.confirmations.analyze(df)

        return df, bias

    # =========================================================
    # DETERMINE SIGNAL
    # =========================================================

    def get_signal(self, row):

        bullish_score = 0
        bearish_score = 0

        reasons = []

        # -----------------------------------------------------
        # BULLISH LIQUIDITY SWEEP
        # -----------------------------------------------------

        if row.get("sell_side_sweep", False):

            bullish_score += 2

            reasons.append(
                "Sell-side liquidity sweep"
            )

        # -----------------------------------------------------
        # BEARISH LIQUIDITY SWEEP
        # -----------------------------------------------------

        if row.get("buy_side_sweep", False):

            bearish_score += 2

            reasons.append(
                "Buy-side liquidity sweep"
            )

        # -----------------------------------------------------
        # BULLISH ORDER BLOCK
        # -----------------------------------------------------

        if row.get(
            "bullish_order_block",
            False
        ):

            bullish_score += 1

            reasons.append(
                "Bullish order block"
            )

        # -----------------------------------------------------
        # BEARISH ORDER BLOCK
        # -----------------------------------------------------

        if row.get(
            "bearish_order_block",
            False
        ):

            bearish_score += 1

            reasons.append(
                "Bearish order block"
            )

        # -----------------------------------------------------
        # BULLISH FVG
        # -----------------------------------------------------

        if row.get(
            "bullish_fvg",
            False
        ):

            bullish_score += 1

            reasons.append(
                "Bullish FVG"
            )

        # -----------------------------------------------------
        # BEARISH FVG
        # -----------------------------------------------------

        if row.get(
            "bearish_fvg",
            False
        ):

            bearish_score += 1

            reasons.append(
                "Bearish FVG"
            )

        # -----------------------------------------------------
        # BULLISH ENGULFING
        # -----------------------------------------------------

        if row.get(
            "bullish_engulfing",
            False
        ):

            bullish_score += 1

            reasons.append(
                "Bullish engulfing"
            )

        # -----------------------------------------------------
        # BEARISH ENGULFING
        # -----------------------------------------------------

        if row.get(
            "bearish_engulfing",
            False
        ):

            bearish_score += 1

            reasons.append(
                "Bearish engulfing"
            )

        # -----------------------------------------------------
        # BULLISH REJECTION
        # -----------------------------------------------------

        if row.get(
            "bullish_rejection",
            False
        ):

            bullish_score += 1

            reasons.append(
                "Bullish rejection"
            )

        # -----------------------------------------------------
        # BEARISH REJECTION
        # -----------------------------------------------------

        if row.get(
            "bearish_rejection",
            False
        ):

            bearish_score += 1

            reasons.append(
                "Bearish rejection"
            )

        # -----------------------------------------------------
        # FINAL SIGNAL
        # -----------------------------------------------------

        if (
            bullish_score >= 3
            and
            bullish_score > bearish_score
        ):

            return {
                "signal": "BUY",
                "score": bullish_score,
                "reasons": reasons
            }

        if (
            bearish_score >= 3
            and
            bearish_score > bullish_score
        ):

            return {
                "signal": "SELL",
                "score": bearish_score,
                "reasons": reasons
            }

        return {
            "signal": "WAIT",
            "score": max(
                bullish_score,
                bearish_score
            ),
            "reasons": reasons
        }

    # =========================================================
    # EXECUTE TRADE
    # =========================================================

    def execute_trade(
        self,
        df,
        index,
        signal
    ):

        entry = df.iloc[index]["close"]

        direction = signal["signal"]

        # -----------------------------------------------------
        # INITIAL STOP
        # -----------------------------------------------------

        if direction == "BUY":

            stop = df.iloc[index]["low"]

        else:

            stop = df.iloc[index]["high"]

        # -----------------------------------------------------
        # TARGET
        # -----------------------------------------------------

        target = self.risk.calculate_target(
            entry,
            stop,
            "bullish"
            if direction == "BUY"
            else "bearish"
        )

        valid = self.risk.validate_trade(
            entry,
            stop,
            target,
            "bullish"
            if direction == "BUY"
            else "bearish"
        )

        if not valid:

            return

        position_size = (
            self.risk.calculate_position_size(
                self.balance,
                entry,
                stop
            )
        )

        trade = {

            "entry_index": index,

            "direction": direction,

            "entry": entry,

            "stop": stop,

            "target": target,

            "position_size": position_size,

            "score": signal["score"],

            "reasons": signal["reasons"],

            "result": "OPEN",

            "profit": 0

        }

        self.trades.append(trade)

    # =========================================================
    # CHECK OPEN TRADES
    # =========================================================

    def check_trade_result(
        self,
        df,
        current_index
    ):

        current = df.iloc[current_index]

        for trade in self.trades:

            if trade["result"] != "OPEN":

                continue

            # BUY
            if trade["direction"] == "BUY":

                if current["low"] <= trade["stop"]:

                    trade["result"] = "LOSS"

                    trade["profit"] = -1

                elif current["high"] >= trade["target"]:

                    trade["result"] = "WIN"

                    trade["profit"] = 1

            # SELL
            elif trade["direction"] == "SELL":

                if current["high"] >= trade["stop"]:

                    trade["result"] = "LOSS"

                    trade["profit"] = -1

                elif current["low"] <= trade["target"]:

                    trade["result"] = "WIN"

                    trade["profit"] = 1

    # =========================================================
    # RUN BACKTEST
    # =========================================================

    def run(self, df):

        df, bias = self.prepare_data(df)

        print(
            f"Detected overall bias: {bias}"
        )

        for i in range(len(df)):

            # Check existing trades first
            self.check_trade_result(
                df,
                i
            )

            signal = self.get_signal(
                df.iloc[i]
            )

            if signal["signal"] != "WAIT":

                self.execute_trade(
                    df,
                    i,
                    signal
                )

        return self.trades
