/*
============================================================
AUREUS AI — ENTRY ZONE ENGINE v1
============================================================

PURPOSE
-------
Combine the outputs of:

    liquidityEngine.js       (sweeps)
    structureBreakEngine.js  (BOS / CHOCH / displacement)
    orderBlockEngine.js      (order blocks / FVGs)

into a single, ranked list of candidate entry zones.

SEQUENCE REQUIRED
------------------
    Liquidity sweep
        ↓
    Displacement (already required inside structureBreakEngine)
        ↓
    Confirmed structure shift (BOS or CHOCH)
        ↓
    Order block / FVG located near the shift
        ↓
    CANDIDATE ENTRY ZONE

IMPORTANT
---------
This engine does NOT decide whether to trade. It only
assembles a candidate. Session filtering, risk sizing,
and the 1:2 minimum R:R rule belong in decisionEngine.js,
which will consume this engine's output.

No lookahead: a candidate is only ever built from a sweep,
break, and order block that all occurred at or before the
current point in the replay.

============================================================
*/

// ============================================================
// 1. CONFIGURATION
// ============================================================

const ENTRY_ZONE_CONFIG = {

    /*
        Maximum number of candles allowed between the
        liquidity sweep and the structural break that
        followed it. Prevents linking unrelated events
        that happen to occur near each other on the chart.
    */
    maxCandlesSweepToBreak: 6,

    /*
        Maximum number of candles allowed between the
        confirmed structural break and the order block /
        FVG we treat as its "location."
    */
    maxCandlesBreakToZone: 10,

    /*
        Minimum confluence score required for a candidate
        to be returned at all. Raised later once we start
        backtesting and know what actually matters.
    */
    minimumScore: 2,

};

// ============================================================
// 2. CORE LINKING LOGIC
// ============================================================

/*
    sweeps:      output from liquidityEngine.js
    breaks:      output from structureBreakEngine.js
    orderBlocks: output from orderBlockEngine.js (findOrderBlocks)
    fvgs:        output from orderBlockEngine.js (findFairValueGaps)
*/
function getEntryZones(sweeps, breaks, orderBlocks, fvgs) {
    const candidates = [];

    for (const brk of breaks) {

        // ----------------------------------------------------
        // Step 1: find a sweep that plausibly caused this break
        // ----------------------------------------------------
        const relatedSweep = sweeps.find(sw => {
            const distance = brk.candleIndex - sw.candleIndex;
            return (
                distance >= 0 &&
                distance <= ENTRY_ZONE_CONFIG.maxCandlesSweepToBreak &&
                sw.direction === brk.direction
            );
        });

        if (!relatedSweep) continue; // no sweep behind this break — skip

        // ----------------------------------------------------
        // Step 2: find order block(s) tied to this exact break
        // ----------------------------------------------------
        const relatedOBs = orderBlocks.filter(
            ob => ob.relatedBreakIndex === brk.candleIndex
        );

        // ----------------------------------------------------
        // Step 3: find FVG(s) formed near the break, same direction
        // ----------------------------------------------------
        const relatedFVGs = fvgs.filter(fvg => {
            const distance = brk.candleIndex - fvg.candleIndex;
            const sameDirection =
                (brk.direction === "bullish" && fvg.type === "bullish_fvg") ||
                (brk.direction === "bearish" && fvg.type === "bearish_fvg");
            return (
                distance >= 0 &&
                distance <= ENTRY_ZONE_CONFIG.maxCandlesBreakToZone &&
                sameDirection
            );
        });

        if (relatedOBs.length === 0 && relatedFVGs.length === 0) continue;

        // ----------------------------------------------------
        // Step 4: score the confluence
        // ----------------------------------------------------
        let score = 0;
        score += 1; // sweep present
        score += 1; // confirmed structural break present
        if (relatedOBs.length > 0) score += 1;
        if (relatedFVGs.length > 0) score += 1;
        if (brk.type === "CHOCH") score += 1; // shift > continuation, weighted higher

        if (score < ENTRY_ZONE_CONFIG.minimumScore) continue;

        candidates.push({
            direction: brk.direction,
            breakType: brk.type,          // "BOS" or "CHOCH"
            breakCandleIndex: brk.candleIndex,
            sweep: relatedSweep,
            orderBlocks: relatedOBs,
            fvgs: relatedFVGs,
            confluenceScore: score,
            status: "candidate",          // decisionEngine.js will re-evaluate this
        });
    }

    return candidates;
}

// ============================================================
// EXPORTS
// ============================================================

module.exports = {
    ENTRY_ZONE_CONFIG,
    getEntryZones,
};
