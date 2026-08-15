/*
============================================================
AUREUS AI — STRUCTURE BREAK ENGINE v1
============================================================

PURPOSE
-------
Detect structural breaks after the market structure engine
has identified confirmed swing highs and swing lows.

CURRENT DETECTIONS
------------------

1. Bullish BOS
2. Bearish BOS
3. Bullish CHOCH / Structure Shift
4. Bearish CHOCH / Structure Shift
5. Displacement
6. Break confirmation
7. Wick-only rejection vs closing break

IMPORTANT
---------
Aureus does NOT consider a wick through a structural level
to be a confirmed BOS.

A structural break requires a candle CLOSE beyond the level.

This engine is designed for future historical backtesting
and therefore avoids using future information.

============================================================
*/


// ============================================================
// 1. CONFIGURATION
// ============================================================

const STRUCTURE_BREAK_CONFIG = {

    /*
        Number of candles used to calculate recent volatility.
    */

    volatilityLookback: 14,


    /*
        Minimum displacement ratio.

        Example:

        Current candle range / average recent range

        A value of 1.5 means the current candle range must
        be at least 1.5 times the recent average range.

        IMPORTANT:
        This is a starting parameter.

        We will eventually optimize/test this rather than
        assuming 1.5 is universally optimal.
    */

    minimumDisplacementRatio: 1.5,


    /*
        Minimum body-to-range ratio for displacement.

        This prevents a huge candle with an enormous wick
        from automatically being considered strong
        directional displacement.
    */

    minimumBodyRatio: 0.60,


    /*
        Require the closing price to be beyond the
        structural level.

        This should remain TRUE for our initial model.
    */

    requireCloseBeyondLevel: true,


    /*
        Minimum number of candles that must separate
        repeated breaks of the same level.

        Prevents the engine from generating excessive
        duplicate signals.
    */

    minimumBreakSeparation: 1

};


// ============================================================
// 2. BASIC VALIDATION
// ============================================================

function validateInputs(candles, swings) {

    if (!Array.isArray(candles)) {

        throw new Error(
            "Structure Break Engine: candles must be an array."
        );

    }


    if (!Array.isArray(swings)) {

        throw new Error(
            "Structure Break Engine: swings must be an array."
        );

    }


    if (candles.length === 0) {

        throw new Error(
            "Structure Break Engine: candle data is empty."
        );

    }

}


// ============================================================
// 3. CANDLE RANGE
// ============================================================

function getCandleRange(candle) {

    return candle.high - candle.low;

}


// ============================================================
// 4. CANDLE BODY
// ============================================================

function getCandleBody(candle) {

    return Math.abs(
        candle.close - candle.open
    );

}


// ============================================================
// 5. BODY / RANGE RATIO
// ============================================================

function getBodyRatio(candle) {

    const range =
        getCandleRange(candle);


    if (range === 0) {

        return 0;

    }


    return (
        getCandleBody(candle) /
        range
    );

}


// ============================================================
// 6. AVERAGE RANGE
// ============================================================

function getAverageRange(
    candles,
    endIndex,
    lookback =
        STRUCTURE_BREAK_CONFIG.volatilityLookback
) {

    /*
        IMPORTANT:

        We only use candles BEFORE the current candle.

        This prevents the current candle from influencing
        its own displacement measurement.
    */

    const startIndex =
        Math.max(
            0,
            endIndex - lookback
        );


    const historicalCandles =
        candles.slice(
            startIndex,
            endIndex
        );


    if (
        historicalCandles.length === 0
    ) {

        return null;

    }


    const totalRange =
        historicalCandles.reduce(
            (sum, candle) =>
                sum + getCandleRange(candle),
            0
        );


    return (
        totalRange /
        historicalCandles.length
    );

}


// ============================================================
// 7. DISPLACEMENT ANALYSIS
// ============================================================

function analyzeDisplacement(
    candles,
    index
) {

    if (
        index < 1 ||
        index >= candles.length
    ) {

        return {

            displacement: false,

            direction: "NONE",

            range: 0,

            averageRange: null,

            displacementRatio: 0,

            bodyRatio: 0

        };

    }


    const candle =
        candles[index];


    const range =
        getCandleRange(candle);


    const averageRange =
        getAverageRange(
            candles,
            index
        );


    const bodyRatio =
        getBodyRatio(candle);


    if (
        averageRange === null ||
        averageRange === 0
    ) {

        return {

            displacement: false,

            direction: "NONE",

            range,

            averageRange,

            displacementRatio: 0,

            bodyRatio

        };

    }


    const displacementRatio =
        range /
        averageRange;


    const strongRange =
        displacementRatio >=
        STRUCTURE_BREAK_CONFIG.minimumDisplacementRatio;


    const strongBody =
        bodyRatio >=
        STRUCTURE_BREAK_CONFIG.minimumBodyRatio;


    let direction = "NONE";


    if (
        candle.close >
        candle.open
    ) {

        direction = "BULLISH";

    }

    else if (
        candle.close <
        candle.open
    ) {

        direction = "BEARISH";

    }


    return {

        displacement:
            strongRange &&
            strongBody,

        direction,

        range,

        averageRange,

        displacementRatio,

        bodyRatio

    };

}


// ============================================================
// 8. GET AVAILABLE SWINGS
// ============================================================

function getAvailableSwings(
    swings,
    candleIndex
) {

    /*
        A swing can only be used after its confirmation
        candle has occurred.
    */

    return swings.filter(
        swing =>
            swing.confirmationIndex <=
            candleIndex
    );

}


// ============================================================
// 9. GET MOST RECENT SWING HIGH
// ============================================================

function getLatestSwingHigh(
    swings,
    candleIndex
) {

    const available =
        getAvailableSwings(
            swings,
            candleIndex
        );


    const highs =
        available.filter(
            swing =>
                swing.type ===
                "SWING_HIGH"
        );


    if (highs.length === 0) {

        return null;

    }


    return highs[highs.length - 1];

}


// ============================================================
// 10. GET MOST RECENT SWING LOW
// ============================================================

function getLatestSwingLow(
    swings,
    candleIndex
) {

    const available =
        getAvailableSwings(
            swings,
            candleIndex
        );


    const lows =
        available.filter(
            swing =>
                swing.type ===
                "SWING_LOW"
        );


    if (lows.length === 0) {

        return null;

    }


    return lows[lows.length - 1];

}


// ============================================================
// 11. FIND PREVIOUS STRUCTURE
// ============================================================

function getPreviousStructure(
    swings,
    candleIndex
) {

    const available =
        getAvailableSwings(
            swings,
            candleIndex
        );


    const recent =
        available.slice(-6);


    let bullishPoints = 0;

    let bearishPoints = 0;


    for (
        const swing of recent
    ) {

        if (
            swing.classification === "HH" ||
            swing.classification === "HL"
        ) {

            bullishPoints++;

        }


        if (
            swing.classification === "LH" ||
            swing.classification === "LL"
        ) {

            bearishPoints++;

        }

    }


    if (
        bullishPoints >
        bearishPoints
    ) {

        return "BULLISH";

    }


    if (
        bearishPoints >
        bullishPoints
    ) {

        return "BEARISH";

    }


    return "NEUTRAL";

}


// ============================================================
// 12. TEST BULLISH BREAK
// ============================================================

function detectBullishBreak(
    candles,
    swings,
    index
) {

    const candle =
        candles[index];


    const swingHigh =
        getLatestSwingHigh(
            swings,
            index - 1
        );


    if (!swingHigh) {

        return null;

    }


    /*
        The previous candle must not already have
        closed above this level.

        This helps prevent repeated detection of
        the same break.
    */

    if (
        index > 0 &&
        candles[index - 1].close >
        swingHigh.price
    ) {

        return null;

    }


    /*
        A bullish break requires the CURRENT candle
        to CLOSE above the structural high.
    */

    const closedAbove =
        candle.close >
        swingHigh.price;


    if (!closedAbove) {

        return null;

    }


    const displacement =
        analyzeDisplacement(
            candles,
            index
        );


    const previousStructure =
        getPreviousStructure(
            swings,
            index - 1
        );


    /*
        If the existing structure was bearish,
        breaking the high is classified as a
        bullish CHOCH / structure shift.

        If the existing structure was bullish,
        breaking the high is classified as BOS.
    */

    let eventType;


    if (
        previousStructure ===
        "BEARISH"
    ) {

        eventType =
            "BULLISH_CHOCH";

    }

    else {

        eventType =
            "BULLISH_BOS";

    }


    return {

        type: eventType,

        direction: "BULLISH",

        candleIndex: index,

        timestamp:
            candle.timestamp || null,

        brokenLevel:
            swingHigh.price,

        brokenSwingIndex:
            swingHigh.candleIndex,

        close:
            candle.close,

        high:
            candle.high,

        low:
            candle.low,

        displacement,

        previousStructure,

        confirmedByClose: true

    };

}


// ============================================================
// 13. TEST BEARISH BREAK
// ============================================================

function detectBearishBreak(
    candles,
    swings,
    index
) {

    const candle =
        candles[index];


    const swingLow =
        getLatestSwingLow(
            swings,
            index - 1
        );


    if (!swingLow) {

        return null;

    }


    if (
        index > 0 &&
        candles[index - 1].close <
        swingLow.price
    ) {

        return null;

    }


    /*
        Bearish break requires a CLOSE below
        the structural low.
    */

    const closedBelow =
        candle.close <
        swingLow.price;


    if (!closedBelow) {

        return null;

    }


    const displacement =
        analyzeDisplacement(
            candles,
            index
        );


    const previousStructure =
        getPreviousStructure(
            swings,
            index - 1
        );


    let eventType;


    if (
        previousStructure ===
        "BULLISH"
    ) {

        eventType =
            "BEARISH_CHOCH";

    }

    else {

        eventType =
            "BEARISH_BOS";

    }


    return {

        type: eventType,

        direction: "BEARISH",

        candleIndex: index,

        timestamp:
            candle.timestamp || null,

        brokenLevel:
            swingLow.price,

        brokenSwingIndex:
            swingLow.candleIndex,

        close:
            candle.close,

        high:
            candle.high,

        low:
            candle.low,

        displacement,

        previousStructure,

        confirmedByClose: true

    };

}


// ============================================================
// 14. DETECT ALL STRUCTURAL BREAKS
// ============================================================

function detectStructureBreaks(
    candles,
    swings
) {

    validateInputs(
        candles,
        swings
    );


    const events = [];


    /*
        Start from the second candle because
        displacement requires previous data.
    */

    for (
        let i = 1;
        i < candles.length;
        i++
    ) {

        /*
            Bullish break
        */

        const bullishBreak =
            detectBullishBreak(
                candles,
                swings,
                i
            );


        if (bullishBreak) {

            events.push(
                bullishBreak
            );

        }


        /*
            Bearish break
        */

        const bearishBreak =
            detectBearishBreak(
                candles,
                swings,
                i
            );


        if (bearishBreak) {

            events.push(
                bearishBreak
            );

        }

    }


    return events;

}


// ============================================================
// 15. DETECT WICK-ONLY LIQUIDITY EVENTS
// ============================================================

function detectWickThroughLevel(
    candles,
    swings,
    index
) {

    const candle =
        candles[index];


    const swingHigh =
        getLatestSwingHigh(
            swings,
            index - 1
        );


    const swingLow =
        getLatestSwingLow(
            swings,
            index - 1
        );


    const events = [];


    /*
        Price traded ABOVE a swing high
        but CLOSED back below it.

        This is NOT a BOS.

        It is only a potential liquidity event.

        We will build the complete liquidity engine later.
    */

    if (
        swingHigh &&
        candle.high >
        swingHigh.price &&
        candle.close <=
        swingHigh.price
    ) {

        events.push({

            type:
                "HIGH_LIQUIDITY_WICK",

            direction:
                "BEARISH_POTENTIAL",

            candleIndex:
                index,

            level:
                swingHigh.price,

            high:
                candle.high,

            close:
                candle.close,

            confirmedByClose:
                false

        });

    }


    /*
        Price traded BELOW a swing low
        but CLOSED back above it.
    */

    if (
        swingLow &&
        candle.low <
        swingLow.price &&
        candle.close >=
        swingLow.price
    ) {

        events.push({

            type:
                "LOW_LIQUIDITY_WICK",

            direction:
                "BULLISH_POTENTIAL",

            candleIndex:
                index,

            level:
                swingLow.price,

            low:
                candle.low,

            close:
                candle.close,

            confirmedByClose:
                false

        });

    }


    return events;

}


// ============================================================
// 16. BUILD COMPLETE STRUCTURE HISTORY
// ============================================================

function buildStructureBreakHistory(
    candles,
    swings
) {

    const history = [];


    for (
        let i = 0;
        i < candles.length;
        i++
    ) {

        const bullishBreak =
            detectBullishBreak(
                candles,
                swings,
                i
            );


        const bearishBreak =
            detectBearishBreak(
                candles,
                swings,
                i
            );


        const wickEvents =
            detectWickThroughLevel(
                candles,
                swings,
                i
            );


        const displacement =
            analyzeDisplacement(
                candles,
                i
            );


        history.push({

            candleIndex: i,

            timestamp:
                candles[i].timestamp ||
                null,

            bullishBreak,

            bearishBreak,

            wickEvents,

            displacement

        });

    }


    return history;

}


// ============================================================
// 17. MAIN ANALYSIS FUNCTION
// ============================================================

function analyzeStructureBreaks(
    candles,
    swings
) {

    validateInputs(
        candles,
        swings
    );


    const events =
        detectStructureBreaks(
            candles,
            swings
        );


    const history =
        buildStructureBreakHistory(
            candles,
            swings
        );


    return {

        events,

        history,

        bullishEvents:
            events.filter(
                event =>
                    event.direction ===
                    "BULLISH"
            ),

        bearishEvents:
            events.filter(
                event =>
                    event.direction ===
                    "BEARISH"
            ),

        displacementEvents:
            history.filter(
                item =>
                    item.displacement &&
                    item.displacement.displacement
            )

    };

}


// ============================================================
// 18. EXPORTS
// ============================================================

if (typeof module !== "undefined") {

    module.exports = {

        STRUCTURE_BREAK_CONFIG,

        getCandleRange,

        getCandleBody,

        getBodyRatio,

        getAverageRange,

        analyzeDisplacement,

        getAvailableSwings,

        getLatestSwingHigh,

        getLatestSwingLow,

        getPreviousStructure,

        detectBullishBreak,

        detectBearishBreak,

        detectStructureBreaks,

        detectWickThroughLevel,

        buildStructureBreakHistory,

        analyzeStructureBreaks

    };

}
