def calculate_metrics(trades):

    if not trades:

        return {
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0,
            "profit_factor": 0
        }

    wins = 0
    losses = 0

    gross_profit = 0
    gross_loss = 0

    for trade in trades:

        if trade["result"] == "WIN":

            wins += 1
            gross_profit += trade.get("profit", 0)

        elif trade["result"] == "LOSS":

            losses += 1
            gross_loss += abs(
                trade.get("profit", 0)
            )

    total = wins + losses

    win_rate = (
        wins / total * 100
        if total > 0
        else 0
    )

    profit_factor = (
        gross_profit / gross_loss
        if gross_loss > 0
        else 0
    )

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

    }
