from __future__ import annotations

import pandas as pd

from strategy.top_down import TopDownStrategy
from strategy.timeframes import build_mtf_data


class MTFBacktestEngine:
    """Causal M5 execution engine for AUREUS V3.

    Memory-conscious implementation:
      - strategy returns only actionable signal objects
      - only one active trade is tracked at a time
      - M5 OHLC is accessed as NumPy arrays, not Series via iloc
      - progress is printed periodically during long runs
    """

    def __init__(
        self,
        starting_balance=10000.0,
        risk_percent=1.0,
        minimum_rr=2.0,
        stop_buffer=0.00002,
        same_candle_priority="stop",
        progress_every=100000,
    ):
        self.starting_balance = float(starting_balance)
        self.balance = float(starting_balance)
        self.risk_percent = float(risk_percent)
        self.minimum_rr = float(minimum_rr)
        self.stop_buffer = float(stop_buffer)
        self.same_candle_priority = same_candle_priority
        self.progress_every = int(progress_every)
        self.strategy = TopDownStrategy(
            minimum_rr=minimum_rr,
            risk_percent=risk_percent,
            stop_buffer=stop_buffer,
        )
        self.trades = []
        self.signal_count = {"BUY": 0, "SELL": 0, "WAIT": 0}
        self._records = None
        self._analysed = None

    def reset(self):
        self.balance = self.starting_balance
        self.trades = []
        self.signal_count = {"BUY": 0, "SELL": 0, "WAIT": 0}

    def _risk_position(self, entry, stop):
        distance = abs(entry - stop)
        if distance <= 0:
            return 0.0, 0.0
        risk_amount = self.balance * self.risk_percent / 100.0
        return risk_amount / distance, risk_amount

    def _open_trade(self, signal, current_idx, next_idx, timestamps, opens):
        entry = float(opens[next_idx])
        direction = signal.direction
        stop = float(signal.stop)
        target = float(signal.target)

        if direction == "bullish" and not (stop < entry < target):
            return None
        if direction == "bearish" and not (target < entry < stop):
            return None

        distance = abs(entry - stop)
        rr = abs(target - entry) / distance if distance > 0 else 0.0
        if rr < self.minimum_rr:
            return None

        size, risk_amount = self._risk_position(entry, stop)
        trade = {
            "signal_time": str(timestamps[current_idx]),
            "entry_time": str(timestamps[next_idx]),
            "signal_index": current_idx,
            "entry_index": next_idx,
            "direction": "BUY" if direction == "bullish" else "SELL",
            "entry": entry,
            "stop": stop,
            "target": target,
            "position_size": size,
            "risk_distance": distance,
            "risk_amount": risk_amount,
            "planned_rr": rr,
            "score": signal.score,
            "reasons": signal.reasons,
            "daily_bias": signal.daily_bias,
            "h4_bias": signal.h4_bias,
            "h1_bias": signal.h1_bias,
            "entry_timeframe": signal.timeframe,
            "result": "OPEN",
            "profit_R": 0.0,
            "profit_amount": 0.0,
            "exit_index": None,
            "exit_time": None,
            "exit_price": None,
            "balance_before": self.balance,
            "balance_after": self.balance,
        }
        self.trades.append(trade)
        return trade

    def _check_trade_arrays(self, trade, high, low, timestamp, idx):
        if trade["result"] != "OPEN":
            return False

        if trade["direction"] == "BUY":
            stop_hit = low <= trade["stop"]
            target_hit = high >= trade["target"]
        else:
            stop_hit = high >= trade["stop"]
            target_hit = low <= trade["target"]

        if stop_hit and target_hit:
            hit = "LOSS" if self.same_candle_priority == "stop" else "WIN"
        elif stop_hit:
            hit = "LOSS"
        elif target_hit:
            hit = "WIN"
        else:
            return False

        trade["result"] = hit
        trade["profit_R"] = -1.0 if hit == "LOSS" else self.minimum_rr
        trade["profit_amount"] = trade["risk_amount"] * trade["profit_R"]
        trade["exit_index"] = idx
        trade["exit_time"] = str(timestamp)
        trade["exit_price"] = trade["stop"] if hit == "LOSS" else trade["target"]
        self.balance += trade["profit_amount"]
        trade["balance_after"] = self.balance
        return True

    def run(self, df):
        self.reset()
        mtf = build_mtf_data(df)
        signal_map, analysed = self.strategy.run_signals(mtf)
        self._records = signal_map
        self._analysed = analysed

        base = mtf.base
        timestamps = base["timestamp"].to_numpy()
        opens = base["open"].to_numpy(dtype=float)
        highs = base["high"].to_numpy(dtype=float)
        lows = base["low"].to_numpy(dtype=float)
        closes = base["close"].to_numpy(dtype=float)
        n = len(base)

        open_trade = None
        total_signalable = len(signal_map)

        for i in range(n - 1):
            if open_trade is not None:
                self._check_trade_arrays(
                    open_trade,
                    highs[i],
                    lows[i],
                    timestamps[i],
                    i,
                )
                if open_trade["result"] != "OPEN":
                    open_trade = None

            if open_trade is not None:
                self.signal_count["WAIT"] += 1
            else:
                signal = signal_map.get(i)
                if signal is None:
                    self.signal_count["WAIT"] += 1
                else:
                    self.signal_count[signal.signal] += 1
                    if signal.signal in ("BUY", "SELL"):
                        open_trade = self._open_trade(
                            signal,
                            i,
                            i + 1,
                            timestamps,
                            opens,
                        )

            if self.progress_every and (i + 1) % self.progress_every == 0:
                pct = (i + 1) / max(n - 1, 1) * 100.0
                print(
                    f"Progress: {i + 1:,}/{n - 1:,} "
                    f"({pct:.1f}%) | signals={total_signalable:,} "
                    f"| trades={len(self.trades):,} "
                    f"| balance={self.balance:.2f}",
                    flush=True,
                )

        if open_trade is not None and open_trade["result"] == "OPEN":
            open_trade["result"] = "OPEN_AT_END"
            open_trade["exit_index"] = n - 1
            open_trade["exit_time"] = str(timestamps[-1])
            open_trade["exit_price"] = float(closes[-1])
            open_trade["balance_after"] = self.balance

        return self.trades, analysed, signal_map
