class SignalEngine {

    generate({
        technical,
        fundamental,
        news,
        risk,
        minimumScore = 75
    }) {

        const technicalScore =
            technical.score || 0;

        const fundamentalScore =
            fundamental.score || 0;


        let finalScore =
            technicalScore +
            fundamentalScore;


        finalScore =
            Math.max(
                0,
                Math.min(
                    100,
                    finalScore
                )
            );


        let decision = "WAIT";


        if (
            finalScore >= minimumScore &&
            risk.valid &&
            !news.avoidTrading
        ) {

            decision =
                technical.direction === "BUY"
                    ? "BUY"
                    : technical.direction === "SELL"
                        ? "SELL"
                        : "WAIT";

        }


        return {

            decision,

            score:
                finalScore,

            entry:
                risk.entry,

            stop:
                risk.stop,

            target:
                risk.target,

            rr:
                risk.rr

        };

    }

}


if (typeof module !== "undefined") {
    module.exports = SignalEngine;
}
