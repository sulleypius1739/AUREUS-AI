class BacktestEngine {

    constructor(config = {}) {

        this.initialCapital =
            config.initialCapital ?? 10000;

        this.riskPercent =
            config.riskPercent ?? 1;

        this.minimumScore =
            config.minimumScore ?? 75;

    }


    run(candles, signalFunction) {

        if (
            !candles ||
            candles.length < 10
        ) {

            return {

                error:
                    "Insufficient historical data",

                trades: []

            };

        }


        let equity =
            this.initialCapital;


        let peak =
            equity;


        let maxDrawdown = 0;


        const trades = [];


        for (
            let i = 10;
            i < candles.length - 1;
            i++
        ) {

            const history =
                candles.slice(
                    0,
                    i + 1
                );


            const signal =
                signalFunction(
                    history,
                    i
                );


            if (
                !signal ||
                signal.decision === "WAIT"
            ) {

                continue;

            }


            const entry =
                Number(signal.entry);


            const stop =
                Number(signal.stop);


            const target =
                Number(signal.target);


            if (
                !entry ||
                !stop ||
                !target
            ) {

                continue;

            }


            const next =
                candles[i + 1];


            let result =
                null;


            if (
                signal.decision === "BUY"
            ) {

                if (
                    next.low <= stop
                ) {

                    result = -1;

                }
                else if (
                    next.high >= target
                ) {

                    result =
                        Math.abs(
                            target - entry
                        ) /
                        Math.abs(
                            entry - stop
                        );

                }

            }


            if (
                signal.decision === "SELL"
            ) {

                if (
                    next.high >= stop
                ) {

                    result = -1;

                }
                else if (
                    next.low <= target
                ) {

                    result =
                        Math.abs(
                            entry - target
                        ) /
                        Math.abs(
                            stop - entry
                        );

                }

            }


            if (
                result === null
            ) {

                continue;

            }


            const riskMoney =
                equity *
                (this.riskPercent / 100);


            const pnl =
                riskMoney *
                result;


            equity += pnl;


            peak =
                Math.max(
                    peak,
                    equity
                );


            const drawdown =
                (
                    peak - equity
                ) /
                peak;


            maxDrawdown =
                Math.max(
                    maxDrawdown,
                    drawdown
                );


            trades.push({

                index: i,

                direction:
                    signal.decision,

                entry,

                stop,

                target,

                r:
                    result,

                pnl,

                equity

            });

        }


        return {

            initialCapital:
                this.initialCapital,

            finalCapital:
                equity,

            trades,

            maxDrawdown,

            metrics:
                this.calculateMetrics(
                    trades,
                    equity,
                    maxDrawdown
                )

        };

    }


    calculateMetrics(
        trades,
        equity,
        maxDrawdown
    ) {

        if (
            trades.length === 0
        ) {

            return {

                totalTrades: 0,

                winRate: 0,

                profitFactor: 0,

                expectancy: 0,

                averageR: 0,

                netProfit:
                    equity -
                    this.initialCapital,

                maxDrawdown

            };

        }


        const winners =
            trades.filter(
                t => t.r > 0
            );


        const losers =
            trades.filter(
                t => t.r < 0
            );


        const grossProfit =
            winners.reduce(
                (sum, t) =>
                    sum + t.pnl,
                0
            );


        const grossLoss =
            Math.abs(
                losers.reduce(
                    (sum, t) =>
                        sum + t.pnl,
                    0
                )
            );


        const totalR =
            trades.reduce(
                (sum, t) =>
                    sum + t.r,
                0
            );


        return {

            totalTrades:
                trades.length,

            wins:
                winners.length,

            losses:
                losers.length,

            winRate:
                (
                    winners.length /
                    trades.length
                ) * 100,

            profitFactor:
                grossLoss > 0
                    ? grossProfit /
                      grossLoss
                    : Infinity,

            expectancy:
                totalR /
                trades.length,

            averageR:
                totalR /
                trades.length,

            netProfit:
                equity -
                this.initialCapital,

            maxDrawdown:
                maxDrawdown * 100

        };

    }

}


if (typeof module !== "undefined") {
    module.exports = BacktestEngine;
}
