import math

import pandas as pd

from strategy.aureus_strategy import AureusStrategy
from strategy.risk_management import RiskManager


class BacktestEngine:
    """
    AUREUS Historical Backtesting Engine

    Execution model
    ---------------
    1. Strategy evaluates a completed candle.
    2. A BUY/SELL signal is generated at that candle close.
    3. Entry occurs on the NEXT candle open.
    4. Stop and target are then monitored chronologically.
    5. If both stop and target are touched in the same candle,
       the stop is assumed to have been hit first.

    This is deliberately conservative and avoids pretending
    that we can see a candle's final close and simultaneously
    execute at that exact close.
    """

    def __init__(
        self,
        starting_balance=10000,
        risk_percent=1.0,
        minimum_rr=2.0,
        minimum_score=3,
        spread=0.0,
        slippage=0.0,
        same_candle_priority="stop"
    ):

        # =====================================================
        # CONFIGURATION
        # =====================================================

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

        # Price units.
        #
        # Example:
        # EUR/USD spread = 0.00010
        #
        self.spread = float(
            spread
        )

        self.slippage = float(
            slippage
        )

        if same_candle_priority not in (
            "stop",
            "target"
        ):

            raise ValueError(
                "same_candle_priority must be "
                "'stop' or 'target'"
            )

        self.same_candle_priority = (
            same_candle_priority
        )

        # =====================================================
        # COMPONENTS
        # =====================================================

        self.strategy = AureusStrategy(
            minimum_score=minimum_score,
            risk_percent=risk_percent,
            minimum_rr=minimum_rr
        )

        self.risk = RiskManager(
            risk_percent=risk_percent,
            minimum_rr=minimum_rr
        )

        # =====================================================
        # STATE
        # =====================================================

        self.trades = []

        self.signal_count = {
            "BUY": 0,
            "SELL": 0,
            "WAIT": 0
        }

    # =========================================================
    # RESET
    # =========================================================

    def reset(self):

        self.balance = float(
            self.starting_balance
        )

        self.trades = []

        self.signal_count = {
            "BUY": 0,
            "SELL": 0,
            "WAIT": 0
        }

    # =========================================================
    # VALIDATE DATA
    # =========================================================

    def validate_data(self, df):

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
                ", ".join(missing)
            )

        if len(df) == 0:

            raise ValueError(
                "DataFrame is empty."
            )

        # -----------------------------------------------------
        # Numeric OHLC
        # -----------------------------------------------------

        for column in required:

            df[column] = pd.to_numeric(
                df[column],
                errors="coerce"
            )

        if df[
            required
        ].isna().any().any():

            raise ValueError(
                "OHLC data contains NaN or invalid values."
            )

        # -----------------------------------------------------
        # OHLC consistency
        # -----------------------------------------------------

        invalid_high = (
            df["high"]
            <
            df[
                [
                    "open",
                    "close"
                ]
            ].max(axis=1)
        )

        invalid_low = (
            df["low"]
            >
            df[
                [
                    "open",
                    "close"
                ]
            ].min(axis=1)
        )

        if invalid_high.any():

            raise ValueError(
                "Found candles where high is below "
                "open/close."
            )

        if invalid_low.any():

            raise ValueError(
                "Found candles where low is above "
                "open/close."
            )

        # -----------------------------------------------------
        # Optional timestamp
        # -----------------------------------------------------

        if "date" in df.columns:

            df["date"] = pd.to_datetime(
                df["date"],
                errors="coerce"
            )

            if df["date"].isna().any():

                raise ValueError(
                    "Date column contains invalid timestamps."
                )

            df = (
                df
                .sort_values("date")
                .drop_duplicates(
                    subset=["date"],
                    keep="first"
                )
                .reset_index(drop=True)
            )

        else:

            df = df.reset_index(
                drop=True
            )

        return df

    # =========================================================
    # PREPARE DATA
    # =========================================================

    def prepare_data(self, df):

        df = df.copy()

        # -----------------------------------------------------
        # Normalize column names.
        # -----------------------------------------------------

        df.columns = [
            str(column)
            .lower()
            .strip()
            for column in df.columns
        ]

        df = self.validate_data(
            df
        )

        # -----------------------------------------------------
        # Run AUREUS analysis.
        # -----------------------------------------------------

        df, bias = self.strategy.prepare(
            df
        )

        return df, bias

    # =========================================================
    # APPLY ENTRY COSTS
    # =========================================================

    def get_entry_price(
        self,
        raw_open,
        direction
    ):
        """
        Apply half-spread plus slippage.

        BUY:
            pay above the raw open.

        SELL:
            receive below the raw open.
        """

        half_spread = (
            self.spread / 2.0
        )

        if direction == "BUY":

            return (
                raw_open
                +
                half_spread
                +
                self.slippage
            )

        if direction == "SELL":

            return (
                raw_open
                -
                half_spread
                -
                self.slippage
            )

        return None

    # =========================================================
    # OPEN TRADE
    # =========================================================

    def open_trade(
        self,
        df,
        signal_index,
        entry_index,
        signal
    ):
        """
        Open a trade on the next candle's open.

        signal_index:
            Candle on which AUREUS generated the signal.

        entry_index:
            Candle where the order is executed.
        """

        if (
            entry_index < 0
            or
            entry_index >= len(df)
        ):

            return None

        direction = signal.get(
            "signal"
        )

        if direction not in (
            "BUY",
            "SELL"
        ):

            return None

        raw_open = float(
            df.iloc[
                entry_index
            ]["open"]
        )

        entry = self.get_entry_price(
            raw_open,
            direction
        )

        if entry is None:

            return None

        # =====================================================
        # STOP
        #
        # We deliberately use the ENTRY candle's structure,
        # not the future exit candle.
        #
        # BUY:
        #     below entry candle low
        #
        # SELL:
        #     above entry candle high
        # =====================================================

        if direction == "BUY":

            stop = float(
                df.iloc[
                    entry_index
                ]["low"]
            )

            trade_direction = "bullish"

        else:

            stop = float(
                df.iloc[
                    entry_index
                ]["high"]
            )

            trade_direction = "bearish"

        # -----------------------------------------------------
        # Safety buffer.
        #
        # Prevent an entry candle whose low/high is exactly
        # the entry from producing a zero-distance stop.
        # -----------------------------------------------------

        if direction == "BUY":

            if stop >= entry:

                stop = (
                    entry
                    -
                    max(
                        self._minimum_price_distance(
                            df
                        ),
                        1e-12
                    )
                )

        else:

            if stop <= entry:

                stop = (
                    entry
                    +
                    max(
                        self._minimum_price_distance(
                            df
                        ),
                        1e-12
                    )
                )

        # =====================================================
        # TARGET
        # =====================================================

        target = self.risk.calculate_target(
            entry,
            stop,
            trade_direction
        )

        if target is None:

            return None

        # =====================================================
        # VALIDATE
        # =====================================================

        valid = self.risk.validate_trade(
            entry,
            stop,
            target,
            trade_direction
        )

        if not valid:

            return None

        # =====================================================
        # POSITION SIZE
        # =====================================================

        position_size = (
            self.risk.calculate_position_size(
                self.balance,
                entry,
                stop
            )
        )

        if (
            not math.isfinite(
                position_size
            )
            or
            position_size <= 0
        ):

            return None

        # =====================================================
        # RISK AMOUNT
        # =====================================================

        risk_distance = abs(
            entry
            -
            stop
        )

        risk_amount = (
            self.balance
            *
            self.risk_percent
            /
            100.0
        )

        # =====================================================
        # TRADE RECORD
        # =====================================================

        trade = {

            # Signal information
            "signal_index": signal_index,

            "entry_index": entry_index,

            "direction": direction,

            # Price information
            "raw_entry": raw_open,

            "entry": entry,

            "stop": stop,

            "target": target,

            # Risk information
            "position_size": position_size,

            "risk_distance": risk_distance,

            "risk_amount": risk_amount,

            # Strategy information
            "score": signal.get(
                "score",
                0
            ),

            "reasons": signal.get(
                "reasons",
                []
            ),

            # Result
            "result": "OPEN",

            "profit_R": 0.0,

            "profit_amount": 0.0,

            "exit_index": None,

            "exit_price": None,

            # Account state
            "balance_before": self.balance,

            "balance_after": None

        }

        self.trades.append(
            trade
        )

        return trade

    # =========================================================
    # MINIMUM PRICE DISTANCE
    # =========================================================

    def _minimum_price_distance(
        self,
        df
    ):

        ranges = (
            df["high"]
            -
            df["low"]
        )

        valid = ranges[
            ranges > 0
        ]

        if len(valid) == 0:

            return 0.00001

        # Small fraction of recent average range.
        distance = (
            float(
                valid.tail(
                    min(
                        20,
                        len(valid)
                    )
                ).mean()
            )
            *
            0.05
        )

        return max(
            distance,
            0.00001
        )

    # =========================================================
    # CLOSE TRADE
    # =========================================================

    def close_trade(
        self,
        trade,
        result,
        profit_R,
        exit_index,
        exit_price
    ):
        """
        Realize P/L and update the account balance.
        """

        trade["result"] = result

        trade["profit_R"] = float(
            profit_R
        )

        trade["profit_amount"] = (
            trade["risk_amount"]
            *
            float(profit_R)
        )

        trade["exit_index"] = (
            exit_index
        )

        trade["exit_price"] = (
            float(exit_price)
        )

        trade["balance_after"] = (
            trade["balance_before"]
            +
            trade["profit_amount"]
        )

        self.balance = (
            trade["balance_after"]
        )

    # =========================================================
    # CHECK OPEN TRADES
    # =========================================================

    def check_open_trades(
        self,
        df,
        current_index
    ):
        """
        Evaluate open positions against the current completed
        candle.

        Conservative same-candle assumption:
            STOP first
            unless configured otherwise.
        """

        if (
            current_index < 0
            or
            current_index >= len(df)
        ):

            return

        current = df.iloc[
            current_index
        ]

        current_high = float(
            current["high"]
        )

        current_low = float(
            current["low"]
        )

        for trade in self.trades:

            if (
                trade["result"]
                !=
                "OPEN"
            ):

                continue

            # -------------------------------------------------
            # Do not test the entry candle itself.
            #
            # The order is assumed executed at the entry price
            # during the candle open. For a conservative model,
            # monitoring starts from the following candle.
            # -------------------------------------------------

            if (
                current_index
                <=
                trade["entry_index"]
            ):

                continue

            # =================================================
            # BUY
            # =================================================

            if (
                trade["direction"]
                ==
                "BUY"
            ):

                stop_hit = (
                    current_low
                    <=
                    trade["stop"]
                )

                target_hit = (
                    current_high
                    >=
                    trade["target"]
                )

                # -------------------------------------------------
                # Both hit in the same candle.
                # -------------------------------------------------

                if (
                    stop_hit
                    and
                    target_hit
                ):

                    if (
                        self.same_candle_priority
                        ==
                        "stop"
                    ):

                        self.close_trade(
                            trade,
                            "LOSS",
                            -1.0,
                            current_index,
                            trade["stop"]
                        )

                    else:

                        self.close_trade(
                            trade,
                            "WIN",
                            self.minimum_rr,
                            current_index,
                            trade["target"]
                        )

                elif stop_hit:

                    self.close_trade(
                        trade,
                        "LOSS",
                        -1.0,
                        current_index,
                        trade["stop"]
                    )

                elif target_hit:

                    self.close_trade(
                        trade,
                        "WIN",
                        self.minimum_rr,
                        current_index,
                        trade["target"]
                    )

            # =================================================
            # SELL
            # =================================================

            elif (
                trade["direction"]
                ==
                "SELL"
            ):

                stop_hit = (
                    current_high
                    >=
                    trade["stop"]
                )

                target_hit = (
                    current_low
                    <=
                    trade["target"]
                )

                # -------------------------------------------------
                # Both hit in the same candle.
                # -------------------------------------------------

                if (
                    stop_hit
                    and
                    target_hit
                ):

                    if (
                        self.same_candle_priority
                        ==
                        "stop"
                    ):

                        self.close_trade(
                            trade,
                            "LOSS",
                            -1.0,
                            current_index,
                            trade["stop"]
                        )

                    else:

                        self.close_trade(
                            trade,
                            "WIN",
                            self.minimum_rr,
                            current_index,
                            trade["target"]
                        )

                elif stop_hit:

                    self.close_trade(
                        trade,
                        "LOSS",
                        -1.0,
                        current_index,
                        trade["stop"]
                    )

                elif target_hit:

                    self.close_trade(
                        trade,
                        "WIN",
                        self.minimum_rr,
                        current_index,
                        trade["target"]
                    )

    # =========================================================
    # OPEN POSITION CHECK
    # =========================================================

    def has_open_position(self):

        return any(
            trade["result"] == "OPEN"
            for trade in self.trades
        )

    # =========================================================
    # CLOSE AT END
    # =========================================================

    def close_open_trades_at_end(
        self,
        df
    ):
        """
        Remaining positions are NOT silently counted as wins
        or losses.

        They remain OPEN_AT_END and receive an exit reference
        at the final available close.
        """

        if len(df) == 0:

            return

        final_index = (
            len(df) - 1
        )

        final_close = float(
            df.iloc[
                final_index
            ]["close"]
        )

        for trade in self.trades:

            if (
                trade["result"]
                !=
                "OPEN"
            ):

                continue

            trade["result"] = (
                "OPEN_AT_END"
            )

            trade["exit_index"] = (
                final_index
            )

            trade["exit_price"] = (
                final_close
            )

            trade["balance_after"] = (
                trade["balance_before"]
            )

    # =========================================================
    # RUN BACKTEST
    # =========================================================

    def run(self, df):

        self.reset()

        # =====================================================
        # PREPARE
        # =====================================================

        df, bias = self.prepare_data(
            df
        )

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

        # =====================================================
        # CHRONOLOGICAL WALK FORWARD
        # =====================================================

        for i in range(
            len(df)
        ):

            # -------------------------------------------------
            # Manage already-open trades first.
            # -------------------------------------------------

            self.check_open_trades(
                df,
                i
            )

            # -------------------------------------------------
            # Only one position at a time for the baseline.
            # -------------------------------------------------

            if self.has_open_position():

                continue

            # -------------------------------------------------
            # No entry possible on final candle because there
            # is no next candle open.
            # -------------------------------------------------

            if (
                i
                >=
                len(df) - 1
            ):

                continue

            # -------------------------------------------------
            # Generate signal using the COMPLETED current candle.
            # -------------------------------------------------

            signal = (
                self.strategy.generate_signal(
                    df,
                    i
                )
            )

            signal_name = (
                signal.get(
                    "signal",
                    "WAIT"
                )
            )

            if signal_name in (
                "BUY",
                "SELL",
                "WAIT"
            ):

                self.signal_count[
                    signal_name
                ] += 1

            # -------------------------------------------------
            # Ignore WAIT.
            # -------------------------------------------------

            if signal_name == "WAIT":

                continue

            # -------------------------------------------------
            # Entry occurs at NEXT candle open.
            # -------------------------------------------------

            entry_index = (
                i + 1
            )

            self.open_trade(
                df,
                signal_index=i,
                entry_index=entry_index,
                signal=signal
            )

        # =====================================================
        # CLOSE REMAINING
        # =====================================================

        self.close_open_trades_at_end(
            df
        )

        return (
            self.trades,
            df,
            bias
        )
