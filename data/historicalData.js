class HistoricalData {

    constructor() {

        this.data = {};

    }


    load(
        symbol,
        timeframe,
        candles
    ) {

        if (
            !this.data[symbol]
        ) {

            this.data[symbol] = {};

        }


        this.data[symbol][
            timeframe
        ] = candles || [];

    }


    get(
        symbol,
        timeframe
    ) {

        return (
            this.data[symbol]?.[
                timeframe
            ] || []
        );

    }


    clear() {

        this.data = {};

    }

}


if (typeof module !== "undefined") {
    module.exports = HistoricalData;
}
