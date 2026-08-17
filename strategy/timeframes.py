"""AUREUS V3 multi-timeframe data preparation.

The source dataset is M5 candles. Higher timeframes are aggregated from the
same chronological M5 stream so the backtest never mixes future information.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

import numpy as np
import pandas as pd


TIMEFRAME_RULES: Dict[str, str] = {
    "10m": "10min",
    "15m": "15min",
    "1h": "1h",
    "4h": "4h",
    "1d": "1D",
}


@dataclass
class MultiTimeframeData:
    base: pd.DataFrame
    frames: Dict[str, pd.DataFrame]


def _find_time_column(df: pd.DataFrame) -> str:
    for name in ("Date", "date", "datetime", "timestamp", "time"):
        if name in df.columns:
            return name
    raise ValueError(
        "M5 data must contain Date/datetime/timestamp/time column"
    )


def normalize_m5(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize M5 OHLCV data and robustly detect epoch timestamps."""
    out = df.copy()
    out.columns = [str(c).strip().lower() for c in out.columns]
    time_col = _find_time_column(out)

    out = out.rename(
        columns={
            time_col: "timestamp",
            "tick_volume": "volume",
        }
    )

    required = ["timestamp", "open", "high", "low", "close"]
    missing = [c for c in required if c not in out.columns]
    if missing:
        raise ValueError("Missing M5 columns: " + ", ".join(missing))

    raw_time = out["timestamp"]
    if pd.api.types.is_numeric_dtype(raw_time):
        numeric = pd.to_numeric(raw_time, errors="coerce")
        sample = numeric.dropna()
        if sample.empty:
            out["timestamp"] = pd.to_datetime(
                raw_time, errors="coerce", utc=True
            )
        else:
            magnitude = float(sample.abs().median())
            if magnitude >= 1e14:
                unit = "ns"
            elif magnitude >= 1e11:
                unit = "ms"
            elif magnitude >= 1e9:
                unit = "s"
            else:
                unit = None
            if unit:
                out["timestamp"] = pd.to_datetime(
                    numeric, unit=unit, errors="coerce", utc=True
                )
            else:
                out["timestamp"] = pd.to_datetime(
                    raw_time, errors="coerce", utc=True
                )
    else:
        out["timestamp"] = pd.to_datetime(
            raw_time, errors="coerce", utc=True
        )

    for col in ("open", "high", "low", "close"):
        out[col] = pd.to_numeric(out[col], errors="coerce")

    if "volume" not in out.columns:
        out["volume"] = 0.0
    out["volume"] = pd.to_numeric(
        out["volume"], errors="coerce"
    ).fillna(0.0)

    out = (
        out.dropna(subset=required)
        .sort_values("timestamp")
        .drop_duplicates("timestamp")
    )

    out["bar_close_time"] = (
        out["timestamp"] + pd.Timedelta(minutes=5)
    )
    return out.reset_index(drop=True)


def resample_ohlcv(m5: pd.DataFrame, rule: str) -> pd.DataFrame:
    base = m5.set_index("timestamp")
    agg = base[["open", "high", "low", "close", "volume"]].resample(
        rule,
        label="right",
        closed="right",
        origin="epoch",
    ).agg(
        {
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum",
        }
    )
    agg = agg.dropna(
        subset=["open", "high", "low", "close"]
    ).reset_index()
    agg["bar_close_time"] = agg["timestamp"]
    agg["source_timeframe"] = rule
    return agg.reset_index(drop=True)


def build_mtf_data(df: pd.DataFrame) -> MultiTimeframeData:
    base = normalize_m5(df)
    frames = {
        name: resample_ohlcv(base, rule)
        for name, rule in TIMEFRAME_RULES.items()
    }
    return MultiTimeframeData(base=base, frames=frames)


def asof_row(frame: pd.DataFrame, timestamp: pd.Timestamp):
    """Return latest fully-closed row at or before timestamp."""
    if frame.empty:
        return None
    ts = pd.Timestamp(timestamp)
    pos = frame["bar_close_time"].searchsorted(ts, side="right") - 1
    if pos < 0:
        return None
    return frame.iloc[int(pos)]
