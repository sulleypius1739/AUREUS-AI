class AureusStrategyEngine {

    constructor(config = {}) {

        this.minimumScore =
            config.minimumScore ?? 75;

        this.minimumRR =
            config.minimumRR ?? 2;

        this.requireLiquiditySweep =
            config.requireLiquiditySweep ?? true;

        this.requireStructure =
            config.requireStructure ?? true;

        this.requireStructureShift =
            config.requireStructureShift ?? true;

    }


    analyze(market) {

        const structure =
            market.structure || {
                direction: "NEUTRAL",
                valid: false
            };


        const liquidity =
            market.liquidity || {
                sweep: false
            };


        const orderBlock =
            market.orderBlock || null;


        const fvg =
            market.fvg || null;


        const supplyDemand =
            market.supplyDemand || null;


        const structureShift =
            market.structureShift || false;


        const candleConfirmation =
            market.candleConfirmation || false;


        const risk =
            market.risk || {
                valid: false,
                rr: 0
            };


        let score = 0;


        if (structure.valid)
            score += 20;

        if (liquidity.sweep)
            score += 15;

        if (orderBlock)
            score += 15;

        if (fvg)
            score += 10;

        if (supplyDemand)
            score += 10;

        if (structureShift)
            score += 10;

        if (candleConfirmation)
            score += 10;

        if (
            risk.rr >=
            this.minimumRR
        )
            score += 10;


        let qualified = true;


        if (
            this.requireStructure &&
            !structure.valid
        )
            qualified = false;


        if (
            this.requireLiquiditySweep &&
            !liquidity.sweep
        )
            qualified = false;


        if (
            this.requireStructureShift &&
            !structureShift
        )
            qualified = false;


        if (
            !risk.valid ||
            risk.rr < this.minimumRR
        )
            qualified = false;


        if (
            score <
            this.minimumScore
        )
            qualified = false;


        return {

            symbol:
                market.symbol,

            direction:
                structure.direction === "BULLISH"
                    ? "BUY"
                    : structure.direction === "BEARISH"
                        ? "SELL"
                        : "WAIT",

            score,

            qualified,

            decision:
                qualified
                    ? (
                        structure.direction === "BULLISH"
                            ? "BUY"
                            : "SELL"
                    )
                    : "WAIT",

            risk,

            reasons: {

                structure:
                    structure.valid,

                liquidity:
                    liquidity.sweep,

                orderBlock:
                    !!orderBlock,

                fvg:
                    !!fvg,

                supplyDemand:
                    !!supplyDemand,

                structureShift,

                candleConfirmation,

                riskReward:
                    risk.rr >= this.minimumRR

            }

        };

    }

}


if (typeof module !== "undefined") {
    module.exports = AureusStrategyEngine;
}
