class FundamentalEngine {

    analyze(data = {}) {

        const result = {

            bias: "NEUTRAL",

            score: 0,

            factors: []

        };


        if (
            data.currencyStrength > 0
        ) {

            result.score += 10;

            result.factors.push(
                "Positive currency strength"
            );

        }


        if (
            data.currencyStrength < 0
        ) {

            result.score -= 10;

            result.factors.push(
                "Negative currency strength"
            );

        }


        if (
            data.rateExpectation > 0
        ) {

            result.score += 10;

            result.factors.push(
                "Hawkish rate expectation"
            );

        }


        if (
            data.rateExpectation < 0
        ) {

            result.score -= 10;

            result.factors.push(
                "Dovish rate expectation"
            );

        }


        if (
            result.score > 5
        ) {

            result.bias = "BULLISH";

        }


        if (
            result.score < -5
        ) {

            result.bias = "BEARISH";

        }


        return result;

    }

}


if (typeof module !== "undefined") {
    module.exports = FundamentalEngine;
}
