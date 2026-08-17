import math
import numpy as np

from strategy.market_structure import MarketStructure
from strategy.liquidity import LiquidityAnalyzer
from strategy.zones import ZoneAnalyzer
from strategy.confirmations import ConfirmationAnalyzer
from strategy.risk_management import RiskManager


class AureusStrategy:
    """
    AUREUS V2 — causal, sequence-based SMC strategy.

    The H1 dataset is treated as both context and execution timeframe because
    no lower-timeframe data is available. The lower-timeframe CHOCH concept is
    therefore represented by a conservative H1 confirmation proxy.
    """

    def __init__(
        self,
        minimum_score=7,
        risk_percent=1.0,
        minimum_rr=2.0,
        swing_length=3,
        equal_tolerance=20.0,
        fvg_min_size=5.0,
        require_liquidity_sweep=True,
        require_premium_discount=True,
        require_confirmation=True,
        max_sweep_age=120,
    ):
        self.minimum_score = int(minimum_score)
        self.require_liquidity_sweep = bool(require_liquidity_sweep)
        self.require_premium_discount = bool(require_premium_discount)
        self.require_confirmation = bool(require_confirmation)
        self.max_sweep_age = int(max_sweep_age)

        self.market_structure = MarketStructure(swing_length=swing_length)
        self.liquidity = LiquidityAnalyzer(
            swing_lookback=swing_length,
            equal_tolerance=equal_tolerance,
            minimum_separation=3,
            liquidity_expiry=max_sweep_age,
        )
        self.zones = ZoneAnalyzer(
            fvg_min_size=fvg_min_size,
            displacement_multiplier=1.5,
            baseline_window=20,
        )
        self.confirmations = ConfirmationAnalyzer(rejection_wick_ratio=1.5)
        self.risk = RiskManager(
            risk_percent=risk_percent,
            minimum_rr=minimum_rr,
            stop_buffer=2.0,
        )

    @staticmethod
    def _true(value):
        try:
            if value is None:
                return False
            if isinstance(value, float) and math.isnan(value):
                return False
            return bool(value)
        except Exception:
            return False

    def prepare(self, df):
        df = df.copy()
        df, bias = self.market_structure.analyze(df)
        df = self.liquidity.analyze(df)
        df = self.zones.analyze(df)
        df = self.confirmations.analyze(df)
        df = self._add_location_columns(df)
        return df, bias

    def _add_location_columns(self, df):
        df = df.copy()
        n = len(df)
        premium = np.zeros(n, dtype=bool)
        discount = np.zeros(n, dtype=bool)
        mid = np.full(n, np.nan)

        hi = df.get("last_major_high").to_numpy(dtype=float)
        lo = df.get("last_major_low").to_numpy(dtype=float)
        close = df["close"].to_numpy(dtype=float)

        for i in range(n):
            if np.isfinite(hi[i]) and np.isfinite(lo[i]) and hi[i] > lo[i]:
                m = (hi[i] + lo[i]) / 2.0
                mid[i] = m
                discount[i] = close[i] <= m
                premium[i] = close[i] >= m

        df["range_mid"] = mid
        df["discount"] = discount
        df["premium"] = premium
        return df

    def _recent_relevant_sweep(self, df, index, direction):
        start = max(0, index - self.max_sweep_age)
        col = "sell_side_sweep" if direction == "bullish" else "buy_side_sweep"
        vals = df[col].to_numpy(dtype=bool)
        return bool(vals[start:index].any())

    def _retest_type(self, row, direction):
        if direction == "bullish":
            if self._true(row.get("bullish_poi_retest")):
                return "Bullish POI", True
            if self._true(row.get("bullish_order_block_retest")):
                return "Bullish OB", True
        else:
            if self._true(row.get("bearish_poi_retest")):
                return "Bearish POI", True
            if self._true(row.get("bearish_order_block_retest")):
                return "Bearish OB", True
        return None, False

    def _target_from_known_levels(self, df, index, direction, entry):
        row = df.iloc[index]
        if direction == "bullish":
            protected = row.get("protected_high")
            if protected == protected and float(protected) > entry:
                return float(protected)
            for key in ("last_major_high", "candidate_high"):
                value = row.get(key)
                if value == value and float(value) > entry:
                    return float(value)
            source = df["swing_high_price"].to_numpy(dtype=float)
            flags = df["confirmed_swing_high"].to_numpy(dtype=bool)
            hist = [float(source[j]) for j in range(index + 1) if flags[j] and np.isfinite(source[j]) and float(source[j]) > entry]
            return min(hist) if hist else None
        protected = row.get("protected_low")
        if protected == protected and float(protected) < entry:
            return float(protected)
        for key in ("last_major_low", "candidate_low"):
            value = row.get(key)
            if value == value and float(value) < entry:
                return float(value)
        source = df["swing_low_price"].to_numpy(dtype=float)
        flags = df["confirmed_swing_low"].to_numpy(dtype=bool)
        hist = [float(source[j]) for j in range(index + 1) if flags[j] and np.isfinite(source[j]) and float(source[j]) < entry]
        return max(hist) if hist else None

    def score_candle(self, df, index):
        row = df.iloc[index]
        trend = str(row.get("trend_state", "neutral"))
        reasons = []

        if trend == "bullish":
            score = 2
            reasons.append("Bullish external structure")
            zone_name, has_retest = self._retest_type(row, "bullish")
            if not has_retest:
                return {"signal": "WAIT", "score": 0, "reasons": [], "direction": None}
            score += 3
            reasons.append(f"First retest of {zone_name}")

            sweep_ok = self._recent_relevant_sweep(df, index, "bullish")
            if sweep_ok:
                score += 2
                reasons.append("Prior sell-side liquidity sweep")
            elif self.require_liquidity_sweep:
                return {"signal": "WAIT", "score": 0, "reasons": [], "direction": None}

            confirm_ok = self._true(row.get("bullish_confirmation"))
            if confirm_ok:
                score += 2
                reasons.append("Bullish confirmation")
            elif self.require_confirmation:
                return {"signal": "WAIT", "score": 0, "reasons": [], "direction": None}

            if bool(row.get("discount", False)):
                score += 1
                reasons.append("Discount location")
            elif self.require_premium_discount:
                return {"signal": "WAIT", "score": 0, "reasons": [], "direction": None}

            if self._true(row.get("bullish_choch")) or self._true(row.get("bullish_bos")):
                score += 1
                reasons.append("Bullish structural confirmation")

            if score >= self.minimum_score:
                return {"signal": "BUY", "score": score, "reasons": reasons, "direction": "bullish"}

        if trend == "bearish":
            score = 2
            reasons.append("Bearish external structure")
            zone_name, has_retest = self._retest_type(row, "bearish")
            if not has_retest:
                return {"signal": "WAIT", "score": 0, "reasons": [], "direction": None}
            score += 3
            reasons.append(f"First retest of {zone_name}")

            sweep_ok = self._recent_relevant_sweep(df, index, "bearish")
            if sweep_ok:
                score += 2
                reasons.append("Prior buy-side liquidity sweep")
            elif self.require_liquidity_sweep:
                return {"signal": "WAIT", "score": 0, "reasons": [], "direction": None}

            confirm_ok = self._true(row.get("bearish_confirmation"))
            if confirm_ok:
                score += 2
                reasons.append("Bearish confirmation")
            elif self.require_confirmation:
                return {"signal": "WAIT", "score": 0, "reasons": [], "direction": None}

            if bool(row.get("premium", False)):
                score += 1
                reasons.append("Premium location")
            elif self.require_premium_discount:
                return {"signal": "WAIT", "score": 0, "reasons": [], "direction": None}

            if self._true(row.get("bearish_choch")) or self._true(row.get("bearish_bos")):
                score += 1
                reasons.append("Bearish structural confirmation")

            if score >= self.minimum_score:
                return {"signal": "SELL", "score": score, "reasons": reasons, "direction": "bearish"}

        return {"signal": "WAIT", "score": 0, "reasons": [], "direction": None}

    def generate_signal(self, df, index):
        if index < 0 or index >= len(df):
            return {"signal": "WAIT", "score": 0, "reasons": [], "direction": None}
        return self.score_candle(df, index)

    def analyze(self, df):
        df, bias = self.prepare(df)
        signals = []
        scores = []
        reasons = []
        for i in range(len(df)):
            result = self.generate_signal(df, i)
            signals.append(result["signal"])
            scores.append(result["score"])
            reasons.append(result["reasons"])
        df["aureus_signal"] = signals
        df["aureus_score"] = scores
        df["aureus_reasons"] = reasons
        return df, bias
