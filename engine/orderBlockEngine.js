class OrderBlockEngine {

    detect(candles, structure) {

        if (
            !candles ||
            candles.length < 5
        ) {

            return null;

        }


        const last =
            candles[candles.length - 1];

        const previous =
            candles[candles.length - 2];


        const displacement =
            Math.abs(
                last.close - last.open
            );


        const previousRange =
            Math.abs(
                previous.high - previous.low
            );


        if (
            previousRange === 0
        ) {

            return null;

        }


        const strongMove =
            displacement >
            previousRange * 1.3;


        if (!strongMove) {
            return null;
        }


        return {

            direction:
                last.close > last.open
                    ? "BULLISH"
                    : "BEARISH",

            high: previous.high,
            low: previous.low,

            index:
                candles.length - 2,

            strength:
                displacement /
                previousRange

        };

    }

}


if (typeof module !== "undefined") {
    module.exports = OrderBlockEngine;
}
