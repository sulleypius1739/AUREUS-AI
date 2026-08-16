class SwingDetector {

    constructor(leftBars = 2, rightBars = 2) {
        this.leftBars = leftBars;
        this.rightBars = rightBars;
    }


    detect(candles) {

        const highs = [];
        const lows = [];

        for (
            let i = this.leftBars;
            i < candles.length - this.rightBars;
            i++
        ) {

            const current = candles[i];

            let swingHigh = true;
            let swingLow = true;


            for (
                let j = 1;
                j <= this.leftBars;
                j++
            ) {

                if (
                    current.high <=
                    candles[i - j].high
                ) {
                    swingHigh = false;
                }

                if (
                    current.low >=
                    candles[i - j].low
                ) {
                    swingLow = false;
                }

            }


            for (
                let j = 1;
                j <= this.rightBars;
                j++
            ) {

                if (
                    current.high <=
                    candles[i + j].high
                ) {
                    swingHigh = false;
                }

                if (
                    current.low >=
                    candles[i + j].low
                ) {
                    swingLow = false;
                }

            }


            if (swingHigh) {

                highs.push({
                    index: i,
                    time: current.time,
                    price: current.high
                });

            }


            if (swingLow) {

                lows.push({
                    index: i,
                    time: current.time,
                    price: current.low
                });

            }

        }


        return {
            highs,
            lows
        };

    }

}


if (typeof module !== "undefined") {
    module.exports = SwingDetector;
}
