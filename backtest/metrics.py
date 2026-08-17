def calculate_metrics(trades):
    closed = [t for t in trades if t.get("result") in ("WIN", "LOSS")]
    total = len(closed)
    if total == 0:
        return {
            "total_trades": 0, "wins": 0, "losses": 0, "win_rate": 0.0,
            "profit_factor": 0.0, "net_result_R": 0.0, "average_R": 0.0,
            "expectancy_R": 0.0, "best_trade_R": 0.0, "worst_trade_R": 0.0,
            "max_drawdown_R": 0.0,
        }
    rs = [float(t.get("profit_R", 0.0)) for t in closed]
    wins = sum(r > 0 for r in rs)
    losses = sum(r < 0 for r in rs)
    gp = sum(r for r in rs if r > 0)
    gl = abs(sum(r for r in rs if r < 0))
    pf = float("inf") if gl == 0 else gp / gl
    equity = peak = max_dd = 0.0
    for r in rs:
        equity += r
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
    expectancy = sum(rs) / total
    return {
        "total_trades": total,
        "wins": wins,
        "losses": losses,
        "win_rate": round(wins / total * 100.0, 2),
        "profit_factor": "INF" if pf == float("inf") else round(pf, 2),
        "net_result_R": round(sum(rs), 2),
        "average_R": round(expectancy, 4),
        "expectancy_R": round(expectancy, 4),
        "best_trade_R": round(max(rs), 2),
        "worst_trade_R": round(min(rs), 2),
        "max_drawdown_R": round(max_dd, 2),
    }
