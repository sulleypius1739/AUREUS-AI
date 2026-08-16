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

        # Diagnostic counters — why did a signal NOT become a trade?
        self.diagnostics = {
            "signals_seen": 0,
            "rejected_no_stop": 0,
            "rejected_invalid_trade": 0,
            "opened": 0,
            "sample_rejections": []
        }

    # =========================================================
    # PREPARE DATA
    # =========================================================

    def prepare_data(self, df):

        df = df.copy()

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

        df, bias = self.strategy.prepare(df)

        return df, bias

    # =========================================================
    # EXECUTE TRADE
    # =========================================================
    #
    # ENTRY TIMING FIX
    # ----------------
    # The signal is generated using information available at
    # the CLOSE of `signal_index`. To avoid unrealistic
    # same-candle decide-and-execute behaviour, the trade is
    # filled at the OPEN of `entry_index` (signal_index + 1),
    # not at signal_index's own close.
    #
    # The structural stop is calculated using data known as of
    # `signal_index`'s close — never data from `entry_index`,
    # since that candle hasn't happened yet at decision time.
    # =========================================================

    def open_trade(
        self,
        df,
        signal_index,
        entry_index,
        signal
    ):

        entry = float(
            df.iloc[entry_index]["open"]
        )

        direction = signal["signal"]

        if direction == "BUY":

            trade_direction = "bullish"

        elif direction == "SELL":

            trade_direction = "bearish"

        else:

            return None

        self.diagnostics["signals_seen"] += 1

        stop = self.risk.find_structural_stop(
            df,
            signal_index,
            trade_direction
        )

        if stop is None:

            self.diagnostics["rejected_no_stop"] += 1

            if len(self.diagnostics["sample_rejections"]) < 5:
                self.diagnostics["sample_rejections"].append({
                    "reason": "no_stop",
                    "signal_index": signal_index,
                    "direction": trade_direction,
                    "entry": entry
                })

            return None

        target = self.risk.calculate_target(
            entry,
            stop,
            trade_direction
        )

        valid = self.risk.validate_trade(
            entry,
            stop,
            target,
            trade_direction
        )

        if not valid:

            self.diagnostics["rejected_invalid_trade"] += 1

            if len(self.diagnostics["sample_rejections"]) < 5:
                self.diagnostics["sample_rejections"].append({
                    "reason": "invalid_trade",
                    "signal_index": signal_index,
                    "direction": trade_direction,
                    "entry": entry,
                    "stop": stop,
                    "target": target
                })

            return None

        self.diagnostics["opened"] += 1

        position_size = (
            self.risk.calculate_position_size(
                self.balance,
                entry,
                stop
            )
        )

        trade = {

            "signal_index": signal_index,

            "entry_index": entry_index,

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

            # A trade can't be checked against a candle before
            # it was actually filled.
            if current_index < trade["entry_index"]:

                continue

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

                if stop_hit:

                    trade["result"] = "LOSS"

                    trade["profit_R"] = -1

                    trade["exit_index"] = current_index

                elif target_hit:

                    trade["result"] = "WIN"

                    trade["profit_R"] = self.minimum_rr

                    trade["exit_index"] = current_index

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

        length = len(df)

        for i in range(length):

            self.check_open_trades(
                df,
                i
            )

            open_position = any(
                trade["result"] == "OPEN"
                for trade in self.trades
            )

            if open_position:

                continue

            if i + 1 >= length:

                continue

            signal = self.strategy.generate_signal(
                df,
                i
            )

            if signal["signal"] == "WAIT":

                continue

            self.open_trade(
                df,
                i,
                i + 1,
                signal
            )

        for trade in self.trades:

            if trade["result"] == "OPEN":

                trade["result"] = "OPEN_AT_END"

                trade["exit_index"] = length - 1

        print()
        print("=" * 55)
        print("DIAGNOSTICS")
        print("=" * 55)
        print("Signals seen:          ", self.diagnostics["signals_seen"])
        print("Rejected (no stop):    ", self.diagnostics["rejected_no_stop"])
        print("Rejected (invalid RR): ", self.diagnostics["rejected_invalid_trade"])
        print("Opened:                ", self.diagnostics["opened"])
        print()
        for sample in self.diagnostics["sample_rejections"]:
            print(sample)

        return self.trades, df, bias
