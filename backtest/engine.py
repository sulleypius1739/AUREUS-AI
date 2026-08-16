import pandas as pd

from strategy.aureus_strategy import AureusStrategy
from strategy.risk_management import RiskManager


class BacktestEngine:

    def __init__(
        self,
        starting_balance=10000.0,
        risk_percent=1.0,
        minimum_rr=2.0,
        minimum_score=4,
        spread=0.00002,
        slippage=0.00001,
        warmup=100
    ):

        self.starting_balance = float(
            starting_balance
        )

        self.balance = float(
            starting_balance
        )

        self.risk_percent = float(
            risk_percent
        )

        self.minimum_rr = float(
            minimum_rr
        )

        self.minimum_score = int(
            minimum_score
        )

        # -----------------------------------------------------
        # Spread and slippage are expressed in price units.
        #
        # Example EURUSD:
        #
        # spread   = 0.00002
        # slippage = 0.00001
        #
        # These are intentionally conservative defaults rather
        # than pretending execution happens at the exact
        # historical candle price.
        # -----------------------------------------------------

        self.spread = float(
            spread
        )

        self.slippage = float(
            slippage
        )

        self.warmup = int(
            warmup
        )

        self.strategy = AureusStrategy(
            minimum_score=self.minimum_score,
            risk_percent=self.risk_percent,
            minimum_rr=self.minimum_rr
        )

        self.risk = RiskManager(
            risk_percent=self.risk_percent,
            minimum_rr=self.minimum_rr
        )

        self.trades = []

        self.equity_curve = []

    # =========================================================
    # PREPARE DATA
    # =========================================================

    def prepare_data(
        self,
        df
    ):

        df = df.copy()

        # -----------------------------------------------------
        # Normalize column names
        # -----------------------------------------------------

        df.columns = [
            str(column)
            .lower()
            .strip()
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
                +
                str(missing)
            )

        # -----------------------------------------------------
        # Make sure OHLC columns are numeric
        # -----------------------------------------------------

        for column in required:

            df[column] = pd.to_numeric(
                df[column],
                errors="coerce"
            )

        df = df.dropna(
            subset=required
        ).reset_index(
            drop=True
        )

        if len(df) <= self.warmup + 10:

            raise ValueError(
                "Not enough candles after cleaning "
                "for the selected warmup period."
            )

        # -----------------------------------------------------
        # Sort chronologically if a Date column exists
        # -----------------------------------------------------

        if "date" in df.columns:

            try:

                df["date"] = pd.to_datetime(
                    df["date"],
                    errors="coerce"
                )

                df = df.sort_values(
                    "date"
                ).reset_index(
                    drop=True
                )

            except Exception:

                pass

        # -----------------------------------------------------
        # Run AUREUS technical analysis.
        #
        # IMPORTANT:
        #
        # The engine will NOT use the final global bias to
        # decide historical trades.
        #
        # Historical decisions come from the information
        # attached to the current candle.
        # -----------------------------------------------------

        df, bias = self.strategy.prepare(
            df
        )

        return df, bias

    # =========================================================
    # GET ENTRY PRICE
    # =========================================================

    def get_entry_price(
        self,
        candle,
        direction
    ):

        raw_open = float(
            candle["open"]
        )

        # -----------------------------------------------------
        # BUY
        #
        # A buy pays the ask.
        # -----------------------------------------------------

        if direction == "BUY":

            return (
                raw_open
                +
                self.spread / 2
                +
                self.slippage
            )

        # -----------------------------------------------------
        # SELL
        #
        # A sell receives the bid.
        # -----------------------------------------------------

        if direction == "SELL":

            return (
                raw_open
                -
                self.spread / 2
                -
                self.slippage
            )

        return None

    # =========================================================
    # DETERMINE STOP
    # =========================================================

    def determine_stop(
        self,
        df,
        index,
        direction
    ):

        row = df.iloc[index]

        # -----------------------------------------------------
        # Current candle is the candle where the trade is
        # actually entered.
        #
        # We use the previous completed candle for the initial
        # structural stop.
        # -----------------------------------------------------

        if index <= 0:

            return None

        previous = df.iloc[
            index - 1
        ]

        # -----------------------------------------------------
        # BUY
        #
        # Stop below the previous candle low.
        # -----------------------------------------------------

        if direction == "BUY":

            stop = float(
                previous["low"]
            )

            # Small safety buffer below the structural low.
            stop -= self.slippage

            return stop

        # -----------------------------------------------------
        # SELL
        # -----------------------------------------------------

        if direction == "SELL":

            stop = float(
                previous["high"]
            )

            stop += self.slippage

            return stop

        return None

    # =========================================================
    # OPEN TRADE
    # =========================================================

    def open_trade(
        self,
        df,
        index,
        signal
    ):

        direction = signal.get(
            "signal"
        )

        if direction not in [
            "BUY",
            "SELL"
        ]:

            return None

        # -----------------------------------------------------
        # We enter at the OPEN of this candle.
        # -----------------------------------------------------

        candle = df.iloc[index]

        entry = self.get_entry_price(
            candle,
            direction
        )

        if entry is None:

            return None

        # -----------------------------------------------------
        # Structural stop
        # -----------------------------------------------------

        stop = self.determine_stop(
            df,
            index,
            direction
        )

        if stop is None:

            return None

        if direction == "BUY":

            trade_direction = "bullish"

        else:

            trade_direction = "bearish"

        # -----------------------------------------------------
        # Check stop is actually on the correct side.
        # -----------------------------------------------------

        if direction == "BUY" and stop >= entry:

            return None

        if direction == "SELL" and stop <= entry:

            return None

        # -----------------------------------------------------
        # Target
        # -----------------------------------------------------

        target = self.risk.calculate_target(
            entry,
            stop,
            trade_direction
        )

        if target is None:

            return None

        # -----------------------------------------------------
        # Validate R:R
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
        # Position size
        #
        # The existing RiskManager returns units based on
        # price distance.
        #
        # We keep that architecture for now.
        # Later we can make the FX contract-value model more
        # broker-realistic.
        # -----------------------------------------------------

        position_size = (
            self.risk.calculate_position_size(
                self.balance,
                entry,
                stop
            )
        )

        if position_size <= 0:

            return None

        risk_distance = abs(
            entry - stop
        )

        risk_amount = (
            self.balance
            *
            self.risk_percent
            /
            100.0
        )

        trade = {

            "entry_index":
                int(index),

            "direction":
                direction,

            "entry":
                float(entry),

            "stop":
                float(stop),

            "target":
                float(target),

            "position_size":
                float(position_size),

            "risk_distance":
                float(risk_distance),

            "risk_amount":
                float(risk_amount),

            "score":
                int(signal.get(
                    "score",
                    0
                )),

            "reasons":
                signal.get(
                    "reasons",
                    []
                ),

            "result":
                "OPEN",

            "profit_R":
                0.0,

            "profit_amount":
                0.0,

            "exit_index":
                None,

            "exit_price":
                None,

            "balance_before":
                float(self.balance),

            "balance_after":
                float(self.balance)

        }

        self.trades.append(
            trade
        )

        return trade

    # =========================================================
    # CLOSE TRADE
    # =========================================================

    def close_trade(
        self,
        trade,
        result,
        exit_index,
        exit_price,
        profit_R
    ):

        trade["result"] = result

        trade["exit_index"] = int(
            exit_index
        )

        trade["exit_price"] = float(
            exit_price
        )

        trade["profit_R"] = float(
            profit_R
        )

        trade["profit_amount"] = (
            trade["risk_amount"]
            *
            float(profit_R)
        )

        self.balance += (
            trade["profit_amount"]
        )

        trade["balance_after"] = (
            float(self.balance)
        )

    # =========================================================
    # CHECK OPEN TRADES
    # =========================================================

    def check_open_trades(
        self,
        df,
        current_index
    ):

        current = df.iloc[
            current_index
        ]

        high = float(
            current["high"]
        )

        low = float(
            current["low"]
        )

        for trade in self.trades:

            if trade["result"] != "OPEN":

                continue

            # =================================================
            # BUY
            # =================================================

            if trade["direction"] == "BUY":

                stop_hit = (
                    low
                    <=
                    trade["stop"]
                )

                target_hit = (
                    high
                    >=
                    trade["target"]
                )

                # -------------------------------------------------
                # If both SL and TP are touched during the same
                # candle, we assume SL occurred first.
                #
                # This is conservative and avoids artificially
                # inflating results.
                # -------------------------------------------------

                if stop_hit:

                    self.close_trade(
                        trade=trade,
                        result="LOSS",
                        exit_index=current_index,
                        exit_price=trade["stop"],
                        profit_R=-1.0
                    )

                elif target_hit:

                    self.close_trade(
                        trade=trade,
                        result="WIN",
                        exit_index=current_index,
                        exit_price=trade["target"],
                        profit_R=self.minimum_rr
                    )

            # =================================================
            # SELL
            # =================================================

            elif trade["direction"] == "SELL":

                stop_hit = (
                    high
                    >=
                    trade["stop"]
                )

                target_hit = (
                    low
                    <=
                    trade["target"]
                )

                if stop_hit:

                    self.close_trade(
                        trade=trade,
                        result="LOSS",
                        exit_index=current_index,
                        exit_price=trade["stop"],
                        profit_R=-1.0
                    )

                elif target_hit:

                    self.close_trade(
                        trade=trade,
                        result="WIN",
                        exit_index=current_index,
                        exit_price=trade["target"],
                        profit_R=self.minimum_rr
                    )

    # =========================================================
    # RECORD EQUITY
    # =========================================================

    def record_equity(
        self,
        index
    ):

        self.equity_curve.append(
            {
                "index": int(index),
                "balance": float(
                    self.balance
                )
            }
        )

    # =========================================================
    # GET OPEN POSITION
    # =========================================================

    def has_open_position(self):

        return any(
            trade["result"] == "OPEN"
            for trade in self.trades
        )

    # =========================================================
    # RUN BACKTEST
    # =========================================================

    def run(
        self,
        df
    ):

        # -----------------------------------------------------
        # Reset engine so it can safely be reused.
        # -----------------------------------------------------

        self.balance = (
            self.starting_balance
        )

        self.trades = []

        self.equity_curve = []

        # -----------------------------------------------------
        # Prepare technical data
        # -----------------------------------------------------

        df, global_bias = (
            self.prepare_data(df)
        )

        print()
        print(
            "AUREUS structural bias:",
            global_bias
        )

        print(
            "Candles analysed:",
            len(df)
        )

        print()

        # =====================================================
        # WALK FORWARD
        # =====================================================

        start_index = max(
            self.warmup,
            1
        )

        for i in range(
            start_index,
            len(df)
        ):

            # -------------------------------------------------
            # FIRST:
            #
            # Manage existing positions using the current
            # candle.
            # -------------------------------------------------

            self.check_open_trades(
                df,
                i
            )

            # -------------------------------------------------
            # Record current equity.
            # -------------------------------------------------

            self.record_equity(
                i
            )

            # -------------------------------------------------
            # Only one position at a time.
            # -------------------------------------------------

            if self.has_open_position():

                continue

            # -------------------------------------------------
            # Generate signal.
            #
            # The signal is generated from the completed
            # candle at index i.
            #
            # Therefore the actual entry happens at i+1.
            # -------------------------------------------------

            signal = (
                self.strategy.generate_signal(
                    df,
                    i
                )
            )

            if signal["signal"] == "WAIT":

                continue

            # -------------------------------------------------
            # We cannot enter on the last candle because there
            # is no following candle open.
            # -------------------------------------------------

            entry_index = i + 1

            if entry_index >= len(df):

                break

            # -------------------------------------------------
            # Open at next candle's open.
            # -------------------------------------------------

            self.open_trade(
                df,
                entry_index,
                signal
            )

        # =====================================================
        # CLOSE REMAINING POSITIONS
        # =====================================================

        final_index = len(df) - 1

        final_close = float(
            df.iloc[
                final_index
            ]["close"]
        )

        for trade in self.trades:

            if trade["result"] != "OPEN":

                continue

            # -------------------------------------------------
            # Mark-to-market final close.
            #
            # We do not pretend an unfinished position was a
            # WIN or LOSS at its target.
            # -------------------------------------------------

            if trade["direction"] == "BUY":

                price_change = (
                    final_close
                    -
                    trade["entry"]
                )

            else:

                price_change = (
                    trade["entry"]
                    -
                    final_close
                )

            if trade["risk_distance"] > 0:

                unrealized_R = (
                    price_change
                    /
                    trade["risk_distance"]
                )

            else:

                unrealized_R = 0.0

            trade["result"] = (
                "OPEN_AT_END"
            )

            trade["exit_index"] = (
                final_index
            )

            trade["exit_price"] = (
                final_close
            )

            trade["profit_R"] = float(
                unrealized_R
            )

            trade["profit_amount"] = (
                trade["risk_amount"]
                *
                float(unrealized_R)
            )

            # -------------------------------------------------
            # IMPORTANT:
            #
            # We do NOT add this unrealized P/L to balance.
            # It remains an open position at the end of the
            # dataset.
            # -------------------------------------------------

            trade["balance_after"] = (
                self.balance
            )

        return (
            self.trades,
            df,
            global_bias
        )
