/* AUREUS AI — Interactive chart layer */
(() => {
    "use strict";

    class AureusChart {
        constructor(containerId) {
            this.container = document.getElementById(containerId);
            this.chart = null;
            this.series = null;
            this.lastCandles = [];
            this.activeTf = "15min";
        }

        create() {
            if (!this.container || !window.LightweightCharts) return;
            this.container.innerHTML = "";
            this.chart = LightweightCharts.createChart(this.container, {
                layout: { background: { color: "#081018" }, textColor: "#8d99ab" },
                grid: { vertLines: { color: "rgba(255,255,255,0.025)" }, horzLines: { color: "rgba(255,255,255,0.025)" } },
                rightPriceScale: { borderColor: "rgba(255,255,255,0.08)" },
                timeScale: { borderColor: "rgba(255,255,255,0.08)", timeVisible: true, secondsVisible: false },
                crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
                handleScroll: true,
                handleScale: true
            });
            this.series = this.chart.addCandlestickSeries({
                upColor: "#35d49a",
                downColor: "#ff5f6d",
                borderVisible: false,
                wickUpColor: "#35d49a",
                wickDownColor: "#ff5f6d"
            });
            const resize = () => this.chart.resize(this.container.clientWidth, this.container.clientHeight);
            window.addEventListener("resize", resize);
            resize();
        }

        setCandles(candles, timeframe = this.activeTf) {
            if (!this.series || !Array.isArray(candles) || !candles.length) return;
            this.activeTf = timeframe;
            const clean = candles
                .filter(c => Number.isFinite(c.open) && Number.isFinite(c.high) && Number.isFinite(c.low) && Number.isFinite(c.close) && Number.isFinite(c.timestamp))
                .map(c => ({ time: Math.floor(c.timestamp / 1000), open: c.open, high: c.high, low: c.low, close: c.close }))
                .sort((a,b) => a.time - b.time);
            this.lastCandles = clean;
            this.series.setData(clean);
            this.chart.timeScale().fitContent();
        }
    }

    document.addEventListener("DOMContentLoaded", () => {
        const chart = new AureusChart("aureusChart");
        chart.create();
        window.aureusChart = chart;
    });
})();
