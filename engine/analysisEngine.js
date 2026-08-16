/*
============================================================
AUREUS AI — ANALYSIS ENGINE v1
============================================================

PURPOSE
-------
Connect the individual Aureus engines into one analysis.

PIPELINE
--------
Candles
   ↓
Market Structure
   ↓
Structure Breaks
   ↓
Liquidity
   ↓
Order Blocks
   ↓
Fair Value Gaps
   ↓
Candidate Setup
   ↓
Risk
   ↓
Aureus Score
   ↓
BUY / SELL / WATCH / NO TRADE

IMPORTANT
---------
This engine does NOT place trades.

It only analyzes historical/current OHLC data.

Designed so the same logic can later be used by
the backtester.

============================================================
*/


// ============================================================
// 1. LOAD ENGINES
// ============================================================

const technicalEngine =
    typeof require !== "undefined"
        ? require("./technicalEngine")
        : null;

const structureBreakEngine =
    typeof require !== "undefined"
        ? require("./structureBreakEngine")
        : null;

const liquidityEngine =
    typeof require !== "undefined"
        ? require("./liquidityEngine")
        : null;

const orderBlockEngine =
    typeof require !== "undefined"
        ? require("./orderBlockEngine")
        : null;

const riskEngine =
    typeof require !== "undefined"
        ? require("./riskEngine")
        : null;


// ============================================================
// 2. CONFIGURATION
// ============================================================

const ANALYSIS_CONFIG = {

    minimumScore: 75,

    highConvictionScore: 85,

    minimumRiskReward: 2,

    requireLiquiditySweep: true,

    requireStructureConfirmation: true,

    requireLocation: true

};


// ============================================================
// 3. VALIDATE CANDLES
// ============================================================

function validateCandles(candles) {

    if (!Array.isArray(candles)) {

        throw new Error(
            "Aureus Analysis Engine: candles must be an array."
        );

    }

    if (candles.length < 20) {

        throw new Error(
            "Aureus Analysis Engine: at least 20 candles are required."
        );

    }

    for (const candle of candles) {

        if (
            typeof candle.open !== "number" ||
            typeof candle.high !== "number" ||
            typeof candle.low !== "number" ||
            typeof candle.close !== "number"
        ) {

            throw new Error(
                "Invalid OHLC candle."
            );

        }

    }

}


// ============================================================
// 4. GET LATEST STRUCTURE
// ============================================================

function getLatestStructure(
    structureAnalysis
) {

    if (!structureAnalysis) {

        return "NEUTRAL";

    }

    return (
        structureAnalysis.currentStructure ||
        "NEUTRAL"
    );

}


// ============================================================
// 5. GET MOST RECENT BREAK
// ============================================================

function getLatestBreak(
    breaks,
    latestCandleIndex
) {

    if (!Array.isArray(breaks)) {

        return null;

    }

    const validBreaks =
        breaks.filter(
            brk =>
                brk.candleIndex <=
                latestCandleIndex
        );

    if (
        validBreaks.length === 0
    ) {

        return null;

    }

    return validBreaks[
        validBreaks.length - 1
    ];

}


// ============================================================
// 6. GET RECENT SWEEP
// ============================================================

function getRecentSweep(
    sweeps,
    latestCandleIndex
) {

    if (!Array.isArray(sweeps)) {

        return null;

    }

    const recent =
        sweeps.filter(
            sweep =>
                sweep.candleIndex <=
                latestCandleIndex
        );

    if (
        recent.length === 0
    ) {

        return null;

    }

    return recent[
        recent.length - 1
    ];

}


// ============================================================
// 7. GET RELEVANT ORDER BLOCK
// ============================================================

function getRelevantOrderBlock(
    orderBlocks,
    direction
) {

    if (!Array.isArray(orderBlocks)) {

        return null;

    }

    const desiredType =
        direction === "BULLISH"
            ? "bullish_ob"
            : "bearish_ob";

    const candidates =
        orderBlocks.filter(
            ob =>
                ob.type === desiredType &&
                !ob.invalidated
        );

    if (
        candidates.length === 0
    ) {

        return null;

    }

    return candidates[
        candidates.length - 1
    ];

}


// ============================================================
// 8. GET RELEVANT FVG
// ============================================================

function getRelevantFVG(
    fvgs,
    direction
) {

    if (!Array.isArray(fvgs)) {

        return null;

    }

    const desiredType =
        direction === "BULLISH"
            ? "bullish_fvg"
            : "bearish_fvg";

    const candidates =
        fvgs.filter(
            fvg =>
                fvg.type === desiredType &&
                !fvg.invalidated
        );

    if (
        candidates.length === 0
    ) {

        return null;

    }

    return candidates[
        candidates.length - 1
    ];

}


// ============================================================
// 9. SCORE SETUP
// ============================================================

function calculateAureusScore(
    setup
) {

    let score = 0;

    const reasons = [];


    // Higher timeframe / structure bias
    if (
        setup.structure ===
        setup.direction
    ) {

        score += 20;

        reasons.push(
            "Structure aligns with direction."
        );

    }


    // Structure break
    if (
        setup.structureBreak
    ) {

        score += 15;

        reasons.push(
            "Confirmed structure break."
        );

    }


    // Liquidity sweep
    if (
        setup.liquiditySweep
    ) {

        score += 20;

        reasons.push(
            "Liquidity sweep detected."
        );

    }


    // Order block
    if (
        setup.orderBlock
    ) {

        score += 10;

        reasons.push(
            "Relevant order block detected."
        );

    }


    // FVG
    if (
        setup.fvg
    ) {

        score += 10;

        reasons.push(
            "Relevant fair value gap detected."
        );

    }


    // Displacement
    if (
        setup.displacement
    ) {

        score += 10;

        reasons.push(
            "Displacement detected."
        );

    }


    // Risk reward
    if (
        setup.riskReward !== null &&
        setup.riskReward >=
        ANALYSIS_CONFIG.minimumRiskReward
    ) {

        score += 15;

        reasons.push(
            "Risk/reward meets minimum requirement."
        );

    }


    return {

        score,

        reasons

    };

}


// ============================================================
// 10. DETERMINE FINAL DECISION
// ============================================================

function determineDecision(
    setup
) {

    if (
        !setup.direction
    ) {

        return "NO TRADE";

    }


    if (
        ANALYSIS_CONFIG.requireLiquiditySweep &&
        !setup.liquiditySweep
    ) {

        return "WAIT";

    }


    if (
        ANALYSIS_CONFIG.requireStructureConfirmation &&
        !setup.structureBreak
    ) {

        return "WAIT";

    }


    if (
        ANALYSIS_CONFIG.requireLocation &&
        !setup.orderBlock &&
        !setup.fvg
    ) {

        return "WAIT";

    }


    if (
        setup.riskReward === null ||
        setup.riskReward <
        ANALYSIS_CONFIG.minimumRiskReward
    ) {

        return "NO TRADE";

    }


    if (
        setup.score >=
        ANALYSIS_CONFIG.highConvictionScore
    ) {

        return setup.direction ===
            "BULLISH"
            ? "BUY"
            : "SELL";

    }


    if (
        setup.score >=
        ANALYSIS_CONFIG.minimumScore
    ) {

        return setup.direction ===
            "BULLISH"
            ? "BUY"
            : "SELL";

    }


    return "WAIT";

}


// ============================================================
// 11. ANALYZE ONE MARKET
// ============================================================

function analyzeMarket(
    candles,
    options = {}
) {

    validateCandles(
        candles
    );


    if (
        !technicalEngine ||
        !structureBreakEngine ||
        !liquidityEngine ||
        !orderBlockEngine ||
        !riskEngine
    ) {

        throw new Error(
            "Aureus Analysis Engine requires Node/CommonJS engines."
        );

    }


    /*
        ========================================================
        STEP 1 — MARKET STRUCTURE
        ========================================================
    */

    const structureAnalysis =
        technicalEngine.analyzeMarketStructure(
            candles,
            options
        );


    const swings =
        structureAnalysis.swings;


    const structure =
        getLatestStructure(
            structureAnalysis
        );


    /*
        ========================================================
        STEP 2 — STRUCTURE BREAK
        ========================================================
    */

    const structureBreaks =
        structureBreakEngine.detectStructureBreaks(
            candles,
            swings
        );


    const latestIndex =
        candles.length - 1;


    const latestBreak =
        getLatestBreak(
            structureBreaks,
            latestIndex
        );


    /*
        ========================================================
        STEP 3 — LIQUIDITY
        ========================================================
    */

    const liquidityAnalysis =
        liquidityEngine.analyzeLiquidity(
            candles,
            swings
        );


    const latestSweep =
        getRecentSweep(
            liquidityAnalysis.sweeps,
            latestIndex
        );


    /*
        ========================================================
        STEP 4 — DETERMINE DIRECTION
        ========================================================
    */

    let direction = null;


    if (
        latestBreak &&
        latestBreak.direction ===
        "BULLISH"
    ) {

        direction = "BULLISH";

    }


    if (
        latestBreak &&
        latestBreak.direction ===
        "BEARISH"
    ) {

        direction = "BEARISH";

    }


    /*
        If there is no current break, use
        market structure as directional bias.
    */

    if (!direction) {

        if (
            structure ===
            "BULLISH"
        ) {

            direction =
                "BULLISH";

        }

        else if (
            structure ===
            "BEARISH"
        ) {

            direction =
                "BEARISH";

        }

    }


    /*
        ========================================================
        STEP 5 — ORDER BLOCKS
        ========================================================
    */

    const orderBlocks =
        latestBreak
            ? orderBlockEngine.findOrderBlocks(
                candles,
                structureBreaks
            )
            : [];


    const fairValueGaps =
        orderBlockEngine.findFairValueGaps(
            candles
        );


    const relevantOrderBlock =
        direction
            ? getRelevantOrderBlock(
                orderBlocks,
                direction
            )
            : null;


    const relevantFVG =
        direction
            ? getRelevantFVG(
                fairValueGaps,
                direction
            )
            : null;


    /*
        ========================================================
        STEP 6 — LIQUIDITY SWEEP
        ========================================================
    */

    let liquiditySweep =
        false;


    if (latestSweep && direction) {

        liquiditySweep =
            (
                direction ===
                "BULLISH" &&
                latestSweep.side ===
                "SELL_SIDE"
            ) ||
            (
                direction ===
                "BEARISH" &&
                latestSweep.side ===
                "BUY_SIDE"
            );

    }


    /*
        ========================================================
        STEP 7 — DISPLACEMENT
        ========================================================
    */

    const displacement =
        Boolean(
            latestBreak &&
            latestBreak.displacement &&
            latestBreak.displacement.isDisplacement
        );


    /*
        ========================================================
        STEP 8 — ENTRY
        ========================================================
    */

    const latestCandle =
        candles[
            candles.length - 1
        ];


    const entryPrice =
        options.entryPrice ||
        latestCandle.close;


    /*
        ========================================================
        STEP 9 — BUILD CANDIDATE
        ========================================================
    */

    const candidate = {

        direction,

        structure,

        structureBreak:
            Boolean(
                latestBreak
            ),

        liquiditySweep,

        orderBlock:
            Boolean(
                relevantOrderBlock
            ),

        fvg:
            Boolean(
                relevantFVG
            ),

        displacement,

        orderBlockData:
            relevantOrderBlock,

        fvgData:
            relevantFVG,

        latestBreak,

        latestSweep

    };


    /*
        ========================================================
        STEP 10 — RISK
        ========================================================
    */

    let risk = {

        stopLoss: null,

        takeProfit: null,

        riskReward: null,

        targetSource: null,

        valid: false

    };


    if (
        direction
    ) {

        risk =
            riskEngine.calculateRiskForCandidate(
                candidate,
                candles,
                liquidityAnalysis
                    .liquidityMap
                    .buySideLiquidity
                    .concat(
                        liquidityAnalysis
                            .liquidityMap
                            .sellSideLiquidity
                    ),
                entryPrice
            );

    }


    /*
        ========================================================
        STEP 11 — SCORE
        ========================================================
    */

    const scoredSetup =
        calculateAureusScore({

            ...candidate,

            riskReward:
                risk.riskReward

        });


    const finalSetup = {

        ...candidate,

        entry:
            entryPrice,

        stopLoss:
            risk.stopLoss,

        takeProfit:
            risk.takeProfit,

        riskReward:
            risk.riskReward,

        targetSource:
            risk.targetSource,

        riskValid:
            risk.valid,

        score:
            scoredSetup.score,

        scoreReasons:
            scoredSetup.reasons

    };


    /*
        ========================================================
        STEP 12 — FINAL DECISION
        ========================================================
    */

    const decision =
        determineDecision(
            finalSetup
        );


    return {

        symbol:
            options.symbol ||
            "UNKNOWN",

        timeframe:
            options.timeframe ||
            "UNKNOWN",

        currentPrice:
            latestCandle.close,

        structure,

        structureConfidence:
            structureAnalysis.currentConfidence,

        direction,

        latestBreak,

        latestSweep,

        orderBlock:
            relevantOrderBlock,

        fvg:
            relevantFVG,

        liquidity:
            liquidityAnalysis.liquidityMap,

        entry:
            risk.valid
                ? entryPrice
                : null,

        stopLoss:
            risk.stopLoss,

        takeProfit:
            risk.takeProfit,

        riskReward:
            risk.riskReward,

        score:
            scoredSetup.score,

        scoreReasons:
            scoredSetup.reasons,

        decision,

        validSetup:
            decision === "BUY" ||
            decision === "SELL"

    };

}


// ============================================================
// 12. EXPORTS
// ============================================================

if (
    typeof module !==
    "undefined"
) {

    module.exports = {

        ANALYSIS_CONFIG,

        validateCandles,

        calculateAureusScore,

        determineDecision,

        analyzeMarket

    };

}
