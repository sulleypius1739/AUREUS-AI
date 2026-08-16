class PerformanceEngine {

    analyze(trades) {

        if (
            !trades ||
            trades.length === 0
        ) {

            return {

                totalTrades: 0,

                markets: {},

                directions: {},

                sessions: {},

                conditions: {}

            };

        }


        const result = {

            totalTrades:
                trades.length,

            markets: {},

            directions: {},

            conditions: {}

        };


        for (
            const trade of trades
        ) {

            const market =
                trade.market ||
                "UNKNOWN";


            if (
                !result.markets[market]
            ) {

                result.markets[market] = {

                    trades: 0,

                    wins: 0,

                    losses: 0,

                    totalR: 0

                };

            }


            const bucket =
                result.markets[market];


            bucket.trades++;

            bucket.totalR +=
                trade.r || 0;


            if (
                trade.r > 0
            ) {

                bucket.wins++;

            }
            else {

                bucket.losses++;

            }


            const direction =
                trade.direction ||
                "UNKNOWN";


            if (
                !result.directions[
                    direction
                ]
            ) {

                result.directions[
                    direction
                ] = {

                    trades: 0,

                    wins: 0,

                    totalR: 0

                };

            }


            result.directions[
                direction
            ].trades++;


            result.directions[
                direction
            ].totalR +=
                trade.r || 0;


            if (
                trade.r > 0
            ) {

                result.directions[
                    direction
                ].wins++;

            }

        }


        return result;

    }

}


if (typeof module !== "undefined") {
    module.exports = PerformanceEngine;
}
