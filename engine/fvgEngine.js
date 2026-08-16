class FVGEngine {

    detect(candles) {

        const gaps = [];


        if (
            !candles ||
            candles.length < 3
        ) {

            return gaps;

        }


        for (
            let i = 2;
            i < candles.length;
            i++
        ) {

            const a =
                candles[i - 2];

            const c =
                candles[i];


            if (
                a.high < c.low
            ) {

                gaps.push({

                    direction: "BULLISH",

                    lower: a.high,

                    upper: c.low,

                    index: i

                });

            }


            if (
                a.low > c.high
            ) {

                gaps.push({

                    direction: "BEARISH",

                    lower: c.high,

                    upper: a.low,

                    index: i

                });

            }

        }


        return gaps;

    }

}


if (typeof module !== "undefined") {
    module.exports = FVGEngine;
}
