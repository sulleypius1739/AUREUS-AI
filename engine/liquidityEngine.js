class LiquidityEngine {

    analyze(candles, swings) {

        if (
            !candles ||
            candles.length < 2 ||
            !swings
        ) {

            return {
                sweep: false,
                type: null
            };

        }


        const current =
            candles[candles.length - 1];


        const previousHigh =
            swings.highs.length
                ? swings.highs[
                    swings.highs.length - 1
                ]
                : null;


        const previousLow =
            swings.lows.length
                ? swings.lows[
                    swings.lows.length - 1
                ]
                : null;


        let sweep = false;
        let type = null;
        let level = null;


        if (
            previousHigh &&
            current.high > previousHigh.price &&
            current.close < previousHigh.price
        ) {

            sweep = true;
            type = "BUY_SIDE_LIQUIDITY";
            level = previousHigh.price;

        }


        if (
            previousLow &&
            current.low < previousLow.price &&
            current.close > previousLow.price
        ) {

            sweep = true;
            type = "SELL_SIDE_LIQUIDITY";
            level = previousLow.price;

        }


        return {
            sweep,
            type,
            level
        };

    }

}


if (typeof module !== "undefined") {
    module.exports = LiquidityEngine;
}
