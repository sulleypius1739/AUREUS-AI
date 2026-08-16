class CandlestickEngine {

    analyze(candles) {

        if (
            !candles ||
            candles.length < 2
        ) {

            return {
                confirmation: false,
                patterns: []
            };

        }


        const c =
            candles[candles.length - 1];


        const body =
            Math.abs(
                c.close - c.open
            );


        const range =
            c.high - c.low;


        if (range <= 0) {

            return {
                confirmation: false,
                patterns: []
            };

        }


        const upperWick =
            c.high -
            Math.max(
                c.open,
                c.close
            );


        const lowerWick =
            Math.min(
                c.open,
                c.close
            ) -
            c.low;


        const patterns = [];


        if (
            lowerWick >
            body * 2
        ) {

            patterns.push(
                "BULLISH_REJECTION"
            );

        }


        if (
            upperWick >
            body * 2
        ) {

            patterns.push(
                "BEARISH_REJECTION"
            );

        }


        const previous =
            candles[
                candles.length - 2
            ];


        if (
            c.close > c.open &&
            previous.close < previous.open &&
            c.close >= previous.open &&
            c.open <= previous.close
        ) {

            patterns.push(
                "BULLISH_ENGULFING"
            );

        }


        if (
            c.close < c.open &&
            previous.close > previous.open &&
            c.open >= previous.close &&
            c.close <= previous.open
        ) {

            patterns.push(
                "BEARISH_ENGULFING"
            );

        }


        return {

            confirmation:
                patterns.length > 0,

            patterns

        };

    }

}


if (typeof module !== "undefined") {
    module.exports = CandlestickEngine;
}
