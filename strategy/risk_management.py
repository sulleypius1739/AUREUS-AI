class RiskManager:
    """
    AUREUS risk management.

    Responsible for:

        - Risk per trade
        - Stop-loss validation
        - Risk/reward validation
        - Position sizing
        - Take-profit calculation

    IMPORTANT
    ---------

    This class does NOT decide whether a trade should exist.

    The strategy decides the signal.

    The backtest engine decides when the trade is executed.
    """

    def __init__(
        self,
        risk_percent=1.0,
        minimum_rr=2.0,
        max_risk_percent=2.0,
        pip_size=0.0001
    ):

        self.risk_percent = float(
            risk_percent
        )

        self.minimum_rr = float(
            minimum_rr
        )

        self.max_risk_percent = float(
            max_risk_percent
        )

        self.pip_size = float(
            pip_size
        )

        # -----------------------------------------------------
        # Safety checks
        # -----------------------------------------------------

        if self.risk_percent <= 0:

            raise ValueError(
                "risk_percent must be greater than 0."
            )

        if self.risk_percent > self.max_risk_percent:

            raise ValueError(
                "risk_percent exceeds the configured maximum."
            )

        if self.minimum_rr <= 0:

            raise ValueError(
                "minimum_rr must be greater than 0."
            )

        if self.pip_size <= 0:

            raise ValueError(
                "pip_size must be greater than 0."
            )

    # =========================================================
    # RISK AMOUNT
    # =========================================================

    def calculate_risk_amount(
        self,
        balance
    ):
        """
        Calculate how much account currency can be lost
        if the stop-loss is hit.

        Example:

            balance = 10,000
            risk = 1%

            risk amount = 100
        """

        balance = float(
            balance
        )

        if balance <= 0:

            return 0.0

        return (
            balance
            *
            self.risk_percent
            /
            100.0
        )

    # =========================================================
    # STOP DISTANCE
    # =========================================================

    def calculate_stop_distance(
        self,
        entry,
        stop
    ):

        return abs(
            float(entry)
            -
            float(stop)
        )

    # =========================================================
    # STOP DISTANCE IN PIPS
    # =========================================================

    def calculate_stop_pips(
        self,
        entry,
        stop
    ):
        """
        Convert price distance into pips.

        EURUSD example:

            Entry = 1.1000
            Stop  = 1.0950

            Distance = 0.0050

            Pips = 50
        """

        distance = self.calculate_stop_distance(
            entry,
            stop
        )

        if distance <= 0:

            return 0.0

        return (
            distance
            /
            self.pip_size
        )

    # =========================================================
    # POSITION SIZE
    # =========================================================

    def calculate_position_size(
        self,
        balance,
        entry,
        stop,
        pip_value_per_unit=0.0001
    ):
        """
        Calculate position size using fixed percentage risk.

        The formula is:

            position size =
                money risk
                /
                price risk per unit

        For a more complete broker-specific implementation,
        pip_value_per_unit can be adjusted to match the
        instrument/account currency.

        The default is intentionally conservative for the
        internal backtester.
        """

        balance = float(
            balance
        )

        entry = float(
            entry
        )

        stop = float(
            stop
        )

        pip_value_per_unit = float(
            pip_value_per_unit
        )

        risk_amount = self.calculate_risk_amount(
            balance
        )

        stop_pips = self.calculate_stop_pips(
            entry,
            stop
        )

        if risk_amount <= 0:

            return 0.0

        if stop_pips <= 0:

            return 0.0

        if pip_value_per_unit <= 0:

            return 0.0

        position_size = (
            risk_amount
            /
            (
                stop_pips
                *
                pip_value_per_unit
            )
        )

        return position_size

    # =========================================================
    # TAKE PROFIT
    # =========================================================

    def calculate_target(
        self,
        entry,
        stop,
        direction,
        rr=None
    ):
        """
        Calculate take-profit from risk/reward.

        BUY:

            target = entry + risk * RR

        SELL:

            target = entry - risk * RR
        """

        entry = float(
            entry
        )

        stop = float(
            stop
        )

        risk = abs(
            entry - stop
        )

        if risk <= 0:

            return None

        if rr is None:

            rr = self.minimum_rr

        rr = float(
            rr
        )

        if rr <= 0:

            return None

        reward = (
            risk
            *
            rr
        )

        direction = str(
            direction
        ).upper()

        if direction in (
            "BUY",
            "BULLISH"
        ):

            return entry + reward

        if direction in (
            "SELL",
            "BEARISH"
        ):

            return entry - reward

        return None

    # =========================================================
    # CALCULATE RR
    # =========================================================

    def calculate_rr(
        self,
        entry,
        stop,
        target
    ):
        """
        Calculate actual reward/risk ratio.
        """

        risk = abs(
            float(entry)
            -
            float(stop)
        )

        reward = abs(
            float(target)
            -
            float(entry)
        )

        if risk <= 0:

            return 0.0

        return (
            reward
            /
            risk
        )

    # =========================================================
    # VALIDATE TRADE
    # =========================================================

    def validate_trade(
        self,
        entry,
        stop,
        target,
        direction
    ):
        """
        Confirm that the trade has:

            1. Valid entry
            2. Valid stop
            3. Valid target
            4. Correct direction
            5. Minimum RR
        """

        try:

            entry = float(
                entry
            )

            stop = float(
                stop
            )

            target = float(
                target
            )

        except (
            TypeError,
            ValueError
        ):

            return False

        direction = str(
            direction
        ).upper()

        # -----------------------------------------------------
        # No invalid numbers
        # -----------------------------------------------------

        if not all(
            map(
                lambda x: x == x,
                [
                    entry,
                    stop,
                    target
                ]
            )
        ):

            return False

        # -----------------------------------------------------
        # Risk must exist
        # -----------------------------------------------------

        risk = abs(
            entry - stop
        )

        if risk <= 0:

            return False

        # -----------------------------------------------------
        # BUY
        # -----------------------------------------------------

        if direction in (
            "BUY",
            "BULLISH"
        ):

            if stop >= entry:

                return False

            if target <= entry:

                return False

        # -----------------------------------------------------
        # SELL
        # -----------------------------------------------------

        elif direction in (
            "SELL",
            "BEARISH"
        ):

            if stop <= entry:

                return False

            if target >= entry:

                return False

        else:

            return False

        # -----------------------------------------------------
        # RR
        # -----------------------------------------------------

        rr = self.calculate_rr(
            entry,
            stop,
            target
        )

        if rr < self.minimum_rr:

            return False

        return True
