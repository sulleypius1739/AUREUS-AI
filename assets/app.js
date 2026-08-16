/*
============================================================
AUREUS AI — APPLICATION CONTROLLER
============================================================
*/

const AureusApp = {

    state: {

        selectedMarket:
            "XAU/USD",

        selectedTimeframe:
            "1H",

        marketBias:
            "NEUTRAL",

        signal:
            "WAIT",

        score:
            0,

        connected:
            false

    },


    markets: [

        {
            symbol:
                "XAU/USD",

            name:
                "Gold",

            category:
                "METALS",

            currency:
                "USD"

        },

        {
            symbol:
                "EUR/USD",

            name:
                "Euro / Dollar",

            category:
                "FOREX",

            currency:
                "EUR"

        },

        {
            symbol:
                "GBP/USD",

            name:
                "Pound / Dollar",

            category:
                "FOREX",

            currency:
                "GBP"

        },

        {
            symbol:
                "USD/JPY",

            name:
                "Dollar / Yen",

            category:
                "FOREX",

            currency:
                "JPY"

        },

        {
            symbol:
                "USD/CAD",

            name:
                "Dollar / Canadian",

            category:
                "FOREX",

            currency:
                "CAD"

        },

        {
            symbol:
                "AUD/USD",

            name:
                "Australian Dollar",

            category:
                "FOREX",

            currency:
                "AUD"

        },

        {
            symbol:
                "NAS100",

            name:
                "Nasdaq 100",

            category:
                "INDEX",

            currency:
                "USD"

        },

        {
            symbol:
                "US30",

            name:
                "Dow Jones",

            category:
                "INDEX",

            currency:
                "USD"

        },

        {
            symbol:
                "SPX500",

            name:
                "S&P 500",

            category:
                "INDEX",

            currency:
                "USD"

        },

        {
            symbol:
                "BTC/USD",

            name:
                "Bitcoin",

            category:
                "CRYPTO",

            currency:
                "USD"

        }

    ],


    init() {

        console.log(
            "AUREUS AI INITIALIZED"
        );

        this.setupNavigation();

        this.setupMarketCards();

        this.setupTimeframes();

        this.setupButtons();

        this.updateDashboard();

    },


    setupNavigation() {

        const navItems =
            document.querySelectorAll(
                "[data-page]"
            );


        navItems.forEach(
            item => {

                item.addEventListener(
                    "click",
                    event => {

                        event.preventDefault();

                        const page =
                            item.dataset.page;

                        this.showPage(
                            page
                        );

                    }
                );

            }
        );

    },


    showPage(page) {

        document
            .querySelectorAll(
                ".aureus-page"
            )
            .forEach(
                section => {

                    section.style.display =
                        "none";

                }
            );


        const target =
            document.getElementById(
                page
            );


        if (target) {

            target.style.display =
                "block";

        }


        document
            .querySelectorAll(
                "[data-page]"
            )
            .forEach(
                item => {

                    item.classList.remove(
                        "active"
                    );

                }
            );


        const active =
            document.querySelector(
                `[data-page="${page}"]`
            );


        if (active) {

            active.classList.add(
                "active"
            );

        }

    },


    setupMarketCards() {

        document
            .querySelectorAll(
                "[data-symbol]"
            )
            .forEach(
                card => {

                    card.addEventListener(
                        "click",
                        () => {

                            this.selectMarket(
                                card.dataset.symbol
                            );

                        }
                    );

                }
            );

    },


    selectMarket(
        symbol
    ) {

        this.state.selectedMarket =
            symbol;


        const market =
            this.markets.find(
                item =>
                    item.symbol ===
                    symbol
            );


        if (!market) return;


        const title =
            document.getElementById(
                "selectedMarket"
            );


        if (title) {

            title.textContent =
                market.symbol;

        }


        this.updateDashboard();


        this.showPage(
            "analysis"
        );

    },


    setupTimeframes() {

        document
            .querySelectorAll(
                "[data-timeframe]"
            )
            .forEach(
                button => {

                    button.addEventListener(
                        "click",
                        () => {

                            this.state
                                .selectedTimeframe =
                                button
                                .dataset
                                .timeframe;

                            this.updateDashboard();

                        }
                    );

                }
            );

    },


    setupButtons() {

        const scanButton =
            document.getElementById(
                "scanMarkets"
            );


        if (scanButton) {

            scanButton.addEventListener(
                "click",
                () => {

                    this.scanMarkets();

                }
            );

        }


        const refreshButton =
            document.getElementById(
                "refreshData"
            );


        if (refreshButton) {

            refreshButton.addEventListener(
                "click",
                () => {

                    this.refresh();

                }
            );

        }

    },


    scanMarkets() {

        console.log(
            "Aureus scanning all markets..."
        );


        const results =
            this.markets.map(
                market => ({

                    symbol:
                        market.symbol,

                    score:
                        Math.floor(
                            Math.random() *
                            101
                        ),

                    bias:
                        Math.random() >
                        0.5
                            ? "BULLISH"
                            : "BEARISH"

                })
            );


        results.sort(
            (a, b) =>
                b.score -
                a.score
        );


        console.table(
            results
        );


        this.renderScanResults(
            results
        );

    },


    renderScanResults(
        results
    ) {

        const container =
            document.getElementById(
                "scanResults"
            );


        if (!container) return;


        container.innerHTML =
            "";


        results.forEach(
            result => {

                const row =
                    document.createElement(
                        "div"
                    );


                row.className =
                    "scan-row";


                row.innerHTML = `

                    <span>
                        ${result.symbol}
                    </span>

                    <span>
                        ${result.bias}
                    </span>

                    <strong>
                        ${result.score}/100
                    </strong>

                `;


                row.onclick =
                    () => {

                        this.selectMarket(
                            result.symbol
                        );

                    };


                container.appendChild(
                    row
                );

            }
        );

    },


    updateDashboard() {

        const market =
            this.state.selectedMarket;


        const selected =
            document.getElementById(
                "selectedMarket"
            );


        if (selected) {

            selected.textContent =
                market;

        }


        const timeframe =
            document.getElementById(
                "selectedTimeframe"
            );


        if (timeframe) {

            timeframe.textContent =
                this.state
                    .selectedTimeframe;

        }

    },


    refresh() {

        console.log(
            "Refreshing Aureus..."
        );

        this.updateDashboard();

    }

};


document.addEventListener(
    "DOMContentLoaded",
    () => {

        AureusApp.init();

    }
);
