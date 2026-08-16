import pandas as pd

from backtest.engine import BacktestEngine
from backtest.metrics import calculate_metrics


def main():

    print()
    print("========================================")
    print("             AUREUS AI")
    print("        HISTORICAL BACKTEST")
    print("========================================")
    print()

    file_path = input(
        "Enter the path to your CSV file: "
    )

    try:

        df = pd.read_csv(
            file_path
        )

    except Exception as error:

        print()
        print("Could not load CSV.")
        print(error)

        return

    print()
    print("Data successfully loaded.")
    print()

    print("Rows:", len(df))

    print(
        "Columns:",
        list(df.columns)
    )

    print()

    engine = BacktestEngine(
        starting_balance=10000,
        risk_percent=1,
        minimum_rr=2
    )

    try:

        trades = engine.run(df)

    except Exception as error:

        print()
        print("BACKTEST ERROR")
        print(error)

        return

    metrics = calculate_metrics(
        trades
    )

    print()
    print("========================================")
    print("             RESULTS")
    print("========================================")

    for key, value in metrics.items():

        print(
            f"{key}: {value}"
        )

    print()
    print("Trades generated:", len(trades))


if __name__ == "__main__":

    main()
