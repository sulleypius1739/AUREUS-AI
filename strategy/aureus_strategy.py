"""
AUREUS AI
Core Strategy Decision Engine

The strategy follows:

1. Higher timeframe bias
2. Market structure
3. Key support/resistance
4. Supply/demand
5. Order blocks
6. Fair value gaps
7. Liquidity
8. Liquidity sweep
9. Lower timeframe confirmation
10. Candlestick confirmation
11. Fundamental bias
12. News/event risk
13. Entry
14. Stop loss
15. Take profit
"""

class AureusStrategy:

    def __init__(self):
        self.minimum_score = 8

    def evaluate(self, setup):

        score = 0
        reasons = []

        # -----------------------------
        # HIGHER TIMEFRAME
        # -----------------------------

        if setup.get("htf_bias") in ["bullish", "bearish"]:
            score += 1
            reasons.append("HTF bias identified")

        # -----------------------------
        # MARKET STRUCTURE
        # -----------------------------

        if setup.get("market_structure") == setup.get("htf_bias"):
            score += 1
            reasons.append("Market structure aligns with HTF bias")

        # -----------------------------
        # KEY LEVEL
        # -----------------------------

        if setup.get("key_level"):
            score += 1
            reasons.append("Price located at significant level")

        # -----------------------------
        # SUPPLY / DEMAND
        # -----------------------------

        if setup.get("supply_demand"):
            score += 1
            reasons.append("Supply/demand zone identified")

        # -----------------------------
        # ORDER BLOCK
        # -----------------------------

        if setup.get("order_block"):
            score += 1
            reasons.append("Order block identified")

        # -----------------------------
        # FVG
        # -----------------------------

        if setup.get("fvg"):
            score += 1
            reasons.append("Fair value gap identified")

        # -----------------------------
        # LIQUIDITY
        # -----------------------------

        if setup.get("liquidity"):
            score += 1
            reasons.append("Liquidity pool identified")

        # -----------------------------
        # LIQUIDITY SWEEP
        # -----------------------------

        if setup.get("liquidity_sweep"):
            score += 2
            reasons.append("Liquidity sweep confirmed")

        # -----------------------------
        # LOWER TIMEFRAME
        # -----------------------------

        if setup.get("ltf_confirmation"):
            score += 1
            reasons.append("Lower timeframe confirmation")

        # -----------------------------
        # CANDLESTICK
        # -----------------------------

        if setup.get("candle_confirmation"):
            score += 1
            reasons.append("Candlestick confirmation")

        # -----------------------------
        # FUNDAMENTALS
        # -----------------------------

        if setup.get("fundamental_bias") == setup.get("htf_bias"):
            score += 1
            reasons.append("Fundamental bias aligned")

        # -----------------------------
        # NEWS
        # -----------------------------

        if setup.get("news_risk") == "low":
            score += 1
            reasons.append("News risk acceptable")

        # -----------------------------
        # FINAL DECISION
        # -----------------------------

        if score >= self.minimum_score:

            direction = setup.get("htf_bias")

            return {
                "signal": direction,
                "score": score,
                "reasons": reasons
            }

        return {
            "signal": "WAIT",
            "score": score,
            "reasons": reasons
        }
