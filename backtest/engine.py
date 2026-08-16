import pandas as pd
from strategy.aureus_strategy import AureusStrategy


class BacktestEngine:

    def __init__(
        self,
        starting_balance=10000,
        risk_per_trade=0.01
    ):

        self.starting_balance = starting_balance
        self.balance = starting_balance
        self.risk_per_trade = risk_per_trade

        self.strategy = AureusStrategy()

        self.trades = []

    def run(self, dataframe):

        print("Starting AUREUS backtest...")

        for i in range(len(dataframe)):

            candle = dataframe.iloc[i]

            setup = self.create_setup(
                dataframe,
                i
            )

            decision = self.strategy.evaluate(setup)

            if decision["signal"] != "WAIT":

                self.execute_trade(
                    dataframe,
                    i,
                    decision
                )

        return self.trades

    def create_setup(self, df, index):

        setup = {}

        # Placeholder structure logic.
        # These will be replaced with the actual
        # objective AUREUS definitions.

        if index < 20:
            return setup

        current = df.iloc[index]

        previous = df.iloc[index - 1]

        if current["close"] > previous["close"]:
            bias = "bullish"
        else:
            bias = "bearish"

        setup["htf_bias"] = bias

        setup["market_structure"] = bias

        setup["key_level"] = False
        setup["supply_demand"] = False
        setup["order_block"] = False
        setup["fvg"] = False
        setup["liquidity"] = True

        setup["liquidity_sweep"] = False
        setup["ltf_confirmation"] = True
        setup["candle_confirmation"] = True

        setup["fundamental_bias"] = bias
        setup["news_risk"] = "low"

        return setup

    def execute_trade(
        self,
        df,
        index,
        decision
    ):

        entry = df.iloc[index]["close"]

        direction = decision["signal"]

        if direction == "bullish":

            stop = entry * 0.99
            target = entry * 1.02

        else:

            stop = entry * 1.01
            target = entry * 0.98

        trade = {

            "index": index,

            "direction": direction,

            "entry": entry,

            "stop": stop,

            "target": target,

            "score": decision["score"],

            "result": "OPEN"

        }

        self.trades.append(trade)
