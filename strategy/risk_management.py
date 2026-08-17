import math


class RiskManager:
    """Risk calculations for causal backtesting."""

    def __init__(self, risk_percent=1.0, minimum_rr=2.0, stop_buffer=2.0):
        self.risk_percent = float(risk_percent)
        self.minimum_rr = float(minimum_rr)
        self.stop_buffer = float(stop_buffer)
        if self.risk_percent <= 0:
            raise ValueError("risk_percent must be > 0")
        if self.minimum_rr <= 0:
            raise ValueError("minimum_rr must be > 0")
        if self.stop_buffer < 0:
            raise ValueError("stop_buffer must be >= 0")

    def calculate_position_size(self, balance, entry, stop):
        risk_amount = float(balance) * self.risk_percent / 100.0
        distance = abs(float(entry) - float(stop))
        if distance <= 0:
            return 0.0
        size = risk_amount / distance
        return float(size) if math.isfinite(size) else 0.0

    def calculate_rr(self, entry, stop, target):
        risk = abs(float(entry) - float(stop))
        reward = abs(float(target) - float(entry))
        if risk <= 0:
            return 0.0
        return float(reward / risk)

    def validate_trade(self, entry, stop, target, direction):
        if target is None:
            return False
        risk = abs(float(entry) - float(stop))
        reward = abs(float(target) - float(entry))
        if risk <= 0:
            return False
        rr = reward / risk
        if rr + 1e-12 < self.minimum_rr:
            return False
        if direction == "bullish":
            return stop < entry and target > entry
        if direction == "bearish":
            return stop > entry and target < entry
        return False

    def buffer_stop(self, price, direction):
        if direction == "bullish":
            return float(price) - self.stop_buffer
        if direction == "bearish":
            return float(price) + self.stop_buffer
        raise ValueError("direction must be bullish or bearish")
