const AUREUS_CONFIG = {

    version: "1.0.0",

    risk: {
        riskPerTrade: 0.01,
        minimumRR: 2,
        maximumRR: 8
    },

    scoring: {
        minimumScore: 75,

        weights: {
            structure: 20,
            liquidity: 15,
            orderBlock: 15,
            fvg: 10,
            supplyDemand: 10,
            structureShift: 10,
            candleConfirmation: 10,
            riskReward: 10
        }
    },

    requirements: {
        structure: true,
        liquiditySweep: true,
        structureShift: true,
        candleConfirmation: false,
        minimumRR: true
    },

    timeframes: {
        macro: ["D1", "H4"],
        setup: ["H1", "M30"],
        execution: ["M15", "M5"]
    },

    markets: [
        "EUR/USD",
        "GBP/USD",
        "USD/JPY",
        "USD/CAD",
        "AUD/USD",
        "XAU/USD",
        "NAS100",
        "US30",
        "SPX500",
        "BTC/USD"
    ]

};


if (typeof module !== "undefined") {
    module.exports = AUREUS_CONFIG;
}
