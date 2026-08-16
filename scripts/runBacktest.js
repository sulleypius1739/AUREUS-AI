/*
============================================================
AUREUS AI — BACKTEST RUNNER
============================================================
*/

const fs = require("fs");

const {
    runBacktest
} = require(
    "../engine/backtestEngine"
);


const {
    recordBacktest
} = require(
    "../engine/tradeJournal"
);


// ============================================================
// LOAD HISTORICAL DATA
// ============================================================

const file =
    process.argv[2];


if (!file) {

    console.log(
        "Usage:"
    );

    console.log(
        "node scripts/runBacktest.js data/XAUUSD.json"
    );

    process.exit(1);

}


if (
    !fs.existsSync(file)
) {

    console.error(
        `File not found: ${file}`
    );

    process.exit(1);

}


const candles =
    JSON.parse(
        fs.readFileSync(
            file,
            "utf8"
        )
    );


// ============================================================
// RUN
// ============================================================

console.log(
    "\n========================================"
);

console.log(
    "       AUREUS AI BACKTEST"
);

console.log(
    "========================================\n"
);


console.log(
    `Candles: ${candles.length}`
);


const result =
    runBacktest(
        candles,
        {

            symbol:
                "XAU/USD",

            timeframe:
                "1H"

        }
    );


// ============================================================
// DISPLAY RESULTS
// ============================================================

const p =
    result.performance;


console.log(
    "\nRESULTS"
);

console.log(
    "----------------------------------------"
);

console.log(
    `Starting Capital: $${p.startingCapital.toFixed(2)}`
);

console.log(
    `Ending Capital:   $${p.endingCapital.toFixed(2)}`
);

console.log(
    `Net Profit:       $${p.netProfit.toFixed(2)}`
);

console.log(
    `Return:            ${p.returnPercent.toFixed(2)}%`
);

console.log(
    `Total Trades:      ${p.totalTrades}`
);

console.log(
    `Wins:              ${p.wins}`
);

console.log(
    `Losses:            ${p.losses}`
);

console.log(
    `Time Exits:        ${p.timeExits}`
);

console.log(
    `Win Rate:          ${p.winRate.toFixed(2)}%`
);

console.log(
    `Average Win:       $${p.averageWin.toFixed(2)}`
);

console.log(
    `Average Loss:      $${p.averageLoss.toFixed(2)}`
);

console.log(
    `Profit Factor:     ${p.profitFactor.toFixed(2)}`
);

console.log(
    `Expectancy:        $${p.expectancy.toFixed(2)}`
);

console.log(
    `Average R:         ${p.averageR.toFixed(2)}R`
);

console.log(
    `Max Drawdown:      $${p.maxDrawdown.toFixed(2)}`
);

console.log(
    `Max Drawdown %:    ${p.maxDrawdownPercent.toFixed(2)}%`
);

console.log(
    `Max Loss Streak:   ${p.maxConsecutiveLosses}`
);


// ============================================================
// SAVE JOURNAL
// ============================================================

recordBacktest(
    result
);


console.log(
    "\nBacktest trades saved to trade journal."
);

console.log(
    "========================================\n"
);
