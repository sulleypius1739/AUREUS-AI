/*
============================================================
AUREUS AI — TRADE JOURNAL
============================================================
*/

const fs = require("fs");


const JOURNAL_FILE =
    "./data/tradeJournal.json";


function ensureDataFolder() {

    if (
        !fs.existsSync("./data")
    ) {

        fs.mkdirSync(
            "./data",
            {
                recursive: true
            }
        );

    }

}


function loadJournal() {

    ensureDataFolder();


    if (
        !fs.existsSync(
            JOURNAL_FILE
        )
    ) {

        return [];

    }


    const raw =
        fs.readFileSync(
            JOURNAL_FILE,
            "utf8"
        );


    if (!raw.trim()) {

        return [];

    }


    return JSON.parse(
        raw
    );

}


function saveJournal(
    trades
) {

    ensureDataFolder();


    fs.writeFileSync(

        JOURNAL_FILE,

        JSON.stringify(
            trades,
            null,
            2
        )

    );

}


function recordTrade(
    trade
) {

    const journal =
        loadJournal();


    journal.push({

        ...trade,

        journalId:
            Date.now(),

        recordedAt:
            new Date().toISOString()

    });


    saveJournal(
        journal
    );

}


function recordBacktest(
    backtest
) {

    const journal =
        loadJournal();


    for (
        const trade of
        backtest.trades
    ) {

        journal.push({

            ...trade,

            source:
                "BACKTEST",

            journalId:
                Date.now() +
                journal.length,

            recordedAt:
                new Date().toISOString()

        });

    }


    saveJournal(
        journal
    );

}


module.exports = {

    loadJournal,

    saveJournal,

    recordTrade,

    recordBacktest

};
