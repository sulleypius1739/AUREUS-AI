from pathlib import Path

import pandas as pd

from backtest.engine import BacktestEngine
from backtest.metrics import calculate_metrics


def main():

    print()
    print("==============================================")
    print("                AUREUS AI")
    print("           HISTORICAL BACKTEST")
    print("==============================================")
    print()

    file_path = input(
        "Enter CSV file path: "
    ).strip()

    file_path = Path(file_path)

    if not file_path.exists():

        print()
        print("ERROR: File does not exist.")
        print(file_path)
        return

    try:

        df = pd.read_csv(file_path)

    except Exception as error:

        print()
        print("ERROR: Could not read CSV.")
        print(error)
        return

    print()
    print("Data loaded successfully.")
    print()
    print("Rows:", len(df))
    print("Columns:", list(df.columns))
    print()

    engine = BacktestEngine(
        starting_balance=10000,
        risk_percent=1.0,
        minimum_rr=2.0,
        minimum_score=3
    )

    try:

        trades, analysed_data, bias = engine.run(df)

    except Exception as error:

        print()
        print("==============================================")
        print("              BACKTEST ERROR")
        print("==============================================")
        print(error)
        return

    metrics = calculate_metrics(trades)

    print()
    print("==============================================")
    print("              AUREUS RESULTS")
    print("==============================================")
    print()

    print(
        "Structural bias:",
        bias
    )

    print(
        "Total trades:",
        metrics["total_trades"]
    )

    print(
        "Wins:",
        metrics["wins"]
    )

    print(
        "Losses:",
        metrics["losses"]
    )

    print(
        "Win rate:",
        str(metrics["win_rate"]) + "%"
    )

    print(
        "Profit factor:",
        metrics["profit_factor"]
    )

    print(
        "Net result (R):",
        metrics["net_result_R"]
    )

    print()

    print(
        "Signals generated:",
        (
            analysed_data["aureus_signal"]
            .value_counts()
            .to_dict()
            if "aureus_signal" in analysed_data.columns
            else "N/A"
        )
    )

    print()

    print("==============================================")
    print("             BACKTEST COMPLETE")
    print("==============================================")


if __name__ == "__main__":

    main()
