import math
import pandas as pd

from strategy.aureus_strategy import AureusStrategy
from strategy.risk_management import RiskManager


class BacktestEngine:
    """Chronological AUREUS V2 backtester with next-bar-open execution."""

    def __init__(
        self,
        starting_balance=10000,
        risk_percent=1.0,
        minimum_rr=2.0,
        minimum_score=7,
        spread=0.0,
        slippage=0.0,
        same_candle_priority="stop",
        require_liquidity_sweep=True,
        require_premium_discount=True,
        require_confirmation=True,
    ):
        self.starting_balance = float(starting_balance)
        self.risk_percent = float(risk_percent)
        self.minimum_rr = float(minimum_rr)
        self.minimum_score = int(minimum_score)
        self.spread = float(spread)
        self.slippage = float(slippage)
        self.same_candle_priority = same_candle_priority
        if same_candle_priority not in ("stop", "target"):
            raise ValueError("same_candle_priority must be 'stop' or 'target'")

        self.strategy = AureusStrategy(
            minimum_score=minimum_score,
            risk_percent=risk_percent,
            minimum_rr=minimum_rr,
            require_liquidity_sweep=require_liquidity_sweep,
            require_premium_discount=require_premium_discount,
            require_confirmation=require_confirmation,
        )
        self.risk = RiskManager(risk_percent=risk_percent, minimum_rr=minimum_rr)
        self.reset()

    def reset(self):
        self.balance = self.starting_balance
        self.trades = []
        self.signal_count = {"BUY": 0, "SELL": 0, "WAIT": 0}

    def validate_data(self, df):
        df = df.copy()
        df.columns = [str(c).lower().strip() for c in df.columns]
        required = ["open", "high", "low", "close"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError("Missing required columns: " + ", ".join(missing))
        if df.empty:
            raise ValueError("DataFrame is empty")
        for c in required:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        if df[required].isna().any().any():
            raise ValueError("OHLC data contains invalid values")
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            if df["date"].isna().any():
                raise ValueError("Date column contains invalid timestamps")
            df = df.sort_values("date").drop_duplicates("date").reset_index(drop=True)
        else:
            df = df.reset_index(drop=True)
        return df

    def prepare_data(self, df):
        return self.strategy.prepare(self.validate_data(df))

    def _entry_price(self, raw_open, direction):
        half = self.spread / 2.0
        return raw_open + half + self.slippage if direction == "BUY" else raw_open - half - self.slippage

    def _stop_from_retest_zone(self, df, signal_index, direction, entry):
        row = df.iloc[signal_index]
        if direction == "BUY":
            vals = []
            for c in ("retest_bullish_zone_low", "active_bullish_zone_low"):
                v = row.get(c)
                if v == v:
                    vals.append(float(v))
            stop = min(vals) - self.risk.stop_buffer if vals else float(row["low"]) - self.risk.stop_buffer
            if stop >= entry:
                stop = float(row["low"]) - self.risk.stop_buffer
            return stop

        vals = []
        for c in ("retest_bearish_zone_high", "active_bearish_zone_high"):
            v = row.get(c)
            if v == v:
                vals.append(float(v))
        stop = max(vals) + self.risk.stop_buffer if vals else float(row["high"]) + self.risk.stop_buffer
        if stop <= entry:
            stop = float(row["high"]) + self.risk.stop_buffer
        return stop

    def _target_from_known_levels(self, df, signal_index, direction, entry):
        row = df.iloc[signal_index]
        if direction == "BUY":
            protected = row.get("protected_high")
            if protected == protected and float(protected) > entry:
                return float(protected)
            for key in ("last_major_high", "candidate_high"):
                value = row.get(key)
                if value == value and float(value) > entry:
                    return float(value)
            flags = df["confirmed_swing_high"].to_numpy(dtype=bool)
            prices = df["swing_high_price"].to_numpy(dtype=float)
            hist = [float(prices[i]) for i in range(signal_index + 1) if flags[i] and prices[i] == prices[i] and float(prices[i]) > entry]
            return min(hist) if hist else None
        protected = row.get("protected_low")
        if protected == protected and float(protected) < entry:
            return float(protected)
        for key in ("last_major_low", "candidate_low"):
            value = row.get(key)
            if value == value and float(value) < entry:
                return float(value)
        flags = df["confirmed_swing_low"].to_numpy(dtype=bool)
        prices = df["swing_low_price"].to_numpy(dtype=float)
        hist = [float(prices[i]) for i in range(signal_index + 1) if flags[i] and prices[i] == prices[i] and float(prices[i]) < entry]
        return max(hist) if hist else None

    def open_trade(self, df, signal_index, entry_index, signal):
        if entry_index >= len(df):
            return None
        direction = signal.get("signal")
        if direction not in ("BUY", "SELL"):
            return None

        raw_open = float(df.iloc[entry_index]["open"])
        entry = self._entry_price(raw_open, direction)
        trade_direction = "bullish" if direction == "BUY" else "bearish"
        stop = self._stop_from_retest_zone(df, signal_index, direction, entry)
        target = self._target_from_known_levels(df, signal_index, direction, entry)

        if target is None or not self.risk.validate_trade(entry, stop, target, trade_direction):
            return None

        position_size = self.risk.calculate_position_size(self.balance, entry, stop)
        if not math.isfinite(position_size) or position_size <= 0:
            return None

        risk_distance = abs(entry - stop)
        risk_amount = self.balance * self.risk_percent / 100.0
        planned_rr = abs(target - entry) / risk_distance if risk_distance > 0 else 0.0

        trade = {
            "signal_index": int(signal_index),
            "entry_index": int(entry_index),
            "direction": direction,
            "raw_entry": raw_open,
            "entry": entry,
            "stop": stop,
            "target": target,
            "position_size": position_size,
            "risk_distance": risk_distance,
            "risk_amount": risk_amount,
            "planned_rr": planned_rr,
            "score": int(signal.get("score", 0)),
            "reasons": signal.get("reasons", []),
            "result": "OPEN",
            "profit_R": 0.0,
            "profit_amount": 0.0,
            "exit_index": None,
            "exit_price": None,
            "balance_before": self.balance,
            "balance_after": None,
        }
        self.trades.append(trade)
        return trade

    def close_trade(self, trade, result, profit_R, exit_index, exit_price):
        trade["result"] = result
        trade["profit_R"] = float(profit_R)
        trade["profit_amount"] = trade["risk_amount"] * float(profit_R)
        trade["exit_index"] = int(exit_index)
        trade["exit_price"] = float(exit_price)
        trade["balance_after"] = trade["balance_before"] + trade["profit_amount"]
        self.balance = trade["balance_after"]

    def check_open_trades(self, df, current_index):
        if current_index < 0 or current_index >= len(df):
            return
        row = df.iloc[current_index]
        hi = float(row["high"])
        lo = float(row["low"])
        for trade in self.trades:
            if trade["result"] != "OPEN" or current_index <= trade["entry_index"]:
                continue
            if trade["direction"] == "BUY":
                stop_hit = lo <= trade["stop"]
                target_hit = hi >= trade["target"]
            else:
                stop_hit = hi >= trade["stop"]
                target_hit = lo <= trade["target"]
            if stop_hit and target_hit:
                if self.same_candle_priority == "stop":
                    self.close_trade(trade, "LOSS", -1.0, current_index, trade["stop"])
                else:
                    self.close_trade(trade, "WIN", self.minimum_rr, current_index, trade["target"])
            elif stop_hit:
                self.close_trade(trade, "LOSS", -1.0, current_index, trade["stop"])
            elif target_hit:
                self.close_trade(trade, "WIN", self.minimum_rr, current_index, trade["target"])

    def has_open_position(self):
        return any(t["result"] == "OPEN" for t in self.trades)

    def close_open_trades_at_end(self, df):
        idx = len(df) - 1
        px = float(df.iloc[idx]["close"])
        for trade in self.trades:
            if trade["result"] == "OPEN":
                trade["result"] = "OPEN_AT_END"
                trade["exit_index"] = idx
                trade["exit_price"] = px
                trade["balance_after"] = trade["balance_before"]

    def run(self, df):
        self.reset()
        df, bias = self.prepare_data(df)
        for i in range(len(df) - 1):
            self.check_open_trades(df, i)
            if self.has_open_position():
                continue
            signal = self.strategy.generate_signal(df, i)
            name = signal.get("signal", "WAIT")
            self.signal_count[name] = self.signal_count.get(name, 0) + 1
            if name in ("BUY", "SELL"):
                self.open_trade(df, i, i + 1, signal)
        self.check_open_trades(df, len(df) - 1)
        self.close_open_trades_at_end(df)
        return self.trades, df, bias
