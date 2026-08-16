class MarketData {

    constructor() {

        this.provider =
            "UNCONNECTED";

    }


    async getQuote(symbol) {

        /*
        Live provider will be connected here.

        DO NOT put private API keys in this file
        when this becomes a production application.
        */

        return {

            symbol,

            price: null,

            change: null,

            timestamp:
                new Date().toISOString(),

            status:
                "DATA_PROVIDER_REQUIRED"

        };

    }


    async getCandles(
        symbol,
        timeframe,
        start,
        end
    ) {

        return {

            symbol,

            timeframe,

            start,

            end,

            candles: [],

            status:
                "HISTORICAL_PROVIDER_REQUIRED"

        };

    }

}


if (typeof module !== "undefined") {
    module.exports = MarketData;
}
