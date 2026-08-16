/* =========================================================
   AUREUS AI — CHART CONTROLLER
   ========================================================= */

class AureusChart {

    constructor(containerId) {

        this.container =
            document.getElementById(
                containerId
            );

        this.chart = null;

        this.series = null;

    }


    create() {

        if (!this.container) {

            console.warn(
                "AUREUS chart container not found."
            );

            return;

        }


        /*
         * The real TradingView-style chart
         * will be connected once we add
         * the market-data provider.
         *
         * For now this creates the visual
         * chart area without requiring
         * paid market data.
         */

        this.container.innerHTML = `
            <div class="chart-placeholder">

                <div class="chart-placeholder-grid"></div>

                <div class="chart-placeholder-content">

                    <div class="chart-symbol">
                        XAU/USD
                    </div>

                    <div class="chart-price">
                        MARKET DATA OFFLINE
                    </div>

                    <p>
                        Connect a market-data provider
                        to display live candles.
                    </p>

                </div>

            </div>
        `;

    }


    setCandles(candles) {

        if (!candles || !candles.length) {

            return;

        }


        console.log(
            "Candles received:",
            candles.length
        );

    }


    clear() {

        if (this.container) {

            this.container.innerHTML = "";

        }

    }

}


/* ---------------------------------------------------------
   INITIALIZE CHART
--------------------------------------------------------- */

document.addEventListener(
    "DOMContentLoaded",
    () => {

        const chart =
            new AureusChart(
                "aureusChart"
            );

        chart.create();

        window.aureusChart =
            chart;

    }
);
