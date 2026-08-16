/*
============================================================
AUREUS AI — CHART ENGINE
============================================================
*/

let aureusChart = null;
let candleSeries = null;

function initializeChart(containerId) {

    const container =
        document.getElementById(containerId);

    if (!container) return;

    if (
        typeof LightweightCharts ===
        "undefined"
    ) {

        console.error(
            "Lightweight Charts library not loaded."
        );

        return;

    }

    aureusChart =
        LightweightCharts.createChart(
            container,
            {

                layout: {

                    background: {
                        color: "#090d14"
                    },

                    textColor: "#9aa4b2"

                },

                grid: {

                    vertLines: {
                        color: "#151b25"
                    },

                    horzLines: {
                        color: "#151b25"
                    }

                },

                width:
                    container.clientWidth,

                height: 500,

                timeScale: {

                    timeVisible: true,

                    secondsVisible: false

                }

            }
        );


    candleSeries =
        aureusChart.addCandlestickSeries({

            upColor: "#00c896",

            downColor: "#ff4d67",

            borderUpColor: "#00c896",

            borderDownColor: "#ff4d67",

            wickUpColor: "#00c896",

            wickDownColor: "#ff4d67"

        });


    window.addEventListener(
        "resize",
        () => {

            aureusChart.applyOptions({

                width:
                    container.clientWidth

            });

        }
    );

}


function loadChartData(
    candles
) {

    if (
        !candleSeries
    ) return;


    const formatted =
        candles.map(
            candle => ({

                time:
                    Math.floor(
                        new Date(
                            candle.timestamp
                        ).getTime()
                        / 1000
                    ),

                open:
                    candle.open,

                high:
                    candle.high,

                low:
                    candle.low,

                close:
                    candle.close

            })
        );


    candleSeries.setData(
        formatted
    );


    aureusChart.timeScale()
        .fitContent();

}


function clearChart() {

    if (
        candleSeries
    ) {

        candleSeries.setData([]);

    }

}


window.AureusChart = {

    initializeChart,

    loadChartData,

    clearChart

};
