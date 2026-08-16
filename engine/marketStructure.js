class MarketStructure {

    analyze(candles, swings) {

        if (
            !candles ||
            candles.length < 5 ||
            !swings
        ) {

            return {
                direction: "NEUTRAL",
                state: "INSUFFICIENT_DATA",
                bos: false,
                choch: false
            };

        }


        const highs = swings.highs;
        const lows = swings.lows;


        if (
            highs.length < 2 ||
            lows.length < 2
        ) {

            return {
                direction: "NEUTRAL",
                state: "INSUFFICIENT_SWINGS",
                bos: false,
                choch: false
            };

        }


        const h1 =
            highs[highs.length - 2];

        const h2 =
            highs[highs.length - 1];

        const l1 =
            lows[lows.length - 2];

        const l2 =
            lows[lows.length - 1];


        const higherHigh =
            h2.price > h1.price;

        const higherLow =
            l2.price > l1.price;

        const lowerHigh =
            h2.price < h1.price;

        const lowerLow =
            l2.price < l1.price;


        let direction = "NEUTRAL";
        let state = "RANGE";


        if (
            higherHigh &&
            higherLow
        ) {

            direction = "BULLISH";
            state = "UPTREND";

        }


        if (
            lowerHigh &&
            lowerLow
        ) {

            direction = "BEARISH";
            state = "DOWNTREND";

        }


        return {

            direction,
            state,

            higherHigh,
            higherLow,

            lowerHigh,
            lowerLow,

            lastHigh: h2,
            lastLow: l2,

            bos: this.detectBOS(
                candles,
                direction,
                h2,
                l2
            ),

            choch: false

        };

    }


    detectBOS(
        candles,
        direction,
        high,
        low
    ) {

        const last =
            candles[candles.length - 1];


        if (
            direction === "BULLISH" &&
            last.close > high.price
        ) {

            return true;

        }


        if (
            direction === "BEARISH" &&
            last.close < low.price
        ) {

            return true;

        }


        return false;

    }

}


if (typeof module !== "undefined") {
    module.exports = MarketStructure;
}
