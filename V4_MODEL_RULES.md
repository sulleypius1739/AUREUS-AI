# AUREUS V4 — A+ Market Mechanics (One Setup Only)

V4 is intentionally simple. It implements one mechanical setup from the supplied market-mechanics transcript and does not combine multiple independent entry systems.

## Core sequence

1. **4H direction**
   - Bullish or bearish higher-timeframe order flow.
   - Daily remains context-only in V4.

2. **1H high-priority POI**
   - Use a fresh, pro-trend point of interest.
   - V4 uses POI only as the zone model; order-block and FVG entries are not separate models.
   - A zone is consumed on its first trade opportunity.

3. **15M internal market shift**
   - Bullish setup: a bullish CHOCH on 15M after bearish internal pullback.
   - Bearish setup: a bearish CHOCH on 15M after bullish internal pullback.

4. **15M liquidity sweep**
   - Bullish setup: sell-side sweep after the internal bullish shift.
   - Bearish setup: buy-side sweep after the internal bearish shift.

5. **10M entry confirmation**
   - Same-direction 10M CHOCH.
   - Price must be inside the aligned 1H POI.

6. **M5 execution**
   - Enter at the next M5 candle open.
   - Stop sits just outside the POI.
   - Target is the nearest available 1H structural target in the trade direction.
   - Minimum planned RR is 2R.

## Deliberately excluded from V4

- Separate FVG entry model
- Separate order-block entry model
- Double-zone breakout
- Premium/discount as a trigger
- Large score/confluence stacks
- News/session filters
- Multiple simultaneous setup types
- Automatic broker execution

## Research workflow

V4 is the baseline. After the first backtest, only one change should be introduced at a time. Examples:

- change the internal timeframe;
- change POI definition;
- change the sweep lookback;
- change the target rule;
- add a single session filter.

Each change must be backtested against the same dataset and compared using trade count, win rate, profit factor, expectancy, net R and drawdown.
