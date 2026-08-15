/*
============================================================
AUREUS AI — LIQUIDITY ENGINE v1
============================================================

PURPOSE
-------
Identify important liquidity areas and distinguish between:

1. Buy-side liquidity
2. Sell-side liquidity
3. Equal highs
4. Equal lows
5. Previous day high / low
6. Previous week high / low
7. Swing-high liquidity
8. Swing-low liquidity
9. Liquidity sweeps
10. Rejection after a sweep

IMPORTANT
---------
A liquidity sweep is NOT automatically a trade signal.

Aureus will eventually require:

Liquidity
    ↓
Sweep
    ↓
Displacement
    ↓
Structure shift
    ↓
Location
    ↓
Fundamentals / News
    ↓
Risk / Reward
    ↓
Decision

This engine only identifies liquidity and sweep behaviour.

============================================================
*/


// ============================================================
// 1. CONFIGURATION
// ============================================================

const LIQUIDITY_CONFIG = {

    /*
        Price tolerance used when determining whether
        two highs/lows are approximately equal.

        This will eventually become instrument-aware.
    */

    equalityTolerance: 0.00001,


    /*
        Number of candles used to identify clustered
        equal highs/lows.

        Example:

        2 means we require at least two relevant
        highs/lows in the same area.
    */

    minimumClusterSize: 2,


    /*
        A sweep must move beyond the liquidity level
        by at least this amount.

        This is currently expressed as a fraction of
        recent ATR.

        We will test and optimize this later.
    */

    minimumSweepDistanceATR: 0.05,


    /*
        Number of candles used to calculate ATR.
    */

    atrLookback: 14,


    /*
        How many candles after a liquidity event we
        inspect for rejection.

        We will later test whether confirmation
        should happen immediately or within a window.
    */

    rejectionWindow: 3,


    /*
        Whether the current candle must close back
        inside the liquidity level for a sweep to
        qualify.

        We keep this strict for Version 1.
    */

    requireCloseBackInside: true

};


// ============================================================
// 2. BASIC VALIDATION
// ============================================================

function validateCandles(candles) {

    if (!Array.isArray(candles)) {

        throw new Error(
            "Liquidity Engine: candles must be an array."
        );

    }


    if (candles.length === 0) {

        throw new Error(
            "Liquidity Engine: candle data is empty."
        );

    }


    for (
        let i = 0;
        i < candles.length;
        i++
    ) {

        const candle =
            candles[i];


        if (
            typeof candle.high !== "number" ||
            typeof candle.low !== "number" ||
            typeof candle.open !== "number" ||
            typeof candle.close !== "number"
        ) {

            throw new Error(
                `Invalid OHLC data at candle ${i}.`
            );

        }

    }

}


// ============================================================
// 3. APPROXIMATE EQUALITY
// ============================================================

function approximatelyEqual(
    priceA,
    priceB,
    tolerance =
        LIQUIDITY_CONFIG.equalityTolerance
) {

    return (
        Math.abs(priceA - priceB)
        <= tolerance
    );

}


// ============================================================
// 4. CANDLE RANGE
// ============================================================

function candleRange(candle) {

    return (
        candle.high -
        candle.low
    );

}


// ============================================================
// 5. TRUE RANGE
// ============================================================

function trueRange(
    candle,
    previousCandle
) {

    if (!previousCandle) {

        return candleRange(
            candle
        );

    }


    return Math.max(

        candle.high -
        candle.low,

        Math.abs(
            candle.high -
            previousCandle.close
        ),

        Math.abs(
            candle.low -
            previousCandle.close
        )

    );

}


// ============================================================
// 6. ATR
// ============================================================

function calculateATR(
    candles,
    endIndex,
    lookback =
        LIQUIDITY_CONFIG.atrLookback
) {

    /*
        Only candles BEFORE endIndex are used.

        This is important for backtesting.
    */

    const start =
        Math.max(
            1,
            endIndex - lookback
        );


    const ranges = [];


    for (
        let i = start;
        i < endIndex;
        i++
    ) {

        ranges.push(

            trueRange(
                candles[i],
                candles[i - 1]
            )

        );

    }


    if (
        ranges.length === 0
    ) {

        return null;

    }


    const total =
        ranges.reduce(
            (sum, value) =>
                sum + value,
            0
        );


    return (
        total /
        ranges.length
    );

}


// ============================================================
// 7. CREATE SWING LIQUIDITY
// ============================================================

function createSwingLiquidity(
    swings
) {

    const liquidity = [];


    for (
        const swing of swings
    ) {

        if (
            swing.type ===
            "SWING_HIGH"
        ) {

            liquidity.push({

                type:
                    "SWING_HIGH_LIQUIDITY",

                side:
                    "BUY_SIDE",

                price:
                    swing.price,

                candleIndex:
                    swing.candleIndex,

                confirmationIndex:
                    swing.confirmationIndex,

                classification:
                    swing.classification,

                source:
                    "SWING_HIGH"

            });

        }


        if (
            swing.type ===
            "SWING_LOW"
        ) {

            liquidity.push({

                type:
                    "SWING_LOW_LIQUIDITY",

                side:
                    "SELL_SIDE",

                price:
                    swing.price,

                candleIndex:
                    swing.candleIndex,

                confirmationIndex:
                    swing.confirmationIndex,

                classification:
                    swing.classification,

                source:
                    "SWING_LOW"

            });

        }

    }


    return liquidity;

}


// ============================================================
// 8. DETECT EQUAL HIGH CLUSTERS
// ============================================================

function detectEqualHighs(
    swings
) {

    const highs =
        swings.filter(
            swing =>
                swing.type ===
                "SWING_HIGH"
        );


    const clusters = [];


    for (
        let i = 0;
        i < highs.length;
        i++
    ) {

        const base =
            highs[i];


        const members = [
            base
        ];


        for (
            let j = i + 1;
            j < highs.length;
            j++
        ) {

            if (
                approximatelyEqual(
                    base.price,
                    highs[j].price
                )
            ) {

                members.push(
                    highs[j]
                );

            }

        }


        if (
            members.length >=
            LIQUIDITY_CONFIG.minimumClusterSize
        ) {

            /*
                Use the average price of the
                cluster as the liquidity level.
            */

            const averagePrice =
                members.reduce(
                    (sum, swing) =>
                        sum + swing.price,
                    0
                ) /
                members.length;


            clusters.push({

                type:
                    "EQUAL_HIGH_CLUSTER",

                side:
                    "BUY_SIDE",

                price:
                    averagePrice,

                members,

                size:
                    members.length,

                source:
                    "EQUAL_HIGHS"

            });

        }

    }


    return removeDuplicateClusters(
        clusters
    );

}


// ============================================================
// 9. DETECT EQUAL LOW CLUSTERS
// ============================================================

function detectEqualLows(
    swings
) {

    const lows =
        swings.filter(
            swing =>
                swing.type ===
                "SWING_LOW"
        );


    const clusters = [];


    for (
        let i = 0;
        i < lows.length;
        i++
    ) {

        const base =
            lows[i];


        const members = [
            base
        ];


        for (
            let j = i + 1;
            j < lows.length;
            j++
        ) {

            if (
                approximatelyEqual(
                    base.price,
                    lows[j].price
                )
            ) {

                members.push(
                    lows[j]
                );

            }

        }


        if (
            members.length >=
            LIQUIDITY_CONFIG.minimumClusterSize
        ) {

            const averagePrice =
                members.reduce(
                    (sum, swing) =>
                        sum + swing.price,
                    0
                ) /
                members.length;


            clusters.push({

                type:
                    "EQUAL_LOW_CLUSTER",

                side:
                    "SELL_SIDE",

                price:
                    averagePrice,

                members,

                size:
                    members.length,

                source:
                    "EQUAL_LOWS"

            });

        }

    }


    return removeDuplicateClusters(
        clusters
    );

}


// ============================================================
// 10. REMOVE DUPLICATE CLUSTERS
// ============================================================

function removeDuplicateClusters(
    clusters
) {

    const unique = [];


    for (
        const cluster of clusters
    ) {

        const duplicate =
            unique.some(
                existing =>
                    approximatelyEqual(
                        existing.price,
                        cluster.price
                    ) &&
                    existing.type ===
                    cluster.type
            );


        if (!duplicate) {

            unique.push(
                cluster
            );

        }

    }


    return unique;

}


// ============================================================
// 11. DETECT PREVIOUS DAY LEVELS
// ============================================================

function detectPreviousDayLevels(
    candles
) {

    /*
        This function assumes candles contain
        timestamps.

        We group candles by UTC calendar date.

        Later, when we connect real market data,
        we will make the trading-session timezone
        configurable.
    */

    const dailyData = {};


    for (
        const candle of candles
    ) {

        if (!candle.timestamp) {

            continue;

        }


        const date =
            new Date(
                candle.timestamp
            );


        const key =
            date
                .toISOString()
                .slice(0, 10);


        if (!dailyData[key]) {

            dailyData[key] = {

                high:
                    candle.high,

                low:
                    candle.low

            };

        }

        else {

            dailyData[key].high =
                Math.max(
                    dailyData[key].high,
                    candle.high
                );

            dailyData[key].low =
                Math.min(
                    dailyData[key].low,
                    candle.low
                );

        }

    }


    const dates =
        Object.keys(
            dailyData
        ).sort();


    const levels = [];


    for (
        let i = 1;
        i < dates.length;
        i++
    ) {

        const previousDate =
            dates[i - 1];


        const currentDate =
            dates[i];


        levels.push({

            date:
                currentDate,

            type:
                "PREVIOUS_DAY_HIGH",

            side:
                "BUY_SIDE",

            price:
                dailyData[
                    previousDate
                ].high,

            source:
                "PREVIOUS_DAY"

        });


        levels.push({

            date:
                currentDate,

            type:
                "PREVIOUS_DAY_LOW",

            side:
                "SELL_SIDE",

            price:
                dailyData[
                    previousDate
                ].low,

            source:
                "PREVIOUS_DAY"

        });

    }


    return levels;

}


// ============================================================
// 12. DETECT PREVIOUS WEEK LEVELS
// ============================================================

function getISOWeekKey(
    timestamp
) {

    const date =
        new Date(timestamp);


    /*
        Use UTC date to avoid timezone ambiguity
        in the initial implementation.
    */

    const year =
        date.getUTCFullYear();


    const firstDay =
        new Date(
            Date.UTC(
                year,
                0,
                1
            )
        );


    const dayOfYear =
        Math.floor(
            (
                date -
                firstDay
            ) /
            86400000
        );


    const week =
        Math.floor(
            (
                dayOfYear +
                firstDay.getUTCDay()
            ) / 7
        ) + 1;


    return `${year}-W${week}`;

}


function detectPreviousWeekLevels(
    candles
) {

    const weeklyData = {};


    for (
        const candle of candles
    ) {

        if (!candle.timestamp) {

            continue;

        }


        const week =
            getISOWeekKey(
                candle.timestamp
            );


        if (!weeklyData[week]) {

            weeklyData[week] = {

                high:
                    candle.high,

                low:
                    candle.low

            };

        }

        else {

            weeklyData[week].high =
                Math.max(
                    weeklyData[week].high,
                    candle.high
                );

            weeklyData[week].low =
                Math.min(
                    weeklyData[week].low,
                    candle.low
                );

        }

    }


    const weeks =
        Object.keys(
            weeklyData
        ).sort();


    const levels = [];


    for (
        let i = 1;
        i < weeks.length;
        i++
    ) {

        const previousWeek =
            weeks[i - 1];


        const currentWeek =
            weeks[i];


        levels.push({

            week:
                currentWeek,

            type:
                "PREVIOUS_WEEK_HIGH",

            side:
                "BUY_SIDE",

            price:
                weeklyData[
                    previousWeek
                ].high,

            source:
                "PREVIOUS_WEEK"

        });


        levels.push({

            week:
                currentWeek,

            type:
                "PREVIOUS_WEEK_LOW",

            side:
                "SELL_SIDE",

            price:
                weeklyData[
                    previousWeek
                ].low,

            source:
                "PREVIOUS_WEEK"

        });

    }


    return levels;

}


// ============================================================
// 13. BUILD LIQUIDITY MAP
// ============================================================

function buildLiquidityMap(
    candles,
    swings
) {

    validateCandles(
        candles
    );


    const swingLiquidity =
        createSwingLiquidity(
            swings
        );


    const equalHighs =
        detectEqualHighs(
            swings
        );


    const equalLows =
        detectEqualLows(
            swings
        );


    const previousDay =
        detectPreviousDayLevels(
            candles
        );


    const previousWeek =
        detectPreviousWeekLevels(
            candles
        );


    return {

        swingLiquidity,

        equalHighs,

        equalLows,

        previousDay,

        previousWeek,

        buySideLiquidity: [

            ...swingLiquidity.filter(
                level =>
                    level.side ===
                    "BUY_SIDE"
            ),

            ...equalHighs,

            ...previousDay.filter(
                level =>
                    level.side ===
                    "BUY_SIDE"
            ),

            ...previousWeek.filter(
                level =>
                    level.side ===
                    "BUY_SIDE"
            )

        ],

        sellSideLiquidity: [

            ...swingLiquidity.filter(
                level =>
                    level.side ===
                    "SELL_SIDE"
            ),

            ...equalLows,

            ...previousDay.filter(
                level =>
                    level.side ===
                    "SELL_SIDE"
            ),

            ...previousWeek.filter(
                level =>
                    level.side ===
                    "SELL_SIDE"
            )

        ]

    };

}


// ============================================================
// 14. CHECK BUY-SIDE LIQUIDITY SWEEP
// ============================================================

function detectBuySideSweep(
    candles,
    level,
    index
) {

    const candle =
        candles[index];


    const previousCandle =
        candles[index - 1];


    if (!previousCandle) {

        return null;

    }


    /*
        Price must trade ABOVE the liquidity level.
    */

    const tradedAbove =
        candle.high >
        level.price;


    if (!tradedAbove) {

        return null;

    }


    /*
        Calculate sweep distance.
    */

    const atr =
        calculateATR(
            candles,
            index
        );


    const minimumDistance =
        atr
            ? atr *
              LIQUIDITY_CONFIG.minimumSweepDistanceATR
            : 0;


    const sweepDistance =
        candle.high -
        level.price;


    if (
        sweepDistance <
        minimumDistance
    ) {

        return null;

    }


    /*
        STRICT VERSION:

        Price must close back at or below
        the liquidity level.

        This separates a potential sweep from
        a clean breakout.
    */

    const rejected =
        candle.close <=
        level.price;


    if (
        LIQUIDITY_CONFIG.requireCloseBackInside &&
        !rejected
    ) {

        return null;

    }


    return {

        type:
            "BUY_SIDE_LIQUIDITY_SWEEP",

        side:
            "BUY_SIDE",

        direction:
            "BEARISH_POTENTIAL",

        candleIndex:
            index,

        timestamp:
            candle.timestamp || null,

        liquidityLevel:
            level.price,

        high:
            candle.high,

        close:
            candle.close,

        sweepDistance,

        atr,

        rejected,

        source:
            level.source ||
            level.type

    };

}


// ============================================================
// 15. CHECK SELL-SIDE LIQUIDITY SWEEP
// ============================================================

function detectSellSideSweep(
    candles,
    level,
    index
) {

    const candle =
        candles[index];


    const previousCandle =
        candles[index - 1];


    if (!previousCandle) {

        return null;

    }


    /*
        Price must trade BELOW the liquidity level.
    */

    const tradedBelow =
        candle.low <
        level.price;


    if (!tradedBelow) {

        return null;

    }


    const atr =
        calculateATR(
            candles,
            index
        );


    const minimumDistance =
        atr
            ? atr *
              LIQUIDITY_CONFIG.minimumSweepDistanceATR
            : 0;


    const sweepDistance =
        level.price -
        candle.low;


    if (
        sweepDistance <
        minimumDistance
    ) {

        return null;

    }


    /*
        Price must close back at or above
        the liquidity level.
    */

    const rejected =
        candle.close >=
        level.price;


    if (
        LIQUIDITY_CONFIG.requireCloseBackInside &&
        !rejected
    ) {

        return null;

    }


    return {

        type:
            "SELL_SIDE_LIQUIDITY_SWEEP",

        side:
            "SELL_SIDE",

        direction:
            "BULLISH_POTENTIAL",

        candleIndex:
            index,

        timestamp:
            candle.timestamp || null,

        liquidityLevel:
            level.price,

        low:
            candle.low,

        close:
            candle.close,

        sweepDistance,

        atr,

        rejected,

        source:
            level.source ||
            level.type

    };

}


// ============================================================
// 16. DETECT SWEEPS AGAINST ALL LEVELS
// ============================================================

function detectLiquiditySweeps(
    candles,
    liquidityMap
) {

    const sweeps = [];


    for (
        let i = 0;
        i < candles.length;
        i++
    ) {

        /*
            BUY-SIDE
        */

        for (
            const level of
            liquidityMap.buySideLiquidity
        ) {

            const sweep =
                detectBuySideSweep(
                    candles,
                    level,
                    i
                );


            if (sweep) {

                sweeps.push(
                    sweep
                );

            }

        }


        /*
            SELL-SIDE
        */

        for (
            const level of
            liquidityMap.sellSideLiquidity
        ) {

            const sweep =
                detectSellSideSweep(
                    candles,
                    level,
                    i
                );


            if (sweep) {

                sweeps.push(
                    sweep
                );

            }

        }

    }


    return sweeps;

}


// ============================================================
// 17. CHECK FOLLOW-THROUGH AFTER SWEEP
// ============================================================

function analyzeSweepFollowThrough(
    candles,
    sweep
) {

    const start =
        sweep.candleIndex;


    const end =
        Math.min(
            candles.length,
            start +
            LIQUIDITY_CONFIG.rejectionWindow +
            1
        );


    const futureCandles =
        candles.slice(
            start,
            end
        );


    /*
        IMPORTANT:

        This function is an analytical result
        AFTER the sweep.

        It must NOT be used as if the information
        were known at the exact sweep candle.

        This distinction is essential for the
        eventual backtester.
    */

    let bullishFollowThrough =
        false;


    let bearishFollowThrough =
        false;


    for (
        const candle of
        futureCandles
    ) {

        if (
            candle.close >
            sweep.liquidityLevel
        ) {

            bullishFollowThrough =
                true;

        }


        if (
            candle.close <
            sweep.liquidityLevel
        ) {

            bearishFollowThrough =
                true;

        }

    }


    return {

        bullishFollowThrough,

        bearishFollowThrough,

        observationWindow:
            futureCandles.length

    };

}


// ============================================================
// 18. MAIN LIQUIDITY ANALYSIS
// ============================================================

function analyzeLiquidity(
    candles,
    swings
) {

    validateCandles(
        candles
    );


    const liquidityMap =
        buildLiquidityMap(
            candles,
            swings
        );


    const sweeps =
        detectLiquiditySweeps(
            candles,
            liquidityMap
        );


    return {

        liquidityMap,

        sweeps,

        buySideSweeps:
            sweeps.filter(
                sweep =>
                    sweep.side ===
                    "BUY_SIDE"
            ),

        sellSideSweeps:
            sweeps.filter(
                sweep =>
                    sweep.side ===
                    "SELL_SIDE"
            )

    };

}


// ============================================================
// 19. EXPORTS
// ============================================================

if (typeof module !== "undefined") {

    module.exports = {

        LIQUIDITY_CONFIG,

        approximatelyEqual,

        candleRange,

        trueRange,

        calculateATR,

        createSwingLiquidity,

        detectEqualHighs,

        detectEqualLows,

        detectPreviousDayLevels,

        detectPreviousWeekLevels,

        buildLiquidityMap,

        detectBuySideSweep,

        detectSellSideSweep,

        detectLiquiditySweeps,

        analyzeSweepFollowThrough,

        analyzeLiquidity

    };

}
