/*
============================================================
AUREUS AI — RISK ENGINE (STOP LOSS / TAKE PROFIT) v1
============================================================

PURPOSE
-------
Calculate a concrete stop-loss, take-profit, and resulting
risk/reward ratio for a candidate produced by
entryZoneEngine.js.

LOGIC
-----
Stop loss:
    Placed just beyond the order block / sweep extreme,
    with a small ATR-based buffer so ordinary noise
    doesn't stop the trade out prematurely.

Take profit:
    Targets the nearest OPPOSING liquidity pool from
    liquidityEngine.js — i.e. where resting liquidity
    actually is, not an arbitrary distance.

IMPORTANT
---------
This engine does not decide whether to take the trade.
It only calculates the numbers. decisionEngine.js still
makes the final call, including rejecting anything below
the minimum 1:2 risk/reward.

FIELD NAMES — matched to liquidityEngine.js output:
    Liquidity pools (from buildLiquidityMap /
    liquidityMap.buySideLiquidity / sellSideLiquidity):
        pool.side  -> "BUY_SIDE" | "SELL_SIDE"
        pool.price -> number

    Sweeps (from detectLiquiditySweeps):
        sweep.direction -> "BULLISH_POTENTIAL" | "BEARISH_POTENTIAL"
        sweep.liquidityLevel -> number (always present)
        sweep.high -> number (only on BUY_SIDE sweeps)
        sweep.low  -> number (only on SELL_SIDE sweeps)

============================================================
*/

// ============================================================
// 1. CONFIGURATION
// ============================================================

const RISK_ENGINE_CONFIG = {

    /*
        Stop-loss buffer beyond the order block / sweep
        extreme, expressed as a fraction of ATR.
    */
    stopBufferATR: 0.15,

    /*
        Number of candles used for ATR calculation.
        Matches the other engines for consistency.
    */
    atrLookback: 14,

    /*
        If no opposing liquidity pool can be found within
        this many candles' worth of price history, fall
        back to a fixed R multiple target instead of
        leaving takeProfit as null.
    */
    fallbackRewardMultiple: 2.0,
};

// ============================================================
// 2. HELPER — AVERAGE TRUE RANGE
// (duplicated intentionally — keeps this engine standalone
// and independently testable, same pattern as the others)
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
// 3. STOP LOSS CALCULATION
// ============================================================

/*
    candidate: one entry from getEntryZones()
    candles:   full OHLC array up to and including current candle
*/
function calculateStopLoss(candidate, candles) {

    const atr = calculateATR(candles, RISK_ENGINE_CONFIG.atrLookback);
    if (!atr) return null;

    const buffer = atr * RISK_ENGINE_CONFIG.stopBufferATR;
    const isBullish = candidate.direction === "bullish";

    // Prefer the order block extreme; fall back to the sweep
    // candle's extreme if no order block is attached.
    let structuralExtreme;

    if (candidate.orderBlocks.length > 0) {
        structuralExtreme = isBullish
            ? Math.min(...candidate.orderBlocks.map(ob => ob.low))
            : Math.max(...candidate.orderBlocks.map(ob => ob.high));
    } else if (candidate.sweep) {
        // Sell-side sweep (bullish setup) only has .low; buy-side
        // sweep (bearish setup) only has .high. liquidityLevel is
        // the safe fallback either way.
        structuralExtreme = isBullish
            ? (candidate.sweep.low ?? candidate.sweep.liquidityLevel)
            : (candidate.sweep.high ?? candidate.sweep.liquidityLevel);
    } else {
        return null; // nothing to anchor a stop to
    }

    return isBullish
        ? structuralExtreme - buffer
        : structuralExtreme + buffer;
}

// ============================================================
// 4. TAKE PROFIT CALCULATION
// ============================================================

/*
    liquidityPools: buySideLiquidity + sellSideLiquidity from
                    liquidityEngine.js's buildLiquidityMap() /
                    analyzeLiquidity().liquidityMap — NOT the
                    sweeps array, that's a different thing.
    entryPrice:     assumed entry (e.g. current close, or
                    order block edge — passed in by caller)
*/
function calculateTakeProfit(candidate, entryPrice, stopLoss, liquidityPools) {

    if (entryPrice === null || stopLoss === null) return null;

    const isBullish = candidate.direction === "bullish";
    const riskDistance = Math.abs(entryPrice - stopLoss);
    if (riskDistance <= 0) return null;

    // Opposing liquidity: buy-side pools above price for a
    // bullish trade, sell-side pools below price for bearish.
    const opposingPools = (liquidityPools || []).filter(pool => {
        if (isBullish) {
            return pool.side === "BUY_SIDE" && pool.price > entryPrice;
        }
        return pool.side === "SELL_SIDE" && pool.price < entryPrice;
    });

    let takeProfit;

    if (opposingPools.length > 0) {
        // Nearest opposing pool = most realistic target
        takeProfit = isBullish
            ? Math.min(...opposingPools.map(p => p.price))
            : Math.max(...opposingPools.map(p => p.price));
    } else {
        // No known liquidity target — fall back to fixed R multiple
        const fallbackDistance = riskDistance * RISK_ENGINE_CONFIG.fallbackRewardMultiple;
        takeProfit = isBullish
            ? entryPrice + fallbackDistance
            : entryPrice - fallbackDistance;
    }

    const rewardDistance = Math.abs(takeProfit - entryPrice);
    const riskReward = rewardDistance / riskDistance;

    return {
        takeProfit,
        riskReward,
        targetSource: opposingPools.length > 0 ? "liquidity_pool" : "fallback_multiple",
    };
}

// ============================================================
// 5. COMBINED — FULL RISK CALCULATION FOR ONE CANDIDATE
// ============================================================

/*
    Returns everything decisionEngine.js needs to plug into
    context.riskReward, plus the raw price levels for
    execution/logging later.
*/
function calculateRiskForCandidate(candidate, candles, liquidityPools, entryPrice) {

    const stopLoss = calculateStopLoss(candidate, candles);

    if (stopLoss === null) {
        return {
            stopLoss: null,
            takeProfit: null,
            riskReward: null,
            targetSource: null,
            valid: false,
            reason: "Could not calculate stop loss — no order block or sweep to anchor to",
        };
    }

    const tpResult = calculateTakeProfit(candidate, entryPrice, stopLoss, liquidityPools);

    if (!tpResult) {
        return {
            stopLoss,
            takeProfit: null,
            riskReward: null,
            targetSource: null,
            valid: false,
            reason: "Could not calculate take profit",
        };
    }

    return {
        stopLoss,
        takeProfit: tpResult.takeProfit,
        riskReward: tpResult.riskReward,
        targetSource: tpResult.targetSource,
        valid: true,
        reason: null,
    };
}

// ============================================================
// EXPORTS
// ============================================================

module.exports = {
    RISK_ENGINE_CONFIG,
    calculateATR,
    calculateStopLoss,
    calculateTakeProfit,
    calculateRiskForCandidate,
};
