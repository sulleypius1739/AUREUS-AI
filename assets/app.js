/* =========================================================
   AUREUS AI — APPLICATION CONTROLLER
   ========================================================= */

document.addEventListener("DOMContentLoaded", () => {

    console.log("AUREUS AI initialized.");

    /* -----------------------------------------------------
       CLOCK
    ----------------------------------------------------- */

    function updateClock() {

        const clock =
            document.getElementById("marketClock");

        if (!clock) return;

        const now = new Date();

        clock.textContent =
            now.toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit"
            });
    }

    updateClock();

    setInterval(updateClock, 1000);


    /* -----------------------------------------------------
       MOBILE SIDEBAR
    ----------------------------------------------------- */

    const menuButton =
        document.getElementById("menuButton");

    const sidebar =
        document.getElementById("sidebar");

    if (menuButton && sidebar) {

        menuButton.addEventListener(
            "click",
            () => {

                sidebar.classList.toggle(
                    "sidebar-open"
                );

            }
        );

    }


    /* -----------------------------------------------------
       NAVIGATION
    ----------------------------------------------------- */

    const navigationButtons =
        document.querySelectorAll(
            "[data-section]"
        );

    const sections =
        document.querySelectorAll(
            ".app-section"
        );

    navigationButtons.forEach(button => {

        button.addEventListener(
            "click",
            () => {

                const target =
                    button.dataset.section;

                navigationButtons.forEach(
                    item =>
                        item.classList.remove(
                            "active"
                        )
                );

                button.classList.add(
                    "active"
                );


                sections.forEach(section => {

                    section.classList.remove(
                        "active-section"
                    );

                });


                const selected =
                    document.getElementById(
                        target
                    );

                if (selected) {

                    selected.classList.add(
                        "active-section"
                    );

                }


                if (window.innerWidth < 900) {

                    sidebar?.classList.remove(
                        "sidebar-open"
                    );

                }

            }
        );

    });


    /* -----------------------------------------------------
       MARKET SEARCH
    ----------------------------------------------------- */

    const searchInput =
        document.getElementById(
            "marketSearch"
        );

    const marketCards =
        document.querySelectorAll(
            ".market-card"
        );


    if (searchInput) {

        searchInput.addEventListener(
            "input",
            () => {

                const query =
                    searchInput.value
                        .toLowerCase()
                        .trim();


                marketCards.forEach(card => {

                    const text =
                        card.textContent
                            .toLowerCase();


                    card.style.display =
                        text.includes(query)
                            ? ""
                            : "none";

                });

            }
        );

    }


    /* -----------------------------------------------------
       MARKET CARDS
    ----------------------------------------------------- */

    marketCards.forEach(card => {

        card.addEventListener(
            "click",
            () => {

                const symbol =
                    card.dataset.symbol ||
                    card.querySelector(
                        ".market-symbol"
                    )?.textContent ||
                    "UNKNOWN";


                const selected =
                    document.getElementById(
                        "selectedMarket"
                    );


                if (selected) {

                    selected.textContent =
                        symbol;

                }


                const scanner =
                    document.getElementById(
                        "scanner"
                    );


                if (scanner) {

                    scanner.scrollIntoView({
                        behavior: "smooth"
                    });

                }

            }
        );

    });


    /* -----------------------------------------------------
       DEMO ANALYSIS
    ----------------------------------------------------- */

    const analyzeButton =
        document.getElementById(
            "analyzeButton"
        );


    if (analyzeButton) {

        analyzeButton.addEventListener(
            "click",
            () => {

                const result =
                    document.getElementById(
                        "analysisResult"
                    );


                if (!result) return;


                result.innerHTML = `
                    <div class="analysis-placeholder">
                        <div class="analysis-icon">◈</div>

                        <h3>
                            AUREUS ANALYSIS ENGINE
                        </h3>

                        <p>
                            Market analysis interface
                            is ready.
                        </p>

                        <div class="analysis-tags">
                            <span>STRUCTURE</span>
                            <span>LIQUIDITY</span>
                            <span>ORDER BLOCK</span>
                            <span>FVG</span>
                            <span>SUPPLY / DEMAND</span>
                            <span>RISK</span>
                            <span>FUNDAMENTALS</span>
                        </div>
                    </div>
                `;

            }
        );

    }


    /* -----------------------------------------------------
       BACKTEST DEMO BUTTON
    ----------------------------------------------------- */

    const backtestButton =
        document.getElementById(
            "runBacktest"
        );


    if (backtestButton) {

        backtestButton.addEventListener(
            "click",
            () => {

                const status =
                    document.getElementById(
                        "backtestStatus"
                    );


                if (status) {

                    status.textContent =
                        "Backtest engine ready — historical data provider required.";

                }

            }
        );

    }

});
