class SupplyDemandEngine {

    detect(candles) {

        if (
            !candles ||
            candles.length < 4
        ) {
            return [];
        }


        const zones = [];


        for (
            let i = 1;
            i < candles.length - 1;
            i++
        ) {

            const previous =
                candles[i - 1];

            const current =
                candles[i];

            const next =
                candles[i + 1];


            const currentRange =
                current.high -
                current.low;


            const nextRange =
                next.high -
                next.low;


            if (
                currentRange <= 0
            ) {
                continue;
            }


            if (
                next.close >
                current.high &&
                nextRange >
                currentRange * 1.2
            ) {

                zones.push({

                    type: "DEMAND",

                    high:
                        current.high,

                    low:
                        current.low,

                    index: i

                });

            }


            if (
                next.close <
                current.low &&
                nextRange >
                currentRange * 1.2
            ) {

                zones.push({

                    type: "SUPPLY",

                    high:
                        current.high,

                    low:
                        current.low,

                    index: i

                });

            }

        }


        return zones;

    }

}


if (typeof module !== "undefined") {
    module.exports = SupplyDemandEngine;
}
