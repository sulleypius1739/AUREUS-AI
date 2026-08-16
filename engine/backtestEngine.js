/*
============================================================
AUREUS AI — BACKTEST ENGINE v1
============================================================

NO LOOK-AHEAD BACKTESTING

The engine processes historical candles sequentially.

At candle i:
    Aureus can only use candles <= i.

Once a signal occurs:
    entry
    stop loss
    take profit

are recorded.

Future candles are used ONLY to determine the result.

============================================================
*/

const {
    analyzeMarket
} = require("./analysisEngine");


const BACKTEST_CONFIG = {

    startingCapital: 10000,

    riskPerTradePercent: 1,

    maxBarsInTrade: 100,

    allowLong: true,

    allowShort: true,

    minimumScore: 75,

    minimumRiskReward: 2

};


// ============================================================
// 1. VALIDATE DATA
// ============================================================

function validateCandles(candles) {

    if (!Array.isArray(candles)) {

        throw new Error(
            "Backtest data must be an array."
        );

    }

    if (candles.length < 100) {

        throw new Error(
            "At least 100 candles are recommended."
        );

    }

}


// ============================================================
// 2. CALCULATE POSITION SIZE
// ============================================================

function calculatePositionSize(
    capital,
    entry,
    stopLoss,
    riskPercent
) {

    const riskMoney =
        capital *
        (riskPercent / 100);

    const riskPerUnit =
        Math.abs(
            entry - stopLoss
        );

    if (
        riskPerUnit <= 0
    ) {

        return 0;

    }

    return (
        riskMoney /
        riskPerUnit
    );

}


// ============================================================
// 3. CHECK TRADE RESULT
// ============================================================

function checkTradeResult(
    candles,
    entryIndex,
    trade
) {

    const endIndex =
        Math.min(
            candles.length,
            entryIndex +
            BACKTEST_CONFIG.maxBarsInTrade +
            1
        );


    for (
        let i = entryIndex + 1;
        i < endIndex;
        i++
    ) {

        const candle =
            candles[i];


        /*
        LONG TRADE
        */

        if (
            trade.direction ===
            "BUY"
        ) {

            const hitSL =
                candle.low <=
                trade.stopLoss;

            const hitTP =
                candle.high >=
                trade.takeProfit;


            /*
            Conservative assumption:

            If both SL and TP occur inside
            the same candle, assume SL happened
            first.

            This prevents artificially optimistic
            backtests when only OHLC data exists.
            */

            if (
                hitSL &&
                hitTP
            ) {

                return {

                    result: "LOSS",

                    exitPrice:
                        trade.stopLoss,

                    exitIndex: i,

                    reason:
                        "SL_AND_TP_SAME_CANDLE_SL_ASSUMED_FIRST"

                };

            }


            if (hitSL) {

                return {

                    result: "LOSS",

                    exitPrice:
                        trade.stopLoss,

                    exitIndex: i,

                    reason:
                        "STOP_LOSS"

                };

            }


            if (hitTP) {

                return {

                    result: "WIN",

                    exitPrice:
                        trade.takeProfit,

                    exitIndex: i,

                    reason:
                        "TAKE_PROFIT"

                };

            }

        }


        /*
        SHORT TRADE
        */

        if (
            trade.direction ===
            "SELL"
        ) {

            const hitSL =
                candle.high >=
                trade.stopLoss;

            const hitTP =
                candle.low <=
                trade.takeProfit;


            if (
                hitSL &&
                hitTP
            ) {

                return {

                    result: "LOSS",

                    exitPrice:
                        trade.stopLoss,

                    exitIndex: i,

                    reason:
                        "SL_AND_TP_SAME_CANDLE_SL_ASSUMED_FIRST"

                };

            }


            if (hitSL) {

                return {

                    result: "LOSS",

                    exitPrice:
                        trade.stopLoss,

                    exitIndex: i,

                    reason:
                        "STOP_LOSS"

                };

            }


            if (hitTP) {

                return {

                    result: "WIN",

                    exitPrice:
                        trade.takeProfit,

                    exitIndex: i,

                    reason:
                        "TAKE_PROFIT"

                };

            }

        }

    }


    /*
    If neither TP nor SL was reached,
    close at the final available candle.
    */

    const finalIndex =
        endIndex - 1;


    return {

        result: "TIME_EXIT",

        exitPrice:
            candles[finalIndex].close,

        exitIndex:
            finalIndex,

        reason:
            "MAX_BARS_REACHED"

    };

}


// ============================================================
// 4. CALCULATE TRADE P&L
// ============================================================

function calculatePnL(
    trade
) {

    const priceDifference =
        trade.direction === "BUY"

            ? trade.exitPrice -
              trade.entry

            : trade.entry -
              trade.exitPrice;


    return (
        priceDifference *
        trade.positionSize
    );

}


// ============================================================
// 5. BACKTEST
// ============================================================

function runBacktest(
    candles,
    options = {}
) {

    validateCandles(
        candles
    );


    const config = {

        ...BACKTEST_CONFIG,

        ...options

    };


    let capital =
        config.startingCapital;


    const trades = [];


    let nextAvailableIndex =
        100;


    /*
    We start at 100 so the engines have enough
    historical information.
    */

    for (
        let i = nextAvailableIndex;
        i < candles.length - 1;
        i++
    ) {

        /*
        ========================================================
        IMPORTANT
        ========================================================

        Only candles up to i are passed to Aureus.

        This prevents future information from entering
        the analysis.
        */

        const visibleCandles =
            candles.slice(
                0,
                i + 1
            );


        let analysis;


        try {

            analysis =
                analyzeMarket(
                    visibleCandles,
                    {

                        symbol:
                            options.symbol ||
                            "UNKNOWN",

                        timeframe:
                            options.timeframe ||
                            "UNKNOWN"

                    }
                );

        }

        catch (error) {

            continue;

        }


        /*
        Only take valid BUY/SELL decisions.
        */

        if (
            !analysis.validSetup
        ) {

            continue;

        }


        if (
            analysis.score <
            config.minimumScore
        ) {

            continue;

        }


        if (
            analysis.riskReward === null ||
            analysis.riskReward <
            config.minimumRiskReward
        ) {

            continue;

        }


        if (
            analysis.decision ===
            "BUY" &&
            !config.allowLong
        ) {

            continue;

        }


        if (
            analysis.decision ===
            "SELL" &&
            !config.allowShort
        ) {

            continue;

        }


        /*
        ========================================================
        CREATE TRADE
        ========================================================
        */

        const entry =
            analysis.entry;


        const stopLoss =
            analysis.stopLoss;


        const takeProfit =
            analysis.takeProfit;


        if (
            entry === null ||
            stopLoss === null ||
            takeProfit === null
        ) {

            continue;

        }


        const positionSize =
            calculatePositionSize(
                capital,
                entry,
                stopLoss,
                config.riskPerTradePercent
            );


        if (
            positionSize <= 0
        ) {

            continue;

        }


        const trade = {

            tradeNumber:
                trades.length + 1,

            symbol:
                options.symbol ||
                "UNKNOWN",

            timeframe:
                options.timeframe ||
                "UNKNOWN",

            entryIndex:
                i,

            entryTime:
                candles[i].timestamp ||
                null,

            direction:
                analysis.decision,

            entry,

            stopLoss,

            takeProfit,

            riskReward:
                analysis.riskReward,

            score:
                analysis.score,

            structure:
                analysis.structure,

            liquiditySweep:
                Boolean(
                    analysis.latestSweep
                ),

            orderBlock:
                Boolean(
                    analysis.orderBlock
                ),

            fvg:
                Boolean(
                    analysis.fvg
                ),

            positionSize,

            capitalBefore:
                capital

        };


        /*
        ========================================================
        FIND EXIT
        ========================================================
        */

        const outcome =
            checkTradeResult(
                candles,
                i,
                trade
            );


        trade.result =
            outcome.result;


        trade.exitPrice =
            outcome.exitPrice;


        trade.exitIndex =
            outcome.exitIndex;


        trade.exitTime =
            candles[
                outcome.exitIndex
            ].timestamp ||
            null;


        trade.exitReason =
            outcome.reason;


        /*
        ========================================================
        P&L
        ========================================================
        */

        trade.pnl =
            calculatePnL(
                trade
            );


        trade.rMultiple =
            trade.pnl /
            (
                Math.abs(
                    trade.entry -
                    trade.stopLoss
                ) *
                trade.positionSize
            );


        capital +=
            trade.pnl;


        trade.capitalAfter =
            capital;


        trades.push(
            trade
        );


        /*
        Jump forward to after the trade.

        This prevents Aureus from opening
        overlapping positions during the same trade.
        */

        i =
            Math.max(
                i,
                outcome.exitIndex
            );

    }


    /*
    ========================================================
    PERFORMANCE
    ========================================================
    */

    const performance =
        calculatePerformance(
            trades,
            config.startingCapital,
            capital
        );


    return {

        config,

        trades,

        performance

    };

}


// ============================================================
// 6. PERFORMANCE STATISTICS
// ============================================================

function calculatePerformance(
    trades,
    startingCapital,
    endingCapital
) {

    const totalTrades =
        trades.length;


    const wins =
        trades.filter(
            trade =>
                trade.result ===
                "WIN"
        );


    const losses =
        trades.filter(
            trade =>
                trade.result ===
                "LOSS"
        );


    const timeExits =
        trades.filter(
            trade =>
                trade.result ===
                "TIME_EXIT"
        );


    const winningPnL =
        wins.reduce(
            (sum, trade) =>
                sum + trade.pnl,
            0
        );


    const losingPnL =
        losses.reduce(
            (sum, trade) =>
                sum + trade.pnl,
            0
        );


    const netProfit =
        endingCapital -
        startingCapital;


    const winRate =
        totalTrades > 0
            ? (
                wins.length /
                totalTrades
            ) * 100
            : 0;


    const averageWin =
        wins.length > 0
            ? winningPnL /
              wins.length
            : 0;


    const averageLoss =
        losses.length > 0
            ? Math.abs(
                losingPnL /
                losses.length
            )
            : 0;


    const profitFactor =
        losingPnL !== 0
            ? winningPnL /
              Math.abs(losingPnL)
            : Infinity;


    const expectancy =
        totalTrades > 0
            ? netProfit /
              totalTrades
            : 0;


    const rValues =
        trades.map(
            trade =>
                trade.rMultiple
        );


    const averageR =
        rValues.length > 0
            ? rValues.reduce(
                (sum, value) =>
                    sum + value,
                0
            ) /
              rValues.length
            : 0;


    /*
    MAX DRAWDOWN
    */

    let peak =
        startingCapital;


    let maxDrawdown =
        0;


    let maxDrawdownPercent =
        0;


    for (
        const trade of trades
    ) {

        if (
            trade.capitalAfter >
            peak
        ) {

            peak =
                trade.capitalAfter;

        }


        const drawdown =
            peak -
            trade.capitalAfter;


        const drawdownPercent =
            peak > 0
                ? (
                    drawdown /
                    peak
                ) * 100
                : 0;


        if (
            drawdown >
            maxDrawdown
        ) {

            maxDrawdown =
                drawdown;

        }


        if (
            drawdownPercent >
            maxDrawdownPercent
        ) {

            maxDrawdownPercent =
                drawdownPercent;

        }

    }


    /*
    CONSEcutive losses
    */

    let currentLossStreak = 0;

    let maxLossStreak = 0;


    for (
        const trade of trades
    ) {

        if (
            trade.result ===
            "LOSS"
        ) {

            currentLossStreak++;

            maxLossStreak =
                Math.max(
                    maxLossStreak,
                    currentLossStreak
                );

        }

        else {

            currentLossStreak = 0;

        }

    }


    return {

        startingCapital,

        endingCapital,

        netProfit,

        returnPercent:
            startingCapital !== 0
                ? (
                    netProfit /
                    startingCapital
                ) * 100
                : 0,

        totalTrades,

        wins:
            wins.length,

        losses:
            losses.length,

        timeExits:
            timeExits.length,

        winRate,

        averageWin,

        averageLoss,

        profitFactor,

        expectancy,

        averageR,

        maxDrawdown,

        maxDrawdownPercent,

        maxConsecutiveLosses:
            maxLossStreak

    };

}


// ============================================================
// 7. EXPORTS
// ============================================================

module.exports = {

    BACKTEST_CONFIG,

    calculatePositionSize,

    checkTradeResult,

    calculatePnL,

    calculatePerformance,

    runBacktest

};
