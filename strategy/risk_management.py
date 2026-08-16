class RiskManager:

    def __init__(
        self,
        risk_percent=1.0,
        minimum_rr=2.0,
        stop_buffer_atr=0.15,
        atr_lookback=14,
        structural_lookback=20
    ):

        self.risk_percent = risk_percent
        self.minimum_rr = minimum_rr
        self.stop_buffer_atr = stop_buffer_atr
        self.atr_lookback = atr_lookback
        self.structural_lookback = structural_lookback

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

    # =========================================================
    # ATR
    # =========================================================
    #
    # Average true range over the lookback window, using only
    # candles up to and including `index`. No look-ahead.
    # =========================================================

    def calculate_atr(
        self,
        df,
        index,
        lookback=None
    ):

        lookback = lookback or self.atr_lookback

        start = max(1, index - lookback + 1)

        if start >= index + 1:
            return None

        highs = df["high"].to_numpy()
        lows = df["low"].to_numpy()
        closes = df["close"].to_numpy()

        true_ranges = []

        for i in range(start, index + 1):

            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1])
            )

            true_ranges.append(tr)

        if not true_ranges:
            return None

        return sum(true_ranges) / len(true_ranges)

    # =========================================================
    # STRUCTURAL STOP LOSS
    # =========================================================
    #
    # Looks backward from `index` for the most recent order
    # block in the trade direction. Falls back to the most
    # recent swing low/high. Falls back to the current
    # candle's own low/high only if nothing structural exists
    # within the lookback window.
    #
    # Mirrors the logic in riskEngine.js so both systems place
    # stops the same way.
    # =========================================================

    def find_structural_stop(
        self,
        df,
        index,
        direction,
        lookback=None
    ):

        lookback = lookback or self.structural_lookback

        atr = self.calculate_atr(df, index)

        buffer = (
            atr * self.stop_buffer_atr
            if atr
            else 0
        )

        start = max(0, index - lookback)

        if direction == "bullish":

            ob_column = "bullish_order_block"
            swing_column = "swing_low"
            price_column = "low"

        elif direction == "bearish":

            ob_column = "bearish_order_block"
            swing_column = "swing_high"
            price_column = "high"

        else:

            return float(df.iloc[index]["low"])

        # -----------------------------------------------------
        # 1. Most recent order block within the lookback window
        # -----------------------------------------------------

        for i in range(index - 1, start - 1, -1):

            if bool(df.iloc[i].get(ob_column, False)):

                level = float(df.iloc[i][price_column])

                return (
                    level - buffer
                    if direction == "bullish"
                    else level + buffer
                )

        # -----------------------------------------------------
        # 2. Most recent swing point within the lookback window
        # -----------------------------------------------------

        for i in range(index - 1, start - 1, -1):

            if bool(df.iloc[i].get(swing_column, False)):

                level = float(df.iloc[i][price_column])

                return (
                    level - buffer
                    if direction == "bullish"
                    else level + buffer
                )

        # -----------------------------------------------------
        # 3. Fallback — current candle's own low/high
        # -----------------------------------------------------

        level = float(df.iloc[index][price_column])

        return (
            level - buffer
            if direction == "bullish"
            else level + buffer
        )

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
