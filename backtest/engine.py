import pandas as pd

from strategy.aureus_strategy import AureusStrategy
from strategy.risk_management import RiskManager


class BacktestEngine:

    def __init__(
        self,
        starting_balance=10000,
        risk_percent=1.0,
        minimum_rr=2.0,
        minimum_score=3
    ):

        self.starting_balance = starting_balance
        self.balance = starting_balance

        self.risk_percent = risk_percent
        self.minimum_rr = minimum_rr

        # The actual AUREUS technical strategy
        self.strategy = AureusStrategy(
            minimum_score=minimum_score,
            risk_percent=risk_percent,
            minimum_rr=minimum_rr
        )

        self.risk = RiskManager(
            risk_percent=risk_percent,
            minimum_rr=minimum_rr
        )

        self.trades = []

    # =========================================================
    # PREPARE DATA
    # =========================================================

    def prepare_data(self, df):

        df = df.copy()

        # Make column names consistent
        df.columns = [
            str(column).lower().strip()
            for column in df.columns
        ]

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
                "Missing required columns: "
                + str(missing)
            )

        # Run the complete AUREUS technical analysis
        df, bias = self.strategy.prepare(df)

        return df, bias

    # =========================================================
    # EXECUTE TRADE
    # =========================================================

    def open_trade(
        self,
        df,
        index,
        signal
    ):

        entry = float(
            df.iloc[index]["close"]
        )

        direction = signal["signal"]

        # -----------------------------------------------------
        # STOP LOSS
        # -----------------------------------------------------
        #
        # Initial version:
        #
        # BUY  → below current candle low
        # SELL → above current candle high
        #
        # Later we will improve this to use protected
        # swing highs/lows and liquidity structure.
        # -----------------------------------------------------

        if direction == "BUY":

            stop = float(
                df.iloc[index]["low"]
            )

            trade_direction = "bullish"

        elif direction == "SELL":

            stop = float(
                df.iloc[index]["high"]
            )

            trade_direction = "bearish"

        else:

            return None

        # -----------------------------------------------------
        # TAKE PROFIT
        # -----------------------------------------------------

        target = self.risk.calculate_target(
            entry,
            stop,
            trade_direction
        )

        # -----------------------------------------------------
        # VALIDATE RISK/REWARD
        # -----------------------------------------------------

        valid = self.risk.validate_trade(
            entry,
            stop,
            target,
            trade_direction
        )

        if not valid:

            return None

        # -----------------------------------------------------
        # POSITION SIZE
        # -----------------------------------------------------

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

            "profit_R": 0,

            "exit_index": None

        }

        self.trades.append(trade)

        return trade

    # =========================================================
    # CHECK OPEN TRADES
    # =========================================================

    def check_open_trades(
        self,
        df,
        current_index
    ):

        current = df.iloc[current_index]

        for trade in self.trades:

            if trade["result"] != "OPEN":

                continue

            # =================================================
            # BUY
            # =================================================

            if trade["direction"] == "BUY":

                stop_hit = (
                    current["low"]
                    <=
                    trade["stop"]
                )

                target_hit = (
                    current["high"]
                    >=
                    trade["target"]
                )

                # Conservative assumption:
                # If both happen within the same candle,
                # assume the stop was hit first.
                if stop_hit:

                    trade["result"] = "LOSS"

                    trade["profit_R"] = -1

                    trade["exit_index"] = current_index

                elif target_hit:

                    trade["result"] = "WIN"

                    trade["profit_R"] = self.minimum_rr

                    trade["exit_index"] = current_index

            # =================================================
            # SELL
            # =================================================

            elif trade["direction"] == "SELL":

                stop_hit = (
                    current["high"]
                    >=
                    trade["stop"]
                )

                target_hit = (
                    current["low"]
                    <=
                    trade["target"]
                )

                if stop_hit:

                    trade["result"] = "LOSS"

                    trade["profit_R"] = -1

                    trade["exit_index"] = current_index

                elif target_hit:

                    trade["result"] = "WIN"

                    trade["profit_R"] = self.minimum_rr

                    trade["exit_index"] = current_index

    # =========================================================
    # RUN BACKTEST
    # =========================================================

    def run(self, df):

        df, bias = self.prepare_data(df)

        print()
        print(
            "AUREUS structural bias:",
            bias
        )

        print(
            "Candles analysed:",
            len(df)
        )

        print()

        # -----------------------------------------------------
        # WALK FORWARD THROUGH HISTORY
        # -----------------------------------------------------
        #
        # This is important:
        #
        # The strategy only gets information available at
        # each candle.
        #
        # We don't intentionally look into the future when
        # making the trading decision.
        # -----------------------------------------------------

        for i in range(len(df)):

            # First manage existing positions
            self.check_open_trades(
                df,
                i
            )

            # Don't open another trade if there is already
            # an open position.
            open_position = any(
                trade["result"] == "OPEN"
                for trade in self.trades
            )

            if open_position:

                continue

            # Generate AUREUS signal
            signal = self.strategy.generate_signal(
                df,
                i
            )

            # Only trade BUY or SELL
            if signal["signal"] == "WAIT":

                continue

            # Open trade
            self.open_trade(
                df,
                i,
                signal
            )

        # -----------------------------------------------------
        # CLOSE REMAINING POSITIONS
        # -----------------------------------------------------

        for trade in self.trades:

            if trade["result"] == "OPEN":

                trade["result"] = "OPEN_AT_END"

                trade["exit_index"] = len(df) - 1

        return self.trades, df, bias
