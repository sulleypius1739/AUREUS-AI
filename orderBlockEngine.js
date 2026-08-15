/*
============================================================
AUREUS AI — ORDER BLOCK + FAIR VALUE GAP ENGINE v1
============================================================

PURPOSE
-------
Identify entry-zone candidates after a structure break has
been confirmed by structureBreakEngine.js.

CURRENT DETECTIONS
-------------------
1. Bullish Order Block (last down-close candle before an
   up-move that causes a confirmed structural break)
2. Bearish Order Block (last up-close candle before a
   down-move that causes a confirmed structural break)
3. Fair Value Gap (3-candle imbalance, bullish/bearish)
4. Mitigation status (untested / tested / invalidated)

IMPORTANT
---------
An order block is NOT valid just because it's the last
opposite-colour candle before a move. It only becomes a
valid Aureus order block if the move that follows it
produced a CONFIRMED structural break (BOS or CHOCH),
matching what structureBreakEngine.js already detected.

This keeps the engines consistent with each other instead
of each one inventing its own definition of "significant."

============================================================
*/

// ============================================================
// 1. CONFIGURATION
// ============================================================

const ORDER_BLOCK_CONFIG = {

    /*
        How many candles forward we allow between the
        candidate order block candle and the confirmed
        structural break before we discard it as unrelated.
    */
    maxCandlesToBreak: 10,

    /*
        Minimum FVG size, expressed as a fraction of
        recent ATR. Filters out tiny, meaningless gaps.
    */
    minimumFVGSizeATR: 0.10,

    /*
        Number of candles used for ATR calculation.
        Matches liquidityEngine.js for consistency.
    */
    atrLookback: 14,

    /*
        Once price returns into an order block or FVG,
        how much of it must be touched to count as
        "tested" vs just wicking the edge.
    */
    mitigationThreshold: 0.5, // 50% into the zone

};

// ============================================================
// 2. HELPER — AVERAGE TRUE RANGE
// ============================================================

function calculateATR(candles, lookback) {
    if (candles.length < lookback + 1) return null;

    let trSum = 0;
    for (let i = candles.length - lookback; i < candles.length; i++) {
        const curr = candles[i];
        const prev = candles[i - 1];
        const tr = Math.max(
            curr.high - curr.low,
            Math.abs(curr.high - prev.close),
            Math.abs(curr.low - prev.close)
        );
        trSum += tr;
    }
    return trSum / lookback;
}

// ============================================================
// 3. ORDER BLOCK DETECTION
// ============================================================

/*
    confirmedBreaks: output array from structureBreakEngine.js
    candles: full OHLC array up to and including the break candle
*/
function findOrderBlocks(candles, confirmedBreaks) {
    const orderBlocks = [];

    for (const brk of confirmedBreaks) {
        const breakIndex = brk.candleIndex;
        const isBullishBreak = brk.direction === "bullish";

        // Search backward from the break candle for the last
        // opposite-colour candle within the allowed window.
        let obIndex = null;

        for (
            let i = breakIndex - 1;
            i >= Math.max(0, breakIndex - ORDER_BLOCK_CONFIG.maxCandlesToBreak);
            i--
        ) {
            const candle = candles[i];
            const isDownClose = candle.close < candle.open;
            const isUpClose = candle.close > candle.open;

            if (isBullishBreak && isDownClose) {
                obIndex = i;
                break;
            }
            if (!isBullishBreak && isUpClose) {
                obIndex = i;
                break;
            }
        }

        if (obIndex === null) continue; // no valid candidate found

        const obCandle = candles[obIndex];

        orderBlocks.push({
            type: isBullishBreak ? "bullish_ob" : "bearish_ob",
            candleIndex: obIndex,
            high: obCandle.high,
            low: obCandle.low,
            open: obCandle.open,
            close: obCandle.close,
            relatedBreakIndex: breakIndex,
            relatedBreakType: brk.type, // "BOS" or "CHOCH"
            mitigated: false,
            mitigationPercent: 0,
            invalidated: false,
        });
    }

    return orderBlocks;
}

// ============================================================
// 4. FAIR VALUE GAP DETECTION
// ============================================================

/*
    Classic 3-candle imbalance:
    Bullish FVG: candle[i-1].high < candle[i+1].low
    Bearish FVG: candle[i-1].low > candle[i+1].high
*/
function findFairValueGaps(candles) {
    const fvgs = [];
    const atr = calculateATR(candles, ORDER_BLOCK_CONFIG.atrLookback);
    if (!atr) return fvgs;

    const minSize = atr * ORDER_BLOCK_CONFIG.minimumFVGSizeATR;

    for (let i = 1; i < candles.length - 1; i++) {
        const prev = candles[i - 1];
        const next = candles[i + 1];

        // Bullish FVG
        if (prev.high < next.low) {
            const gapSize = next.low - prev.high;
            if (gapSize >= minSize) {
                fvgs.push({
                    type: "bullish_fvg",
                    candleIndex: i,
                    top: next.low,
                    bottom: prev.high,
                    gapSize,
                    mitigated: false,
                    mitigationPercent: 0,
                });
            }
        }

        // Bearish FVG
        if (prev.low > next.high) {
            const gapSize = prev.low - next.high;
            if (gapSize >= minSize) {
                fvgs.push({
                    type: "bearish_fvg",
                    candleIndex: i,
                    top: prev.low,
                    bottom: next.high,
                    gapSize,
                    mitigated: false,
                    mitigationPercent: 0,
                });
            }
        }
    }

    return fvgs;
}

// ============================================================
// 5. MITIGATION TRACKING (called forward, candle by candle —
//    no lookahead, this only ever looks at candles AFTER
//    the zone was formed)
// ============================================================

function updateMitigation(zone, candle) {
    const zoneHigh = zone.high !== undefined ? zone.high : zone.top;
    const zoneLow = zone.low !== undefined ? zone.low : zone.bottom;
    const zoneRange = zoneHigh - zoneLow;

    if (zoneRange <= 0) return zone;

    const isBullishZone = zone.type.includes("bullish");

    if (isBullishZone) {
        if (candle.low <= zoneLow) {
            zone.invalidated = true;
        } else if (candle.low < zoneHigh) {
            const penetration = (zoneHigh - candle.low) / zoneRange;
            zone.mitigationPercent = Math.max(zone.mitigationPercent, penetration);
            if (penetration >= ORDER_BLOCK_CONFIG.mitigationThreshold) {
                zone.mitigated = true;
            }
        }
    } else {
        if (candle.high >= zoneHigh) {
            zone.invalidated = true;
        } else if (candle.high > zoneLow) {
            const penetration = (candle.high - zoneLow) / zoneRange;
            zone.mitigationPercent = Math.max(zone.mitigationPercent, penetration);
            if (penetration >= ORDER_BLOCK_CONFIG.mitigationThreshold) {
                zone.mitigated = true;
            }
        }
    }

    return zone;
}

// ============================================================
// EXPORTS
// ============================================================

module.exports = {
    ORDER_BLOCK_CONFIG,
    calculateATR,
    findOrderBlocks,
    findFairValueGaps,
    updateMitigation,
};
