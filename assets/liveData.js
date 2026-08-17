/*
 * AUREUS AI - Real Market Data Connector
 *
 * Provider: Twelve Data
 * - REST: latest prices + OHLC time series
 * - WebSocket: real-time price stream when the account/plan permits it
 *
 * No API key is hard-coded. The user enters it in the browser and it is
 * stored only in localStorage on this computer.
 *
 * This connector is DATA/ANALYSIS ONLY. It does not place or route trades.
 */

(() => {
    "use strict";

    const PROVIDER = "Twelve Data";
    const REST_BASE = "https://api.twelvedata.com";
    const WS_BASE = "wss://ws.twelvedata.com/v1/quotes/price";

    const SYMBOLS = {
        EURUSD: "EUR/USD",
        GBPUSD: "GBP/USD",
        USDJPY: "USD/JPY",
        AUDUSD: "AUD/USD",
        USDCAD: "USD/CAD",
        XAUUSD: "XAU/USD",
        NAS100: "NDX",
        SPX500: "SPX"
    };

    const state = {
        apiKey: localStorage.getItem("aureus_twelvedata_api_key") || "",
        socket: null,
        connected: false,
        subscribed: [],
        prices: new Map(),
        candles: new Map(),
        refreshTimer: null,
        quoteTimer: null
    };

    function tdSymbol(symbol) {
        const key = String(symbol || "").replace("/", "").toUpperCase();
        return SYMBOLS[key] || symbol;
    }

    function displaySymbol(symbol) {
        return String(symbol || "").replace("/", "").toUpperCase();
    }

    function setStatus(text, online = false) {
        document.querySelectorAll("[data-aureus-live-status]").forEach((el) => {
            el.textContent = text;
            el.classList.toggle("aureus-live-online", online);
        });
        const pill = document.getElementById("aureusLivePill");
        const label = document.getElementById("aureusLivePillText");
        if (label) label.textContent = text;
        if (pill) pill.classList.toggle("offline", !online);
    }

    function formatPrice(value) {
        if (!Number.isFinite(value)) return "—";
        if (value >= 1000) return value.toLocaleString(undefined, {maximumFractionDigits: 2});
        if (value >= 100) return value.toLocaleString(undefined, {maximumFractionDigits: 3});
        return value.toFixed(5);
    }

    function updateRows(symbol, price) {
        const clean = displaySymbol(symbol);
        document.querySelectorAll(".market-row").forEach((row) => {
            const el = row.querySelector(".symbol");
            if (!el) return;
            const rowSymbol = displaySymbol(el.textContent.trim());
            if (rowSymbol !== clean) return;

            const cells = row.children;
            if (cells.length >= 3) {
                const priceCell = cells[cells.length - 2];
                if (priceCell && !priceCell.querySelector(".signal")) {
                    priceCell.textContent = formatPrice(price);
                }
            }

            row.dataset.livePrice = String(price);
        });
    }

    function showError(message) {
        const el = document.getElementById("aureusLiveError");
        if (el) {
            el.textContent = message;
            el.style.display = "block";
        }
        console.warn("AUREUS LIVE DATA:", message);
    }

    function clearError() {
        const el = document.getElementById("aureusLiveError");
        if (el) el.style.display = "none";
    }

    async function api(path, params = {}) {
        if (!state.apiKey) throw new Error("Enter your Twelve Data API key first.");
        const url = new URL(`${REST_BASE}${path}`);
        Object.entries({ ...params, apikey: state.apiKey }).forEach(([key, value]) => {
            url.searchParams.set(key, value);
        });
        const response = await fetch(url.toString());
        const data = await response.json();
        if (!response.ok || data.status === "error" || data.code >= 400) {
            throw new Error(data.message || `HTTP ${response.status}`);
        }
        return data;
    }

    async function fetchPrice(symbol) {
        const td = tdSymbol(symbol);
        const data = await api("/price", { symbol: td, dp: 6 });
        const price = Number(data.price);
        if (!Number.isFinite(price)) throw new Error(`No valid price returned for ${td}`);
        state.prices.set(td, { price, timestamp: new Date().toISOString(), source: "REST" });
        updateRows(td, price);
        return price;
    }

    async function fetchSeries(symbol, interval, outputsize = 300) {
        const td = tdSymbol(symbol);
        const data = await api("/time_series", {
            symbol: td,
            interval,
            outputsize,
            timezone: "UTC",
            order: "asc",
            format: "JSON"
        });

        if (!Array.isArray(data.values)) {
            throw new Error(`No candle data returned for ${td} ${interval}`);
        }

        const candles = data.values.map((row) => ({
            timestamp: new Date(`${row.datetime.replace(" ", "T")}Z`).getTime(),
            open: Number(row.open),
            high: Number(row.high),
            low: Number(row.low),
            close: Number(row.close),
            volume: Number(row.volume || 0)
        })).filter((c) =>
            Number.isFinite(c.timestamp) &&
            Number.isFinite(c.open) &&
            Number.isFinite(c.high) &&
            Number.isFinite(c.low) &&
            Number.isFinite(c.close)
        );

        state.candles.set(`${td}:${interval}`, candles);
        const selected = document.getElementById("aureusLiveSymbol")?.value;
        const selectedTd = selected ? tdSymbol(selected) : null;
        const activeTf = document.querySelector("#aureusTfButtons .tf-btn.active")?.dataset.tf || "15min";
        if (window.aureusChart && selectedTd === td && interval === activeTf) {
            window.aureusChart.setCandles(candles, interval);
        }
        return candles;
    }

    function aggregateFiveToTen(candles) {
        const groups = new Map();
        for (const candle of candles) {
            const bucket = Math.floor(candle.timestamp / 600000) * 600000;
            if (!groups.has(bucket)) groups.set(bucket, []);
            groups.get(bucket).push(candle);
        }
        return [...groups.entries()].sort((a, b) => a[0] - b[0]).map(([timestamp, group]) => ({
            timestamp,
            open: group[0].open,
            high: Math.max(...group.map(x => x.high)),
            low: Math.min(...group.map(x => x.low)),
            close: group[group.length - 1].close,
            volume: group.reduce((sum, x) => sum + (x.volume || 0), 0)
        }));
    }

    function candleBias(candles, lookback = 50) {
        const data = candles.slice(-lookback);
        if (data.length < 8) return "NEUTRAL";
        const highs = [];
        const lows = [];
        for (let i = 2; i < data.length - 2; i++) {
            const h = data[i].high;
            const l = data[i].low;
            if (h > data[i - 1].high && h > data[i - 2].high && h > data[i + 1].high && h > data[i + 2].high) highs.push(h);
            if (l < data[i - 1].low && l < data[i - 2].low && l < data[i + 1].low && l < data[i + 2].low) lows.push(l);
        }
        if (highs.length < 2 || lows.length < 2) return "NEUTRAL";
        const hh = highs.at(-1) > highs.at(-2);
        const hl = lows.at(-1) > lows.at(-2);
        const lh = highs.at(-1) < highs.at(-2);
        const ll = lows.at(-1) < lows.at(-2);
        if (hh && hl) return "BULLISH";
        if (lh && ll) return "BEARISH";
        return "NEUTRAL";
    }

    function recentSweep(candles, direction, lookback = 12) {
        const data = candles.slice(-lookback);
        if (data.length < 4) return false;
        for (let i = 2; i < data.length; i++) {
            const previous = data[i - 1];
            const current = data[i];
            if (direction === "BULLISH") {
                if (current.low < previous.low && current.close > previous.low) return true;
            } else {
                if (current.high > previous.high && current.close < previous.high) return true;
            }
        }
        return false;
    }

    function momentumConfirmation(candles, direction) {
        const data = candles.slice(-5);
        if (data.length < 3) return false;
        const last = data.at(-1);
        const prev = data.at(-2);
        const range = Math.max(last.high - last.low, 1e-12);
        const body = Math.abs(last.close - last.open);
        const displacement = range > (prev.high - prev.low) * 1.35 && body / range >= 0.5;
        if (direction === "BULLISH") return displacement && last.close > prev.high;
        return displacement && last.close < prev.low;
    }

    function premiumDiscount(candles) {
        const data = candles.slice(-50);
        const hi = Math.max(...data.map(x => x.high));
        const lo = Math.min(...data.map(x => x.low));
        const mid = (hi + lo) / 2;
        const price = data.at(-1).close;
        return { price, mid, location: price <= mid ? "DISCOUNT" : "PREMIUM" };
    }

    async function buildTopDownSnapshot(symbol) {
        const daily = await fetchSeries(symbol, "1day", 120);
        const h4 = await fetchSeries(symbol, "4h", 200);
        const h1 = await fetchSeries(symbol, "1h", 250);
        const m15 = await fetchSeries(symbol, "15min", 250);
        const m5 = await fetchSeries(symbol, "5min", 400);
        const m10 = aggregateFiveToTen(m5);

        const dailyBias = candleBias(daily);
        const h4Bias = candleBias(h4);
        const h1Bias = candleBias(h1);
        const bias = dailyBias === h4Bias && h4Bias !== "NEUTRAL"
            ? h4Bias
            : "NEUTRAL";

        const lowerFrame = bias === "BULLISH" ? "BULLISH" : bias === "BEARISH" ? "BEARISH" : "NEUTRAL";
        const sweep15 = lowerFrame !== "NEUTRAL" && recentSweep(m15, lowerFrame);
        const sweep10 = lowerFrame !== "NEUTRAL" && recentSweep(m10, lowerFrame);
        const confirm15 = lowerFrame !== "NEUTRAL" && momentumConfirmation(m15, lowerFrame);
        const confirm10 = lowerFrame !== "NEUTRAL" && momentumConfirmation(m10, lowerFrame);
        const loc = premiumDiscount(h1);

        let entrySignal = "WAIT";
        if (bias !== "NEUTRAL" && h1Bias === bias) {
            if (bias === "BULLISH" && loc.location === "DISCOUNT" && (sweep15 || sweep10) && (confirm15 || confirm10)) {
                entrySignal = "BUY WATCH";
            }
            if (bias === "BEARISH" && loc.location === "PREMIUM" && (sweep15 || sweep10) && (confirm15 || confirm10)) {
                entrySignal = "SELL WATCH";
            }
        }

        return {
            symbol: tdSymbol(symbol),
            dailyBias,
            h4Bias,
            h1Bias,
            location: loc.location,
            price: loc.price,
            sweep15,
            sweep10,
            confirm15,
            confirm10,
            entrySignal,
            updated: new Date().toISOString()
        };
    }

    function renderSnapshot(snapshot) {
        renderIntegratedSnapshot(snapshot);
        let box = document.getElementById("aureusTopDownSnapshot");
        if (!box) return;
        const badge = snapshot.entrySignal.includes("BUY") ? "BUY WATCH" : snapshot.entrySignal.includes("SELL") ? "SELL WATCH" : "WAIT";
        box.innerHTML = `
            <div class="aureus-live-title">AUREUS TOP-DOWN • ${snapshot.symbol}</div>
            <div class="aureus-grid">
                <div><span>Daily</span><strong>${snapshot.dailyBias}</strong></div>
                <div><span>4H</span><strong>${snapshot.h4Bias}</strong></div>
                <div><span>1H</span><strong>${snapshot.h1Bias}</strong></div>
                <div><span>Location</span><strong>${snapshot.location}</strong></div>
            </div>
            <div class="aureus-signal ${badge.replace(" ", "-").toLowerCase()}">${badge}</div>
            <div class="aureus-small">15M sweep: ${snapshot.sweep15 ? "YES" : "NO"} · 10M sweep: ${snapshot.sweep10 ? "YES" : "NO"} · 15M confirm: ${snapshot.confirm15 ? "YES" : "NO"} · 10M confirm: ${snapshot.confirm10 ? "YES" : "NO"}</div>
            <div class="aureus-small">Updated ${new Date(snapshot.updated).toLocaleTimeString()}</div>
        `;
    }

    async function connectWebSocket() {
        if (!state.apiKey) throw new Error("Enter your Twelve Data API key first.");
        if (state.socket) state.socket.close();

        return new Promise((resolve, reject) => {
            const ws = new WebSocket(`${WS_BASE}?apikey=${encodeURIComponent(state.apiKey)}`);
            state.socket = ws;
            let settled = false;

            ws.onopen = () => {
                const symbols = Object.values(SYMBOLS).filter(x => x.includes("/")).join(",");
                ws.send(JSON.stringify({ action: "subscribe", params: { symbols } }));
                state.connected = true;
                state.subscribed = symbols.split(",");
                setStatus(`${PROVIDER} LIVE`, true);
                if (!settled) { settled = true; resolve(); }
            };

            ws.onmessage = (event) => {
                try {
                    const payload = JSON.parse(event.data);
                    if (payload.event === "price" && payload.symbol && payload.price !== undefined) {
                        const price = Number(payload.price);
                        if (Number.isFinite(price)) {
                            state.prices.set(payload.symbol, { price, timestamp: new Date().toISOString(), source: "WebSocket" });
                            updateRows(payload.symbol, price);
                        }
                    }
                } catch (error) {
                    console.warn("AUREUS live stream parse error", error);
                }
            };

            ws.onerror = () => {
                state.connected = false;
                if (!settled) { settled = true; reject(new Error("WebSocket connection failed or is not enabled for this API plan.")); }
            };

            ws.onclose = () => {
                state.connected = false;
                setStatus(`${PROVIDER} disconnected`, false);
            };
        });
    }

    async function refreshQuotes() {
        const symbols = ["EURUSD", "GBPUSD", "XAUUSD", "USDJPY", "AUDUSD", "USDCAD"];
        for (const symbol of symbols) {
            try { await fetchPrice(symbol); } catch (error) { console.warn(error.message); }
        }
    }


    function setBiasElement(id, value) {
        const el = document.getElementById(id);
        if (!el) return;
        const v = String(value || "NEUTRAL").toUpperCase();
        el.textContent = v;
        el.classList.remove("bias-bull", "bias-bear", "bias-neutral");
        el.classList.add(v === "BULLISH" ? "bias-bull" : v === "BEARISH" ? "bias-bear" : "bias-neutral");
    }

    function setEvidence(id, yes) {
        const el = document.getElementById(id);
        if (!el) return;
        el.textContent = yes ? "YES" : "NO";
        el.classList.toggle("yes", !!yes);
        el.classList.toggle("no", !yes);
    }

    function renderIntegratedSnapshot(snapshot) {
        setBiasElement("aureusDailyBias", snapshot.dailyBias);
        setBiasElement("aureusH4Bias", snapshot.h4Bias);
        setBiasElement("aureusH1Bias", snapshot.h1Bias);
        setBiasElement("mtfDaily", snapshot.dailyBias);
        setBiasElement("mtf4h", snapshot.h4Bias);
        setBiasElement("mtf1h", snapshot.h1Bias);
        setBiasElement("mtf15m", snapshot.sweep15 ? snapshot.bias : "WAIT");
        setBiasElement("mtf10m", snapshot.confirm10 ? snapshot.bias : "WAIT");
        const location = document.getElementById("aureusLocation");
        if (location) location.textContent = snapshot.location || "—";
        const decision = document.getElementById("aureusDecision");
        if (decision) {
            const signal = snapshot.entrySignal || "WAIT";
            decision.textContent = signal;
            decision.classList.remove("buy", "sell", "wait");
            decision.classList.add(signal.includes("BUY") ? "buy" : signal.includes("SELL") ? "sell" : "wait");
        }
        setEvidence("evidenceSweep15", snapshot.sweep15);
        setEvidence("evidenceSweep10", snapshot.sweep10);
        setEvidence("evidenceConfirm15", snapshot.confirm15);
        setEvidence("evidenceConfirm10", snapshot.confirm10);
        const bias = document.getElementById("aureusChartBias");
        if (bias) bias.textContent = snapshot.entrySignal || "WAIT";
        const symbol = document.getElementById("aureusChartSymbol");
        if (symbol) symbol.textContent = `${snapshot.symbol} · ${document.querySelector("#aureusTfButtons .tf-btn.active")?.textContent || "15M"}`;
    }

    async function refreshChart(symbol, interval) {
        clearError();
        try {
            let candles;
            if (interval === "10min") {
                const m5 = await fetchSeries(symbol, "5min", 400);
                candles = aggregateFiveToTen(m5);
            } else {
                candles = await fetchSeries(symbol, interval, interval === "1day" ? 120 : 300);
            }
            if (window.aureusChart) window.aureusChart.setCandles(candles, interval);
            const latest = candles?.at(-1);
            const price = latest?.close;
            const priceEl = document.getElementById("aureusChartPrice");
            if (priceEl && Number.isFinite(price)) priceEl.textContent = formatPrice(price);
            const meta = document.getElementById("aureusChartMeta");
            if (meta) meta.textContent = `Live candles • ${interval.toUpperCase()} • ${new Date(latest.timestamp).toLocaleString()}`;
        } catch (error) {
            showError(error.message);
            throw error;
        }
    }

    async function refreshSnapshot(symbol) {
        clearError();
        try {
            const snapshot = await buildTopDownSnapshot(symbol);
            renderSnapshot(snapshot);
            return snapshot;
        } catch (error) {
            showError(error.message);
            throw error;
        }
    }

    function buildPanel() {
        const keyInput = document.getElementById("aureusApiKey");
        const saveBtn = document.getElementById("aureusSaveKey");
        const symbolSelect = document.getElementById("aureusLiveSymbol");
        const refreshBtn = document.getElementById("aureusRefreshAnalysis");
        const tfButtons = document.querySelectorAll("#aureusTfButtons .tf-btn");
        if (!keyInput || !saveBtn || !symbolSelect || !refreshBtn) return;

        keyInput.value = state.apiKey;

        const updateStatusUi = (text, online) => {
            const pill = document.getElementById("aureusLivePill");
            const label = document.getElementById("aureusLivePillText");
            if (label) label.textContent = text;
            if (pill) pill.classList.toggle("offline", !online);
        };

        saveBtn.addEventListener("click", async () => {
            const key = keyInput.value.trim();
            if (!key) return showError("Enter your Twelve Data API key first.");
            state.apiKey = key;
            localStorage.setItem("aureus_twelvedata_api_key", key);
            clearError();
            try {
                await connectWebSocket();
                updateStatusUi("TWELVE DATA LIVE", true);
            } catch (error) {
                updateStatusUi("REST FALLBACK", false);
                showError(`${error.message} REST polling will still be used.`);
            }
            await refreshQuotes();
            await refreshChart(symbolSelect.value, document.querySelector("#aureusTfButtons .tf-btn.active")?.dataset.tf || "15min");
            await refreshSnapshot(symbolSelect.value);
        });

        refreshBtn.addEventListener("click", async () => {
            if (!state.apiKey) return showError("Connect live data first.");
            const symbol = symbolSelect.value;
            const interval = document.querySelector("#aureusTfButtons .tf-btn.active")?.dataset.tf || "15min";
            await refreshChart(symbol, interval);
            await refreshSnapshot(symbol);
        });

        symbolSelect.addEventListener("change", async () => {
            if (!state.apiKey) return;
            await refreshChart(symbolSelect.value, document.querySelector("#aureusTfButtons .tf-btn.active")?.dataset.tf || "15min");
            await refreshSnapshot(symbolSelect.value);
        });

        tfButtons.forEach((button) => {
            button.addEventListener("click", async () => {
                tfButtons.forEach(b => b.classList.remove("active"));
                button.classList.add("active");
                if (!state.apiKey) return;
                await refreshChart(symbolSelect.value, button.dataset.tf);
                const symbolEl = document.getElementById("aureusChartSymbol");
                if (symbolEl) symbolEl.textContent = `${tdSymbol(symbolSelect.value)} · ${button.textContent}`;
            });
        });

        if (state.apiKey) {
            setStatus(`${PROVIDER} ready`, false);
            updateStatusUi("KEY SAVED", false);
            refreshQuotes().catch(() => {});
        }
    }

    function startPolling() {
        clearInterval(state.quoteTimer);
        state.quoteTimer = setInterval(() => {
            if (state.apiKey && !state.connected) refreshQuotes().catch(() => {});
        }, 10000);

        clearInterval(state.refreshTimer);
        state.refreshTimer = setInterval(() => {
            const selected = document.getElementById("aureusLiveSymbol")?.value;
            if (state.apiKey && selected) refreshSnapshot(selected).catch(() => {});
        }, 60000);
    }

    window.AUREUSLiveData = {
        connect: connectWebSocket,
        fetchPrice,
        fetchSeries,
        buildTopDownSnapshot,
        refreshSnapshot,
        symbols: SYMBOLS,
        state
    };

    document.addEventListener("DOMContentLoaded", () => {
        buildPanel();
        setStatus("LIVE FEED OFFLINE", false);
        startPolling();
    });
})();
