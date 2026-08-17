"""Download real OHLC data from Twelve Data using only the Python standard library.

No Node/npm is required.

Example:
    python scripts/download_twelvedata.py --api-key YOUR_KEY --symbol EUR/USD \
        --interval 5min --output data/EURUSD_m5.csv --outputsize 5000

The exact historical depth available is controlled by the provider plan.  The
script does not bypass provider limits.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE = "https://api.twelvedata.com/time_series"


def fetch(symbol: str, interval: str, api_key: str, outputsize: int):
    params = {
        "symbol": symbol,
        "interval": interval,
        "outputsize": str(outputsize),
        "timezone": "UTC",
        "apikey": api_key,
    }
    url = BASE + "?" + urlencode(params)
    req = Request(url, headers={"User-Agent": "AUREUS-AI/3.0"})
    with urlopen(req, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if payload.get("status") == "error" or payload.get("code", 200) >= 400:
        raise RuntimeError(payload.get("message", "Twelve Data request failed"))
    values = payload.get("values")
    if not isinstance(values, list) or not values:
        raise RuntimeError(f"No candles returned for {symbol} {interval}")
    values.reverse()
    return values


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--symbol", required=True, help="Example: EUR/USD or XAU/USD")
    parser.add_argument("--interval", default="5min", choices=["1min", "5min", "15min", "30min", "45min", "1h", "2h", "4h", "8h", "1day", "1week", "1month"])
    parser.add_argument("--output", required=True)
    parser.add_argument("--outputsize", type=int, default=5000)
    args = parser.parse_args()

    values = fetch(args.symbol, args.interval, args.api_key, args.outputsize)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)

    fields = ["datetime", "open", "high", "low", "close", "volume"]
    with out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in values:
            writer.writerow({
                "datetime": row.get("datetime", ""),
                "open": row.get("open", ""),
                "high": row.get("high", ""),
                "low": row.get("low", ""),
                "close": row.get("close", ""),
                "volume": row.get("volume", "0"),
            })

    print(f"Downloaded {len(values)} {args.interval} candles for {args.symbol}")
    print(f"Saved to: {out.resolve()}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
