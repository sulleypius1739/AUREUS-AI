# AUREUS V4 — Golden Scenario Testing

This folder contains synthetic M5 data designed to represent one bullish
A+ market-mechanics path:

4H bullish direction
-> fresh 1H bullish POI
-> 15M bearish internal pullback
-> 15M bullish market shift
-> 15M sell-side sweep
-> 10M bullish market shift
-> M5 execution inside the POI.

The purpose is NOT to prove profitability. The purpose is to prove that the
code can mechanically recognize one known situation before we run large
historical datasets.

Run:

    python scripts/run_scenario_tests.py

The test prints PASS/FAIL for each stage and whether an A+ BUY was generated.

Important: The current scenario is intentionally a golden-path test. If the
engine fails a stage, do not "fix the test" by changing the labels. Fix the
strategy logic so the code recognizes the market structure that the scenario
was designed to represent.
