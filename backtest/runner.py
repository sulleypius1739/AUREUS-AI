import pandas as pd

from backtest.engine import BacktestEngine
from backtest.metrics import calculate_metrics


def run_backtest():

    print("\n")
    print("==============================")
    print("       AUREUS AI")
    print("     BACKTEST ENGINE")
    print("==============================")
    print("\n")

    file_path = input(
        "Enter historical CSV path: "
    )

    data = pd.read_csv(file_path)

    print("\nData loaded:")
    print(data.head())

    engine = BacktestEngine(
        starting_balance=10000,
        risk_per_trade=0.01
    )

    trades = engine.run(data)

    metrics = calculate_metrics(
        trades
    )

    print("\n")
    print("==============================")
    print("BACKTEST RESULTS")
    print("==============================")

    for key, value in metrics.items():

        print(
            f"{key}: {value}"
        )


if __name__ == "__main__":

    run_backtest()
