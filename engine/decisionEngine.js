/*
============================================================
AUREUS AI — DECISION ENGINE
============================================================

Purpose:
Determine whether a market setup satisfies the Aureus
technical, fundamental and risk requirements.

IMPORTANT:
This is the INITIAL DECISION FRAMEWORK.

The values passed into this engine are currently inputs.
They will eventually come from real market-data analysis
modules.

This engine does NOT execute trades.
It only produces a decision.

Possible decisions:

HIGH-CONVICTION BUY
VALID BUY
WATCHLIST
HIGH-CONVICTION SELL
VALID SELL
NO TRADE
============================================================
*/


// ============================================================
// 1. CONFIGURATION
// ============================================================

const AUREUS_CONFIG = {

    // Minimum score required for a valid setup
    minimumValidScore: 75,

    // Minimum score for high conviction
    highConvictionScore: 85,

    // Minimum acceptable risk/reward
    minimumRiskReward: 2.0,

    // Maximum number of conditions allowed to conflict
    maximumConflicts: 2,

    // Only trade during these sessions
    allowedSessions: ["LONDON", "NEWYORK"],

    // Hard cap regardless of how good setups look
    maxTradesPerDay: 2,

    // Fixed risk per trade as a fraction of account equity
    riskPerTrade: 0.005, // 0.5%

    /*
        TEMPORARY — remove once a real fundamentalEngine.js
        exists. Until then we mirror technical bias so setups
        aren't blocked forever by an unbuilt component.
    */
    fundamentalEngineIsPlaceholder: true
};


// ============================================================
// 2. SCORE WEIGHTS
// ============================================================

const SCORE_WEIGHTS = {

    higherTimeframeBias: 15,

    supportResistance: 10,

    supplyDemand: 10,

    orderBlock: 10,

    fairValueGap: 10,

    liquiditySweep: 15,

    marketStructure: 10,

    candleConfirmation: 5,

    fundamentalAlignment: 10,

    acceptableRiskReward: 5
};


// ============================================================
// 3. VALIDATE INPUT
// ============================================================

function validateSetup(setup) {

    if (!setup) {

        throw new Error(
            "Aureus AI: No setup data supplied."
        );
    }

    if (!setup.symbol) {

        throw new Error(
            "Aureus AI: Setup must contain a symbol."
        );
    }

    return true;
}


// ============================================================
// 4. CALCULATE TECHNICAL SCORE
// ============================================================

function calculateTechnicalScore(setup) {

    let score = 0;


    if (setup.higherTimeframeBias === true) {

        score += SCORE_WEIGHTS.higherTimeframeBias;

    }


    if (setup.supportResistance === true) {

        score += SCORE_WEIGHTS.supportResistance;

    }


    if (setup.supplyDemand === true) {

        score += SCORE_WEIGHTS.supplyDemand;

    }


    if (setup.orderBlock === true) {

        score += SCORE_WEIGHTS.orderBlock;

    }


    if (setup.fairValueGap === true) {

        score += SCORE_WEIGHTS.fairValueGap;

    }


    if (setup.liquiditySweep === true) {

        score += SCORE_WEIGHTS.liquiditySweep;

    }


    if (setup.marketStructure === true) {

        score += SCORE_WEIGHTS.marketStructure;

    }


    if (setup.candleConfirmation === true) {

        score += SCORE_WEIGHTS.candleConfirmation;

    }


    return score;
}


// ============================================================
// 5. FUNDAMENTAL SCORE
// ============================================================

function calculateFundamentalScore(setup) {

    if (setup.fundamentalAlignment === true) {

        return SCORE_WEIGHTS.fundamentalAlignment;

    }

    return 0;
}


// ============================================================
// 6. RISK / REWARD SCORE
// ============================================================

function calculateRiskScore(setup) {

    if (
        typeof setup.riskReward !== "number"
    ) {

        return 0;
    }


    if (
        setup.riskReward >=
        AUREUS_CONFIG.minimumRiskReward
    ) {

        return SCORE_WEIGHTS.acceptableRiskReward;

    }


    return 0;
}


// ============================================================
// 7. DETERMINE MARKET DIRECTION
// ============================================================

function determineDirection(setup) {

    const technicalBias =
        setup.technicalBias || "NEUTRAL";

    const fundamentalBias =
        setup.fundamentalBias || "NEUTRAL";


    /*
        We want technical and fundamental direction
        to agree whenever possible.
    */


    if (
        technicalBias === "BULLISH" &&
        fundamentalBias === "BULLISH"
    ) {

        return "BUY";
    }


    if (
        technicalBias === "BEARISH" &&
        fundamentalBias === "BEARISH"
    ) {

        return "SELL";
    }


    /*
        If they disagree, the setup is conflicted.
    */

    return "CONFLICT";
}


// ============================================================
// 8. COUNT CONFLICTS
// ============================================================

function countConflicts(setup) {

    let conflicts = 0;


    /*
        Technical vs fundamental
    */

    if (
        setup.technicalBias &&
        setup.fundamentalBias &&
        setup.technicalBias !== "NEUTRAL" &&
        setup.fundamentalBias !== "NEUTRAL" &&
        setup.technicalBias !== setup.fundamentalBias
    ) {

        conflicts++;
    }


    /*
        News environment
    */

    if (
        setup.newsRisk === "HIGH"
    ) {

        conflicts++;
    }


    /*
        Risk/reward
    */

    if (
        typeof setup.riskReward === "number" &&
        setup.riskReward 
        AUREUS_CONFIG.minimumRiskReward
    ) {

        conflicts++;
    }


    return conflicts;
}


// ============================================================
// 9. DETERMINE FINAL SIGNAL
// ============================================================

function determineSignal(
    score,
    direction,
    conflicts
) {


    /*
        Too many conflicts = NO TRADE
    */

    if (
        conflicts >
        AUREUS_CONFIG.maximumConflicts
    ) {

        return "NO TRADE";
    }


    /*
        Technical and fundamental direction disagree.
    */

    if (
        direction === "CONFLICT"
    ) {

        return "NO TRADE";
    }


    /*
        Score too low.
    */

    if (
        score 
        60
    ) {

        return "NO TRADE";
    }


    /*
        Moderate setup.
    */

    if (
        score 
        AUREUS_CONFIG.minimumValidScore
    ) {

        return "WATCHLIST";
    }


    /*
        Strong setup.
    */

    if (
        score >=
        AUREUS_CONFIG.highConvictionScore
    ) {

        return `HIGH-CONVICTION ${direction}`;
    }


    /*
        Valid setup.
    */

    return `VALID ${direction}`;
}


// ============================================================
// 9B. SESSION AND TRADE-COUNT GATES
// ============================================================

function isSessionAllowed(session) {
    return AUREUS_CONFIG.allowedSessions.includes(session);
}

function isUnderDailyTradeLimit(tradesTakenToday) {
    return tradesTakenToday < AUREUS_CONFIG.maxTradesPerDay;
}


// ============================================================
// 9C. BRIDGE FROM entryZoneEngine.js CANDIDATES
// ============================================================

/*
    Converts a candidate from getEntryZones() into the
    "setup" shape analyzeSetup() expects.

    context = {
        symbol: "XAUUSD",
        session: "LONDON" | "NEWYORK" | "ASIA" | "OTHER",
        tradesTakenToday: 0,
        riskResult: <output of riskEngine.calculateRiskForCandidate()>,
        newsRisk: "LOW" | "HIGH"
    }
*/
function buildSetupFromEntryZone(candidate, context) {

    const technicalBias =
        candidate.direction === "bullish" ? "BULLISH" : "BEARISH";

    // TEMPORARY placeholder — see AUREUS_CONFIG note above
    const fundamentalBias = AUREUS_CONFIG.fundamentalEngineIsPlaceholder
        ? technicalBias
        : (context.fundamentalBias || "NEUTRAL");

    return {
        symbol: context.symbol,
        technicalBias,
        fundamentalBias,
        fundamentalAlignment: technicalBias === fundamentalBias,

        higherTimeframeBias: context.higherTimeframeBias === true,
        supportResistance: context.supportResistance === true,
        supplyDemand: context.supplyDemand === true,

        orderBlock: candidate.orderBlocks.length > 0,
        fairValueGap: candidate.fvgs.length > 0,
        liquiditySweep: true, // guaranteed by entryZoneEngine's linking logic
        marketStructure: true, // confirmed break guaranteed by entryZoneEngine

        candleConfirmation: context.candleConfirmation === true,

        riskReward: context.riskResult ? context.riskResult.riskReward : null,
        newsRisk: context.newsRisk || "LOW",

        // carried through for logging/debugging, not scored
        breakType: candidate.breakType,
        confluenceScore: candidate.confluenceScore,
    };
}

/*
    Full pipeline: entry zone candidate -> setup -> decision,
    with the hard session/trade-count gates applied on top
    of whatever analyzeSetup() decides.
*/
function evaluateEntryZone(candidate, context) {

    if (!isSessionAllowed(context.session)) {
        return {
            symbol: context.symbol,
            signal: "NO TRADE",
            reason: `Outside allowed sessions (${context.session})`,
            valid: false,
        };
    }

    if (!isUnderDailyTradeLimit(context.tradesTakenToday)) {
        return {
            symbol: context.symbol,
            signal: "NO TRADE",
            reason: "Daily trade limit reached",
            valid: false,
        };
    }

    // Requires the caller to have already run calculateRiskForCandidate()
    // from riskEngine.js and attached the result as context.riskResult
    if (!context.riskResult || !context.riskResult.valid) {
        return {
            symbol: context.symbol,
            signal: "NO TRADE",
            reason: context.riskResult
                ? context.riskResult.reason
                : "No risk calculation provided",
            valid: false,
        };
    }

    const setup = buildSetupFromEntryZone(candidate, context);
    const result = analyzeSetup(setup);

    // Position sizing, only meaningful once riskReward is real
    result.riskPerTradePercent = AUREUS_CONFIG.riskPerTrade * 100;

    return result;
}


// ============================================================
// 10. MAIN DECISION FUNCTION
// ============================================================

function analyzeSetup(setup) {

    validateSetup(setup);


    /*
        Calculate individual components.
    */

    const technicalScore =
        calculateTechnicalScore(setup);


    const fundamentalScore =
        calculateFundamentalScore(setup);


    const riskScore =
        calculateRiskScore(setup);


    /*
        Total score.
    */

    const totalScore =
        technicalScore +
        fundamentalScore +
        riskScore;


    /*
        Determine direction.
    */

    const direction =
        determineDirection(setup);


    /*
        Count conflicts.
    */

    const conflicts =
        countConflicts(setup);


    /*
        Determine final decision.
    */

    const signal =
        determineSignal(
            totalScore,
            direction,
            conflicts
        );


    /*
        Return complete analysis.
    */

    return {

        symbol: setup.symbol,

        technicalBias:
            setup.technicalBias || "NEUTRAL",

        fundamentalBias:
            setup.fundamentalBias || "NEUTRAL",

        direction:

            direction === "CONFLICT"
                ? "NONE"
                : direction,

        technicalScore,

        fundamentalScore,

        riskScore,

        totalScore,

        conflicts,

        signal,

        valid:
            signal.includes("BUY") ||
            signal.includes("SELL"),

        riskReward:
            setup.riskReward || null,

        timestamp:
            new Date().toISOString()
    };
}


// ============================================================
// 11. EXPORT
// ============================================================

/*
    This allows the engine to be used by other Aureus
    modules later.

    Example future architecture:

    marketData
          ↓
    technicalEngine
          ↓
    fundamentalEngine
          ↓
    decisionEngine
          ↓
    signalEngine
          ↓
    dashboard
*/

if (typeof module !== "undefined") {

    module.exports = {

        analyzeSetup,

        calculateTechnicalScore,

        calculateFundamentalScore,

        calculateRiskScore,

        determineDirection,

        determineSignal,

        isSessionAllowed,

        isUnderDailyTradeLimit,

        buildSetupFromEntryZone,

        evaluateEntryZone

    };

}
