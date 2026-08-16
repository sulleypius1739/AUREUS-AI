def calculate_metrics(trades):

    # =========================================================
    # KEEP ONLY CLOSED TRADES
    # =========================================================

    closed_trades = [
        trade
        for trade in trades
        if trade.get("result") in ["WIN", "LOSS"]
    ]

    total = len(closed_trades)

    # =========================================================
    # NO TRADES
    # =========================================================

    if total == 0:

        return {
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0,
            "profit_factor": 0,
            "net_result_R": 0,
            "average_R": 0,
            "best_trade_R": 0,
            "worst_trade_R": 0
        }

    # =========================================================
    # WIN / LOSS COUNTS
    # =========================================================

    wins = sum(
        1
        for trade in closed_trades
        if trade.get("result") == "WIN"
    )

    losses = sum(
        1
        for trade in closed_trades
        if trade.get("result") == "LOSS"
    )

    # =========================================================
    # ACTUAL R RESULTS
    #
    # IMPORTANT:
    #
    # We use the actual profit_R stored in every trade.
    #
    # Example:
    #
    # WIN  = +2R
    # LOSS = -1R
    #
    # =========================================================

    profit_values = []

    for trade in closed_trades:

        try:

            value = float(
                trade.get(
                    "profit_R",
                    0
                )
            )

        except (TypeError, ValueError):

            value = 0.0

        profit_values.append(value)

    # =========================================================
    # GROSS PROFIT
    # =========================================================

    gross_profit = sum(
        value
        for value in profit_values
        if value > 0
    )

    # =========================================================
    # GROSS LOSS
    #
    # Stored as a positive number for profit factor.
    # =========================================================

    gross_loss = abs(
        sum(
            value
            for value in profit_values
            if value < 0
        )
    )

    # =========================================================
    # PROFIT FACTOR
    #
    # Profit Factor =
    #
    # Gross Profit / Gross Loss
    #
    # =========================================================

    if gross_loss == 0:

        profit_factor = float("inf")

    else:

        profit_factor = (
            gross_profit /
            gross_loss
        )

    # =========================================================
    # NET RESULT
    # =========================================================

    net_result = sum(
        profit_values
    )

    # =========================================================
    # WIN RATE
    # =========================================================

    win_rate = (
        wins /
        total
    ) * 100

    # =========================================================
    # AVERAGE R
    # =========================================================

    average_R = (
        net_result /
        total
    )

    # =========================================================
    # BEST / WORST TRADE
    # =========================================================

    best_trade_R = max(
        profit_values
    )

    worst_trade_R = min(
        profit_values
    )

    # =========================================================
    # RETURN RESULTS
    # =========================================================

    return {

        "total_trades": total,

        "wins": wins,

        "losses": losses,

        "win_rate": round(
            win_rate,
            2
        ),

        "profit_factor": round(
            profit_factor,
            2
        )
        if profit_factor != float("inf")
        else "INF",

        "net_result_R": round(
            net_result,
            2
        ),

        "average_R": round(
            average_R,
            4
        ),

        "best_trade_R": round(
            best_trade_R,
            2
        ),

        "worst_trade_R": round(
            worst_trade_R,
            2
        )
    }
