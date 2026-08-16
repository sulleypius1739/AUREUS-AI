/*
========================================================
AUREUS STRATEGY ENGINE
========================================================

Purpose:
Determine whether a market satisfies the Aureus
technical strategy.

IMPORTANT:
This is a research engine.
It does NOT place live trades.

Every decision should be explainable.
========================================================
*/


class AureusStrategyEngine {

    constructor(config = {}) {

        this.config = {

            minimumScore:
                config.minimumScore ?? 75,

            minimumRR:
                config.minimumRR ?? 2,

            requireLiquiditySweep:
                config.requireLiquiditySweep ?? true,

            requireStructure:
                config.requireStructure ?? true,

            requireConfirmation:
                config.requireConfirmation ?? true

        };

    }


    /*
    ====================================================
    MAIN ANALYSIS
    ====================================================
    */

    analyze(market) {

        const technical =
            this.evaluateTechnical(market);


        const risk =
            this.evaluateRisk(market);


        const finalScore =
            this.calculateScore(
                technical,
                risk
            );


        const qualified =
            this.qualifies(
                technical,
                risk,
                finalScore
            );


        return {

            market:
                market.symbol,

            timestamp:
                new Date().toISOString(),

            direction:
                technical.direction,

            score:
                finalScore,

            qualified,

            technical,

            risk,

            decision:
                qualified
                    ? technical.direction
                    : "WAIT"

        };

    }


    /*
    ====================================================
    TECHNICAL ENGINE
    ====================================================
    */

    evaluateTechnical(market) {

        const structure =
            this.detectStructure(
                market
            );


        const liquidity =
            this.detectLiquidity(
                market
            );


        const zones =
            this.detectZones(
                market
            );


        const confirmation =
            this.detectConfirmation(
                market
            );


        return {

            direction:
                structure.direction,

            structure,

            liquidity,

            zones,

            confirmation

        };

    }


    /*
    ====================================================
    STRUCTURE
    ====================================================
    */

    detectStructure(market) {

        /*
        Real swing detection will be implemented
        against OHLC data.

        For now the function expects the market object
        to eventually contain:

        market.swingHighs
        market.swingLows
        market.structure
        */


        const structure =
            market.structure
            ?? "NEUTRAL";


        let direction =
            "NEUTRAL";


        if (
            structure === "BULLISH"
        ) {

            direction =
                "BUY";

        }


        if (
            structure === "BEARISH"
        ) {

            direction =
                "SELL";

        }


        return {

            valid:
                structure !== "NEUTRAL",

            structure,

            direction

        };

    }


    /*
    ====================================================
    LIQUIDITY
    ====================================================
    */

    detectLiquidity(market) {

        return {

            sweep:
                market.liquiditySweep
                ?? false,

            type:
                market.liquidityType
                ?? null,

            level:
                market.liquidityLevel
                ?? null

        };

    }


    /*
    ====================================================
    ZONES
    ====================================================
    */

    detectZones(market) {

        return {

            orderBlock:
                market.orderBlock
                ?? null,

            fairValueGap:
                market.fvg
                ?? null,

            supplyDemand:
                market.supplyDemand
                ?? null

        };

    }


    /*
    ====================================================
    CONFIRMATION
    ====================================================
    */

    detectConfirmation(market) {

        return {

            structureShift:
                market.structureShift
                ?? false,

            candleConfirmation:
                market.candleConfirmation
                ?? false

        };

    }


    /*
    ====================================================
    RISK ENGINE
    ====================================================
    */

    evaluateRisk(market) {

        const entry =
            Number(
                market.entry
                ?? 0
            );


        const stop =
            Number(
                market.stop
                ?? 0
            );


        const target =
            Number(
                market.target
                ?? 0
            );


        if (
            !entry ||
            !stop ||
            !target
        ) {

            return {

                valid:
                    false,

                entry,
                stop,
                target,

                rr:
                    0

            };

        }


        const risk =
            Math.abs(
                entry - stop
            );


        const reward =
            Math.abs(
                target - entry
            );


        const rr =
            risk > 0
                ? reward / risk
                : 0;


        return {

            valid:
                rr >= this.config.minimumRR,

            entry,

            stop,

            target,

            rr

        };

    }


    /*
    ====================================================
    SCORE
    ====================================================
    */

    calculateScore(
        technical,
        risk
    ) {

        let score = 0;


        /*
        Structure
        */

        if (
            technical.structure.valid
        ) {

            score += 20;

        }


        /*
        Liquidity
        */

        if (
            technical.liquidity.sweep
        ) {

            score += 15;

        }


        /*
        Order block
        */

        if (
            technical.zones.orderBlock
        ) {

            score += 15;

        }


        /*
        FVG
        */

        if (
            technical.zones.fairValueGap
        ) {

            score += 10;

        }


        /*
        Supply / demand
        */

        if (
            technical.zones.supplyDemand
        ) {

            score += 10;

        }


        /*
        Structure shift
        */

        if (
            technical.confirmation
                .structureShift
        ) {

            score += 10;

        }


        /*
        Candle confirmation
        */

        if (
            technical.confirmation
                .candleConfirmation
        ) {

            score += 10;

        }


        /*
        Risk / reward
        */

        if (
            risk.valid
        ) {

            score += 10;

        }


        return score;

    }


    /*
    ====================================================
    QUALIFICATION
    ====================================================
    */

    qualifies(
        technical,
        risk,
        score
    ) {

        if (
            this.config.requireStructure &&
            !technical.structure.valid
        ) {

            return false;

        }


        if (
            this.config.requireLiquiditySweep &&
            !technical.liquidity.sweep
        ) {

            return false;

        }


        if (
            this.config.requireConfirmation &&
            !technical.confirmation
                .structureShift
        ) {

            return false;

        }


        if (
            !risk.valid
        ) {

            return false;

        }


        if (
            score <
            this.config.minimumScore
        ) {

            return false;

        }


        return true;

    }

}


/*
========================================================
EXPORT
========================================================
*/


if (
    typeof module !== "undefined"
) {

    module.exports =
        AureusStrategyEngine;

}
