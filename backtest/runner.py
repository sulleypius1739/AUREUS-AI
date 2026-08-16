from pathlib import Path

import pandas as pd

from backtest.engine import BacktestEngine
from backtest.metrics import calculate_metrics


# =========================================================
# DISPLAY HELPERS
# =========================================================

def print_section(title):

    print()
    print("=" * 54)
    print(title.center(54))
    print("=" * 54)


# =========================================================
# DATA DIAGNOSTICS
# =========================================================

def print_data_diagnostics(df):

    print_section("DATA")

    print(
        "Candles:",
        len(df)
    )

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


# =========================================================
# MARKET STRUCTURE DIAGNOSTICS
# =========================================================

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

    for label in [
        "HH",
        "HL",
        "LH",
        "LL"
    ]:

        print(
            f"{label}:",
            int(
                structure_counts.get(
                    label,
                    0
                )
            )
        )


# =========================================================
# LIQUIDITY DIAGNOSTICS
# =========================================================

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

        values = (
            df[column]
            .fillna(False)
            .astype(bool)
        )

        print(
            f"{label}:",
            int(values.sum())
        )


# =========================================================
# ZONE DIAGNOSTICS
# =========================================================

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

        values = (
            df[column]
            .fillna(False)
            .astype(bool)
        )

        print(
            f"{label}:",
            int(values.sum())
        )


# =========================================================
# SIGNAL DIAGNOSTICS
# =========================================================

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

    # Remove empty / neutral values.

    signals = signals[
        ~signals
        .astype(str)
        .str.lower()
        .isin(
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

    print(
        "Signal breakdown:"
    )

    counts = (
        signals
        .astype(str)
        .value_counts()
    )

    for signal, count in counts.items():

        print(
            f"  {signal}: {count}"
        )


# =========================================================
# TRADE DIAGNOSTICS
# =========================================================

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

    # ---------------------------------------------------------
    # No trades
    # ---------------------------------------------------------

    if not trades:

        print()

        print(
            "No completed trades available "
            "for additional diagnostics."
        )

        return

    # ---------------------------------------------------------
    # Convert list of trade dictionaries into DataFrame
    # ---------------------------------------------------------

    try:

        trade_df = pd.DataFrame(
            trades
        )

    except Exception as error:

        print()

        print(
            "Could not convert trades "
            "to DataFrame:"
        )

        print(error)

        return

    if trade_df.empty:

        print()

        print(
            "No completed trades available."
        )

        return

    # ---------------------------------------------------------
    # Show available trade fields
    # ---------------------------------------------------------

    print()

    print(
        "Trade fields:",
        list(trade_df.columns)
    )

    # ---------------------------------------------------------
    # Trade direction
    # ---------------------------------------------------------

    direction_column = None

    for column in [
        "direction",
        "side",
        "type",
        "signal"
    ]:

        if column in trade_df.columns:

            direction_column = column

            break

    if direction_column is not None:

        values = (
            trade_df[
                direction_column
            ]
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

    else:

        print(
            "Trade direction: N/A"
        )

    # ---------------------------------------------------------
    # R statistics
    # ---------------------------------------------------------

    result_column = None

    for column in [
        "R",
        "r",
        "result_R",
        "profit_R",
        "pnl_R"
    ]:

        if column in trade_df.columns:

            result_column = column

            break

    if result_column is not None:

        numeric_results = pd.to_numeric(
            trade_df[
                result_column
            ],
            errors="coerce"
        ).dropna()

        if len(numeric_results) > 0:

            print(
                "Average R:",
                round(
                    numeric_results.mean(),
                    3
                )
            )

            print(
                "Best trade (R):",
                round(
                    numeric_results.max(),
                    3
                )
            )

            print(
                "Worst trade (R):",
                round(
                    numeric_results.min(),
                    3
                )
            )

    else:

        print(
            "R-result field: N/A"
        )


# =========================================================
# TRADE SAMPLE
# =========================================================

def print_trade_sample(trades):

    print_section("TRADE SAMPLE")

    if not trades:

        print(
            "No trades available."
        )

        return

    try:

        trade_df = pd.DataFrame(
            trades
        )

    except Exception as error:

        print(
            "Could not display trade sample:"
        )

        print(error)

        return

    if trade_df.empty:

        print(
            "No trades available."
        )

        return

    print(
        trade_df
        .head(5)
        .to_string(
            index=False
        )
    )


# =========================================================
# MAIN
# =========================================================

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

    # =====================================================
    # FILE INPUT
    # =====================================================

    file_path = input(
        "Enter CSV file path: "
    ).strip()

    file_path = Path(
        file_path
    )

    if not file_path.exists():

        print()

        print_section(
            "BACKTEST ERROR"
        )

        print(
            "ERROR: File does not exist."
        )

        print(
            file_path
        )

        return

    # =====================================================
    # LOAD DATA
    # =====================================================

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

        print(
            error
        )

        return

    print()

    print(
        "Data loaded successfully."
    )

    print_data_diagnostics(
        df
    )

    # =====================================================
    # CREATE ENGINE
    # =====================================================

    engine = BacktestEngine(

        starting_balance=10000,

        risk_percent=1.0,

        minimum_rr=2.0,

        minimum_score=3
    )

    # =====================================================
    # RUN BACKTEST
    # =====================================================

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

        print(
            error
        )

        return

    # =====================================================
    # CALCULATE METRICS
    # =====================================================

    try:

        metrics = calculate_metrics(
            trades
        )

    except Exception as error:

        print_section(
            "METRICS ERROR"
        )

        print(
            error
        )

        return

    # =====================================================
    # MAIN RESULTS
    # =====================================================

    print_section(
        "AUREUS RESULTS"
    )

    print(
        "Structural bias:",
        bias
    )

    # =====================================================
    # TRADE PERFORMANCE
    # =====================================================

    print_trade_diagnostics(
        trades,
        metrics
    )

    # =====================================================
    # MARKET STRUCTURE
    # =====================================================

    print_structure_diagnostics(
        analysed_data
    )

    # =====================================================
    # LIQUIDITY
    # =====================================================

    print_liquidity_diagnostics(
        analysed_data
    )

    # =====================================================
    # ZONES
    # =====================================================

    print_zone_diagnostics(
        analysed_data
    )

    # =====================================================
    # SIGNALS
    # =====================================================

    print_signal_diagnostics(
        analysed_data
    )

    # =====================================================
    # SAMPLE TRADES
    # =====================================================

    print_trade_sample(
        trades
    )

    # =====================================================
    # COMPLETE
    # =====================================================

    print_section(
        "BACKTEST COMPLETE"
    )


# =========================================================
# PROGRAM ENTRY
# =========================================================

if __name__ == "__main__":

    main()
