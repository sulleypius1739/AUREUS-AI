from pathlib import Path

import pandas as pd

from backtest.engine import BacktestEngine
from backtest.metrics import calculate_metrics


def print_section(title):

    print()
    print("=" * 54)
    print(title.center(54))
    print("=" * 54)


def safe_count(df, column, value=None):

    if column not in df.columns:
        return "N/A"

    if value is None:
        return len(df[column].dropna())

    return int(
        (df[column] == value).sum()
    )


def print_data_diagnostics(df):

    print_section("DATA")

    print("Candles:", len(df))

    if "Date" in df.columns:

        try:

            dates = pd.to_datetime(
                df["Date"],
                errors="coerce"
            )

            valid_dates = dates.dropna()

            if len(valid_dates) > 0:

                print(
                    "Start:",
                    valid_dates.iloc[0]
                )

                print(
                    "End:",
                    valid_dates.iloc[-1]
                )

        except Exception:

            pass

    print(
        "Columns:",
        list(df.columns)
    )


def print_structure_diagnostics(df):

    print_section("MARKET STRUCTURE")

    if "structure" not in df.columns:

        print(
            "Structure information: N/A"
        )

        return

    structure_counts = (
        df["structure"]
        .dropna()
        .value_counts()
    )

    for label in ["HH", "HL", "LH", "LL"]:

        print(
            f"{label}:",
            int(
                structure_counts.get(
                    label,
                    0
                )
            )
        )


def print_liquidity_diagnostics(df):

    print_section("LIQUIDITY")

    liquidity_columns = [

        (
            "Equal highs",
            "equal_high"
        ),

        (
            "Equal lows",
            "equal_low"
        ),

        (
            "Buy-side liquidity",
            "buy_side_liquidity"
        ),

        (
            "Sell-side liquidity",
            "sell_side_liquidity"
        ),

        (
            "Buy-side sweeps",
            "buy_side_sweep"
        ),

        (
            "Sell-side sweeps",
            "sell_side_sweep"
        )
    ]

    for label, column in liquidity_columns:

        if column not in df.columns:

            print(
                f"{label}: N/A"
            )

            continue

        print(
            f"{label}:",
            int(
                df[column]
                .fillna(False)
                .astype(bool)
                .sum()
            )
        )


def print_zone_diagnostics(df):

    print_section("ZONES")

    zone_columns = [

        (
            "Support",
            "support"
        ),

        (
            "Resistance",
            "resistance"
        ),

        (
            "Demand",
            "demand"
        ),

        (
            "Supply",
            "supply"
        ),

        (
            "Bullish order blocks",
            "bullish_order_block"
        ),

        (
            "Bearish order blocks",
            "bearish_order_block"
        ),

        (
            "Bullish FVGs",
            "bullish_fvg"
        ),

        (
            "Bearish FVGs",
            "bearish_fvg"
        ),

        (
            "Displacement",
            "displacement"
        )
    ]

    for label, column in zone_columns:

        if column not in df.columns:

            print(
                f"{label}: N/A"
            )

            continue

        print(
            f"{label}:",
            int(
                df[column]
                .fillna(False)
                .astype(bool)
                .sum()
            )
        )


def print_signal_diagnostics(df):

    print_section("SIGNALS")

    if "aureus_signal" not in df.columns:

        print(
            "Signals generated: N/A"
        )

        return

    signals = (
        df["aureus_signal"]
        .dropna()
    )

    # Remove common empty representations.

    signals = signals[
        ~signals.astype(str).str.lower().isin(
            [
                "",
                "none",
                "nan",
                "neutral",
                "no_signal",
                "hold"
            ]
        )
    ]

    print(
        "Signals generated:",
        len(signals)
    )

    if len(signals) == 0:

        print(
            "Signal breakdown: none"
        )

        return

    print()
    print("Signal breakdown:")

    counts = (
        signals
        .astype(str)
        .value_counts()
    )

    for signal, count in counts.items():

        print(
            f"  {signal}: {count}"
        )


def print_trade_diagnostics(
    trades,
    metrics
):

    print_section("TRADE PERFORMANCE")

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

    if len(trades) == 0:

        print()
        print(
            "No completed trades available "
            "for additional diagnostics."
        )

        return

    # ---------------------------------------------------------
    # Try to identify long/short trades.
    # ---------------------------------------------------------

    direction_column = None

    for column in [
        "direction",
        "side",
        "type",
        "signal"
    ]:

        if column in trades.columns:

            direction_column = column

            break

    if direction_column is not None:

        values = (
            trades[direction_column]
            .astype(str)
            .str.lower()
        )

        long_count = values.isin(
            [
                "long",
                "buy",
                "bullish"
            ]
        ).sum()

        short_count = values.isin(
            [
                "short",
                "sell",
                "bearish"
            ]
        ).sum()

        print(
            "Long trades:",
            int(long_count)
        )

        print(
            "Short trades:",
            int(short_count)
        )


def print_trade_sample(trades):

    print_section("TRADE SAMPLE")

    if len(trades) == 0:

        print(
            "No trades available."
        )

        return

    # Show only the first five trades so the terminal
    # remains readable.

    print(
        trades.head(5).to_string(
            index=False
        )
    )


def main():

    print()

    print("=" * 54)
    print(
        "AUREUS AI".center(54)
    )
    print(
        "HISTORICAL BACKTEST".center(54)
    )
    print("=" * 54)

    print()

    file_path = input(
        "Enter CSV file path: "
    ).strip()

    file_path = Path(file_path)

    if not file_path.exists():

        print()
        print(
            "ERROR: File does not exist."
        )

        print(
            file_path
        )

        return

    try:

        df = pd.read_csv(
            file_path
        )

    except Exception as error:

        print()
        print_section(
            "BACKTEST ERROR"
        )

        print(
            "Could not read CSV."
        )

        print(error)

        return

    print()

    print(
        "Data loaded successfully."
    )

    print_data_diagnostics(df)

    # =========================================================
    # ENGINE
    # =========================================================

    engine = BacktestEngine(

        starting_balance=10000,

        risk_percent=1.0,

        minimum_rr=2.0,

        minimum_score=3
    )

    # =========================================================
    # RUN BACKTEST
    # =========================================================

    try:

        trades, analysed_data, bias = (
            engine.run(df)
        )

    except Exception as error:

        print_section(
            "BACKTEST ERROR"
        )

        print(
            type(error).__name__ + ":"
        )

        print(error)

        return

    # =========================================================
    # METRICS
    # =========================================================

    try:

        metrics = calculate_metrics(
            trades
        )

    except Exception as error:

        print_section(
            "METRICS ERROR"
        )

        print(error)

        return

    # =========================================================
    # RESULTS
    # =========================================================

    print_section(
        "AUREUS RESULTS"
    )

    print(
        "Structural bias:",
        bias
    )

    print_trade_diagnostics(
        trades,
        metrics
    )

    # =========================================================
    # DIAGNOSTICS
    # =========================================================

    print_data_diagnostics(
        analysed_data
    )

    print_structure_diagnostics(
        analysed_data
    )

    print_liquidity_diagnostics(
        analysed_data
    )

    print_zone_diagnostics(
        analysed_data
    )

    print_signal_diagnostics(
        analysed_data
    )

    # =========================================================
    # SAMPLE
    # =========================================================

    print_trade_sample(
        trades
    )

    # =========================================================
    # COMPLETE
    # =========================================================

    print_section(
        "BACKTEST COMPLETE"
    )


if __name__ == "__main__":

    main()
