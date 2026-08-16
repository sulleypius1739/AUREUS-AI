class NewsEngine {

    analyze(event = {}) {

        const result = {

            impact:
                event.impact || "UNKNOWN",

            surprise: null,

            bias: "NEUTRAL",

            avoidTrading: false

        };


        if (
            event.actual != null &&
            event.forecast != null
        ) {

            result.surprise =
                Number(event.actual) -
                Number(event.forecast);

        }


        if (
            result.surprise > 0
        ) {

            result.bias =
                "POSITIVE_SURPRISE";

        }


        if (
            result.surprise < 0
        ) {

            result.bias =
                "NEGATIVE_SURPRISE";

        }


        if (
            event.impact === "HIGH"
        ) {

            result.avoidTrading =
                true;

        }


        return result;

    }

}


if (typeof module !== "undefined") {
    module.exports = NewsEngine;
}
