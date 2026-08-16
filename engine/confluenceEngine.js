class ConfluenceEngine {

    score(data) {

        let score = 0;

        const reasons = [];


        if (
            data.structure?.valid
        ) {

            score += 20;

            reasons.push(
                "Valid market structure"
            );

        }


        if (
            data.liquidity?.sweep
        ) {

            score += 15;

            reasons.push(
                "Liquidity sweep"
            );

        }


        if (
            data.orderBlock
        ) {

            score += 15;

            reasons.push(
                "Order block"
            );

        }


        if (
            data.fvg
        ) {

            score += 10;

            reasons.push(
                "Fair value gap"
            );

        }


        if (
            data.supplyDemand
        ) {

            score += 10;

            reasons.push(
                "Supply/demand zone"
            );

        }


        if (
            data.structureShift
        ) {

            score += 10;

            reasons.push(
                "Structure shift"
            );

        }


        if (
            data.candleConfirmation
        ) {

            score += 10;

            reasons.push(
                "Candlestick confirmation"
            );

        }


        if (
            data.rr >= 2
        ) {

            score += 10;

            reasons.push(
                "Acceptable risk/reward"
            );

        }


        return {

            score,

            reasons

        };

    }

}


if (typeof module !== "undefined") {
    module.exports = ConfluenceEngine;
}
