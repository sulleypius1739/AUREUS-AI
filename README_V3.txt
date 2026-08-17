AUREUS V3 — TRUE TOP-DOWN MTF + LIVE DATA

This build is based on the Smart Risk course framework collected during the redesign.

CORE TOP-DOWN LOGIC
-------------------
Daily: macro bias and major context
4H: directional confirmation + higher-timeframe context
1H: setup / POI / OB context
15M: primary entry confirmation
10M: refined entry confirmation
M5: execution clock

A lower timeframe is allowed to retrace against the higher-timeframe direction before reversing into alignment. The lower timeframe does not independently flip the Daily/4H directional bias.

HISTORICAL BACKTEST
-------------------
V3 requires real M5 candles. The old EURUSDh1.csv is not sufficient to reproduce the course's Daily -> 4H -> 1H -> 15M/10M workflow.

Run:
    python -m backtest.runner

Enter a real M5 CSV, e.g.:
    data\EURUSD_m5.csv

REAL MARKET PLATFORM
--------------------
The browser platform now includes a Twelve Data live-data connector. Enter your own Twelve Data API key in the Live Data panel.

The connector requests:
- latest prices
- Daily candles
- 4H candles
- 1H candles
- 15M candles
- 5M candles
- derives 10M from 5M

When the provider account permits WebSocket streaming, AUREUS uses it for live prices. If WebSocket access is unavailable, the platform falls back to REST price polling.

NO API KEY IS BUNDLED WITH THE PROJECT.

The live connector is data/analysis only and does not place trades.
