def calculate_metrics(trades):

    closed_trades = [
        trade
        for trade in trades
        if trade["result"] in ["WIN", "LOSS"]
    ]

    total = len(closed_trades)

    if total == 0:

        return {
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0,
            "profit_factor": 0,
            "net_result_R": 0
        }

    wins = sum(
        1
        for trade in closed_trades
        if trade["result"] == "WIN"
    )

    losses = sum(
        1
        for trade in closed_trades
        if trade["result"] == "LOSS"
    )

    gross_profit = wins

    gross_loss = losses

    if gross_loss == 0:

        profit_factor = float("inf")

    else:

        profit_factor = (
            gross_profit / gross_loss
        )

    net_result = (
        wins - losses
    )

    win_rate = (
        wins / total
    ) * 100

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

        "net_result_R": net_result
    }
