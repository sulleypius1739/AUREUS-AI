/*
============================================================
AUREUS AI — TECHNICAL ENGINE v1
============================================================

PURPOSE
-------
Detect market structure from OHLC price data.

CURRENT VERSION DETECTS:

1. Confirmed swing highs
2. Confirmed swing lows
3. Higher Highs (HH)
4. Higher Lows (HL)
5. Lower Highs (LH)
6. Lower Lows (LL)
7. Bullish structure
8. Bearish structure
9. Neutral / ranging structure

DESIGN PRINCIPLES
-----------------
- Strict swing detection
- Configurable swing strength
- No look-ahead bias
- Works chronologically
- Does not use future information before it
  becomes available
- Suitable for future historical backtesting

IMPORTANT
---------
This engine does NOT place trades.

It only interprets price structure.
============================================================
*/


// ============================================================
// 1. CONFIGURATION
// ============================================================

const TECHNICAL_CONFIG = {

    /*
        Number of candles required on BOTH sides
        of a candidate swing.

        Example:

        swingStrength = 3

        means the candidate must have:

        3 candles to the left
        AND
        3 candles to the right

        with lower highs for a swing high,
        or higher lows for a swing low.
    */

    swingStrength: 3,


    /*
        Number of confirmed structural swings used
        when determining the current market structure.
    */

    structureLookback: 4,


    /*
        Minimum number of structural points required
        before declaring a directional structure.
    */

    minimumStructurePoints: 3,


    /*
        Whether equal highs/lows are treated as
        a separate condition instead of HH/LL.
    */

    allowEqualLevels: true,


    /*
        Floating-point tolerance for equal levels.

        This is intentionally configurable.

        We will eventually make this instrument-aware.
    */

    equalityTolerance: 0.00001
};


// ============================================================
// 2. BASIC VALIDATION
// ============================================================

function validateCandles(candles) {

    if (!Array.isArray(candles)) {

        throw new Error(
            "Aureus Technical Engine: candles must be an array."
        );

    }


    if (candles.length === 0) {

        throw new Error(
            "Aureus Technical Engine: candle data is empty."
        );

    }


    for (let i = 0; i < candles.length; i++) {

        const candle = candles[i];


        if (
            typeof candle.open !== "number" ||
            typeof candle.high !== "number" ||
            typeof candle.low !== "number" ||
            typeof candle.close !== "number"
        ) {

            throw new Error(
                `Invalid OHLC data at candle index ${i}.`
            );

        }


        if (candle.high < candle.low) {

            throw new Error(
                `Invalid candle at index ${i}: high < low.`
            );

        }


        if (candle.open < candle.low ||
            candle.open > candle.high) {

            throw new Error(
                `Invalid open price at candle index ${i}.`
            );

        }


        if (candle.close < candle.low ||
            candle.close > candle.high) {

            throw new Error(
                `Invalid close price at candle index ${i}.`
            );

        }

    }

}


// ============================================================
// 3. PRICE COMPARISON HELPERS
// ============================================================

function approximatelyEqual(priceA, priceB) {

    return (
        Math.abs(priceA - priceB) <=
        TECHNICAL_CONFIG.equalityTolerance
    );

}


// ============================================================
// 4. SWING HIGH DETECTION
// ============================================================

function isConfirmedSwingHigh(
    candles,
    index,
    strength = TECHNICAL_CONFIG.swingStrength
) {

    /*
        A swing cannot be confirmed if there aren't
        enough candles on either side.

        This is one of the most important protections
        against look-ahead errors.
    */

    if (
        index < strength ||
        index + strength >= candles.length
    ) {

        return false;

    }


    const candidateHigh =
        candles[index].high;


    /*
        LEFT SIDE

        Candidate must be strictly higher than
        all required candles to its left.
    */

    for (
        let offset = 1;
        offset <= strength;
        offset++
    ) {

        if (
            candidateHigh <=
            candles[index - offset].high
        ) {

            return false;

        }

    }


    /*
        RIGHT SIDE

        Candidate must also be strictly higher
        than all required candles to its right.
    */

    for (
        let offset = 1;
        offset <= strength;
        offset++
    ) {

        if (
            candidateHigh <=
            candles[index + offset].high
        ) {

            return false;

        }

    }


    return true;

}


// ============================================================
// 5. SWING LOW DETECTION
// ============================================================

function isConfirmedSwingLow(
    candles,
    index,
    strength = TECHNICAL_CONFIG.swingStrength
) {

    if (
        index < strength ||
        index + strength >= candles.length
    ) {

        return false;

    }


    const candidateLow =
        candles[index].low;


    /*
        LEFT SIDE
    */

    for (
        let offset = 1;
        offset <= strength;
        offset++
    ) {

        if (
            candidateLow >=
            candles[index - offset].low
        ) {

            return false;

        }

    }


    /*
        RIGHT SIDE
    */

    for (
        let offset = 1;
        offset <= strength;
        offset++
    ) {

        if (
            candidateLow >=
            candles[index + offset].low
        ) {

            return false;

        }

    }


    return true;

}


// ============================================================
// 6. FIND ALL CONFIRMED SWINGS
// ============================================================

function detectSwings(
    candles,
    strength = TECHNICAL_CONFIG.swingStrength
) {

    validateCandles(candles);


    const swings = [];


    /*
        IMPORTANT:

        We scan chronologically.

        A swing at index i becomes known only after
        the required candles to the RIGHT exist.

        The swing's confirmation index is:

            i + strength
    */

    for (
        let i = strength;
        i < candles.length - strength;
        i++
    ) {

        const swingHigh =
            isConfirmedSwingHigh(
                candles,
                i,
                strength
            );


        const swingLow =
            isConfirmedSwingLow(
                candles,
                i,
                strength
            );


        if (swingHigh) {

            swings.push({

                type: "SWING_HIGH",

                price: candles[i].high,

                candleIndex: i,

                confirmationIndex:
                    i + strength,

                timestamp:
                    candles[i].timestamp || null

            });

        }


        if (swingLow) {

            swings.push({

                type: "SWING_LOW",

                price: candles[i].low,

                candleIndex: i,

                confirmationIndex:
                    i + strength,

                timestamp:
                    candles[i].timestamp || null

            });

        }

    }


    /*
        Sort chronologically by confirmation time.
    */

    swings.sort(
        (a, b) =>
            a.confirmationIndex -
            b.confirmationIndex
    );


    return swings;

}


// ============================================================
// 7. CLASSIFY SWING HIGHS
// ============================================================

function classifySwingHighs(swings) {

    const highSwings =
        swings.filter(
            swing =>
                swing.type === "SWING_HIGH"
        );


    let previousHigh = null;


    for (const swing of highSwings) {


        /*
            First swing high cannot yet be classified
            as HH or LH because there is nothing before it.
        */

        if (previousHigh === null) {

            swing.classification =
                "INITIAL_HIGH";

            previousHigh = swing;

            continue;

        }


        if (
            swing.price >
            previousHigh.price
        ) {

            swing.classification =
                "HH";

        }

        else if (
            swing.price <
            previousHigh.price
        ) {

            swing.classification =
                "LH";

        }

        else {

            swing.classification =
                "EQUAL_HIGH";

        }


        previousHigh = swing;

    }


    return swings;

}


// ============================================================
// 8. CLASSIFY SWING LOWS
// ============================================================

function classifySwingLows(swings) {

    const lowSwings =
        swings.filter(
            swing =>
                swing.type === "SWING_LOW"
        );


    let previousLow = null;


    for (const swing of lowSwings) {


        if (previousLow === null) {

            swing.classification =
                "INITIAL_LOW";

            previousLow = swing;

            continue;

        }


        if (
            swing.price >
            previousLow.price
        ) {

            swing.classification =
                "HL";

        }

        else if (
            swing.price <
            previousLow.price
        ) {

            swing.classification =
                "LL";

        }

        else {

            swing.classification =
                "EQUAL_LOW";

        }


        previousLow = swing;

    }


    return swings;

}


// ============================================================
// 9. CLASSIFY ALL SWINGS
// ============================================================

function classifySwings(swings) {

    classifySwingHighs(swings);

    classifySwingLows(swings);

    return swings;

}


// ============================================================
// 10. GET CONFIRMED SWINGS AVAILABLE AT A GIVEN TIME
// ============================================================

function getAvailableSwings(
    swings,
    candleIndex
) {

    /*
        A swing is available only if its confirmation
        candle has already occurred.
    */

    return swings.filter(
        swing =>
            swing.confirmationIndex <=
            candleIndex
    );

}


// ============================================================
// 11. GET RECENT STRUCTURAL POINTS
// ============================================================

function getRecentStructuralPoints(
    swings,
    candleIndex,
    lookback =
        TECHNICAL_CONFIG.structureLookback
) {

    const available =
        getAvailableSwings(
            swings,
            candleIndex
        );


    return available.slice(
        -lookback
    );

}


// ============================================================
// 12. COUNT STRUCTURAL EVIDENCE
// ============================================================

function countStructureEvidence(
    structuralPoints
) {

    let bullishEvidence = 0;

    let bearishEvidence = 0;


    for (
        const point of structuralPoints
    ) {

        if (
            point.classification === "HH" ||
            point.classification === "HL"
        ) {

            bullishEvidence++;

        }


        if (
            point.classification === "LH" ||
            point.classification === "LL"
        ) {

            bearishEvidence++;

        }

    }


    return {

        bullishEvidence,

        bearishEvidence

    };

}


// ============================================================
// 13. DETERMINE MARKET STRUCTURE
// ============================================================

function determineMarketStructure(
    swings,
    candleIndex
) {

    const structuralPoints =
        getRecentStructuralPoints(
            swings,
            candleIndex
        );


    if (
        structuralPoints.length <
        TECHNICAL_CONFIG.minimumStructurePoints
    ) {

        return {

            structure: "INSUFFICIENT_DATA",

            confidence: 0,

            structuralPoints

        };

    }


    const evidence =
        countStructureEvidence(
            structuralPoints
        );


    const bullish =
        evidence.bullishEvidence;


    const bearish =
        evidence.bearishEvidence;


    /*
        We require directional evidence
        rather than simply looking at the
        most recent candle.
    */


    if (
        bullish > bearish
    ) {

        return {

            structure: "BULLISH",

            confidence:
                bullish /
                structuralPoints.length,

            structuralPoints,

            evidence

        };

    }


    if (
        bearish > bullish
    ) {

        return {

            structure: "BEARISH",

            confidence:
                bearish /
                structuralPoints.length,

            structuralPoints,

            evidence

        };

    }


    return {

        structure: "NEUTRAL",

        confidence: 0.5,

        structuralPoints,

        evidence

    };

}


// ============================================================
// 14. BUILD CHRONOLOGICAL STRUCTURE HISTORY
// ============================================================

function buildStructureHistory(
    candles,
    swings
) {

    const history = [];


    /*
        We evaluate structure at every candle.

        This will become extremely useful for
        historical backtesting.
    */

    for (
        let candleIndex = 0;
        candleIndex < candles.length;
        candleIndex++
    ) {

        const analysis =
            determineMarketStructure(
                swings,
                candleIndex
            );


        history.push({

            candleIndex,

            timestamp:
                candles[candleIndex].timestamp ||
                null,

            structure:
                analysis.structure,

            confidence:
                analysis.confidence,

            structuralPoints:
                analysis.structuralPoints,

            evidence:
                analysis.evidence || null

        });

    }


    return history;

}


// ============================================================
// 15. MAIN TECHNICAL ANALYSIS FUNCTION
// ============================================================

function analyzeMarketStructure(
    candles,
    options = {}
) {

    validateCandles(candles);


    /*
        Allow individual analysis calls to override
        the global swing strength.
    */

    const strength =
        options.swingStrength ||
        TECHNICAL_CONFIG.swingStrength;


    const swings =
        detectSwings(
            candles,
            strength
        );


    classifySwings(swings);


    const structureHistory =
        buildStructureHistory(
            candles,
            swings
        );


    const latest =
        structureHistory[
            structureHistory.length - 1
        ];


    return {

        swingStrength: strength,

        swings,

        structureHistory,

        currentStructure:
            latest.structure,

        currentConfidence:
            latest.confidence,

        latestStructuralPoints:
            latest.structuralPoints

    };

}


// ============================================================
// 16. SIMPLE TEST DATA
// ============================================================

/*
    This function exists only so we can test the engine
    later without needing a live market-data connection.

    DO NOT treat these prices as real market data.
*/

function createTestCandles() {

    return [

        { open: 100, high: 102, low: 99, close: 101 },

        { open: 101, high: 104, low: 100, close: 103 },

        { open: 103, high: 108, low: 102, close: 107 },

        { open: 107, high: 109, low: 105, close: 106 },

        { open: 106, high: 107, low: 103, close: 104 },

        { open: 104, high: 106, low: 101, close: 102 },

        { open: 102, high: 105, low: 100, close: 104 },

        { open: 104, high: 110, low: 103, close: 109 },

        { open: 109, high: 112, low: 107, close: 111 },

        { open: 111, high: 113, low: 108, close: 112 }

    ];

}


// ============================================================
// 17. EXPORTS
// ============================================================

if (typeof module !== "undefined") {

    module.exports = {

        TECHNICAL_CONFIG,

        validateCandles,

        isConfirmedSwingHigh,

        isConfirmedSwingLow,

        detectSwings,

        classifySwings,

        getAvailableSwings,

        getRecentStructuralPoints,

        determineMarketStructure,

        buildStructureHistory,

        analyzeMarketStructure,

        createTestCandles

    };

}
