class RiskEngine {

    calculate({
        entry,
        stop,
        target,
        accountBalance = 10000,
        riskPercent = 1
    }) {

        entry = Number(entry);
        stop = Number(stop);
        target = Number(target);


        if (
            !entry ||
            !stop ||
            !target
        ) {

            return {
                valid: false
            };

        }


        const riskDistance =
            Math.abs(
                entry - stop
            );


        const rewardDistance =
            Math.abs(
                target - entry
            );


        if (
            riskDistance <= 0
        ) {

            return {
                valid: false
            };

        }


        const rr =
            rewardDistance /
            riskDistance;


        const riskMoney =
            accountBalance *
            (riskPercent / 100);


        return {

            valid: true,

            entry,

            stop,

            target,

            riskDistance,

            rewardDistance,

            rr,

            riskMoney,

            positionRisk:
                riskMoney /
                riskDistance

        };

    }

}


if (typeof module !== "undefined") {
    module.exports = RiskEngine;
}
