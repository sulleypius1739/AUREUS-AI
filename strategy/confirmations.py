class RiskManager:

    def __init__(
        self,
        risk_percent=1.0,
        minimum_rr=2.0
    ):

        self.risk_percent = risk_percent
        self.minimum_rr = minimum_rr

    def calculate_position_size(
        self,
        balance,
        entry,
        stop
    ):

        risk_amount = (
            balance
            *
            self.risk_percent
            /
            100
        )

        distance = abs(entry - stop)

        if distance == 0:
            return 0

        return risk_amount / distance

    def calculate_target(
        self,
        entry,
        stop,
        direction
    ):

        risk = abs(entry - stop)

        reward = (
            risk * self.minimum_rr
        )

        if direction == "bullish":

            return entry + reward

        if direction == "bearish":

            return entry - reward

        return None

    def validate_trade(
        self,
        entry,
        stop,
        target,
        direction
    ):

        risk = abs(entry - stop)

        reward = abs(target - entry)

        if risk == 0:
            return False

        rr = reward / risk

        if rr < self.minimum_rr:
            return False

        if direction == "bullish":

            if stop >= entry:
                return False

            if target <= entry:
                return False

        elif direction == "bearish":

            if stop <= entry:
                return False

            if target >= entry:
                return False

        else:

            return False

        return True
