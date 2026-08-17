import numpy as np
import pandas as pd


class MarketStructure:
    """
    AUREUS V2 causal structure model.

    A swing is only available at its confirmation candle.  A BOS/CHOCH can
    only break a swing level that was already known before the current close.
    Once a trend is established, the protected level is updated only by a
    subsequent continuation break, not by every internal retracement swing.
    """

    def __init__(self, swing_length=3):
        self.swing_length = int(swing_length)
        if self.swing_length < 1:
            raise ValueError("swing_length must be >= 1")

    def detect_swings(self, df):
        df = df.copy()
        n = self.swing_length
        length = len(df)
        highs = pd.to_numeric(df["high"], errors="coerce").to_numpy(dtype=float)
        lows = pd.to_numeric(df["low"], errors="coerce").to_numpy(dtype=float)

        swing_high = np.zeros(length, dtype=bool)
        swing_low = np.zeros(length, dtype=bool)
        confirmed_high = np.zeros(length, dtype=bool)
        confirmed_low = np.zeros(length, dtype=bool)
        high_price = np.full(length, np.nan)
        low_price = np.full(length, np.nan)
        high_anchor = np.full(length, -1, dtype=int)
        low_anchor = np.full(length, -1, dtype=int)

        for i in range(n, length - n):
            h = highs[i]
            l = lows[i]
            if not np.isfinite(h) or not np.isfinite(l):
                continue
            if h > highs[i - n:i].max() and h > highs[i + 1:i + n + 1].max():
                swing_high[i] = True
                c = i + n
                confirmed_high[c] = True
                high_price[c] = h
                high_anchor[c] = i
            if l < lows[i - n:i].min() and l < lows[i + 1:i + n + 1].min():
                swing_low[i] = True
                c = i + n
                confirmed_low[c] = True
                low_price[c] = l
                low_anchor[c] = i

        df["swing_high"] = swing_high
        df["swing_low"] = swing_low
        df["confirmed_swing_high"] = confirmed_high
        df["confirmed_swing_low"] = confirmed_low
        df["swing_high_confirmed"] = confirmed_high
        df["swing_low_confirmed"] = confirmed_low
        df["swing_high_price"] = high_price
        df["swing_low_price"] = low_price
        df["swing_high_anchor"] = high_anchor
        df["swing_low_anchor"] = low_anchor
        return df

    def _labels(self, df):
        n = len(df)
        labels = np.full(n, None, dtype=object)
        hp = df["swing_high_price"].to_numpy(dtype=float)
        lp = df["swing_low_price"].to_numpy(dtype=float)
        ch = df["confirmed_swing_high"].to_numpy(dtype=bool)
        cl = df["confirmed_swing_low"].to_numpy(dtype=bool)
        prev_h = None
        prev_l = None
        for i in range(n):
            if ch[i] and np.isfinite(hp[i]):
                if prev_h is not None:
                    labels[i] = "HH" if hp[i] > prev_h else "LH" if hp[i] < prev_h else None
                prev_h = hp[i]
            if cl[i] and np.isfinite(lp[i]):
                if labels[i] is None and prev_l is not None:
                    labels[i] = "HL" if lp[i] > prev_l else "LL" if lp[i] < prev_l else None
                prev_l = lp[i]
        return labels

    def classify_external_structure(self, df):
        df = df.copy()
        n = len(df)
        labels = self._labels(df)

        bullish_bos = np.zeros(n, dtype=bool)
        bearish_bos = np.zeros(n, dtype=bool)
        bullish_choch = np.zeros(n, dtype=bool)
        bearish_choch = np.zeros(n, dtype=bool)
        double_zone_breakout = np.zeros(n, dtype=bool)

        trend = np.full(n, "neutral", dtype=object)
        protected_high = np.full(n, np.nan)
        protected_low = np.full(n, np.nan)
        major_high = np.full(n, np.nan)
        major_low = np.full(n, np.nan)
        candidate_high = np.full(n, np.nan)
        candidate_low = np.full(n, np.nan)

        close = df["close"].to_numpy(dtype=float)
        hp = df["swing_high_price"].to_numpy(dtype=float)
        lp = df["swing_low_price"].to_numpy(dtype=float)
        ch = df["confirmed_swing_high"].to_numpy(dtype=bool)
        cl = df["confirmed_swing_low"].to_numpy(dtype=bool)

        high_history = []
        low_history = []
        known_high = np.nan
        known_low = np.nan
        broken_high = np.nan
        broken_low = np.nan
        state = "neutral"
        prot_h = np.nan
        prot_l = np.nan
        maj_h = np.nan
        maj_l = np.nan

        def last_low_before(index):
            vals = [price for j, price in low_history if j < index]
            return vals[-1] if vals else np.nan

        def last_high_before(index):
            vals = [price for j, price in high_history if j < index]
            return vals[-1] if vals else np.nan

        for i in range(n):
            if ch[i] and np.isfinite(hp[i]):
                known_high = float(hp[i])
                high_history.append((i, known_high))
            if cl[i] and np.isfinite(lp[i]):
                known_low = float(lp[i])
                low_history.append((i, known_low))

            # Establish initial directional state only from confirmed swing
            # progression; the current close is never used as a future label.
            if state == "neutral" and len(high_history) >= 2 and len(low_history) >= 2:
                hh = high_history[-1][1] > high_history[-2][1]
                hl = low_history[-1][1] > low_history[-2][1]
                lh = high_history[-1][1] < high_history[-2][1]
                ll = low_history[-1][1] < low_history[-2][1]
                if hh and hl:
                    state = "bullish"
                elif lh and ll:
                    state = "bearish"

            # A new close above the newest known high is a break only once.
            if np.isfinite(known_high) and close[i] > known_high and (not np.isfinite(broken_high) or known_high != broken_high):
                previous_state = state
                bullish_choch[i] = previous_state == "bearish"
                bullish_bos[i] = previous_state != "bearish"
                new_protected_low = last_low_before(i)
                if previous_state == "bullish" or previous_state == "neutral":
                    bullish_bos[i] = True
                if np.isfinite(new_protected_low):
                    prot_l = new_protected_low
                maj_h = known_high
                state = "bullish"
                broken_high = known_high
                broken_low = np.nan

                if len(high_history) >= 2 and close[i] > high_history[-2][1]:
                    double_zone_breakout[i] = True

            # A new close below the newest known low is a break only once.
            if np.isfinite(known_low) and close[i] < known_low and (not np.isfinite(broken_low) or known_low != broken_low):
                previous_state = state
                bearish_choch[i] = previous_state == "bullish"
                bearish_bos[i] = previous_state != "bullish"
                new_protected_high = last_high_before(i)
                if previous_state == "bearish" or previous_state == "neutral":
                    bearish_bos[i] = True
                if np.isfinite(new_protected_high):
                    prot_h = new_protected_high
                maj_l = known_low
                state = "bearish"
                broken_low = known_low
                broken_high = np.nan

                if len(low_history) >= 2 and close[i] < low_history[-2][1]:
                    double_zone_breakout[i] = True

            candidate_high[i] = known_high
            candidate_low[i] = known_low
            trend[i] = state
            protected_high[i] = prot_h
            protected_low[i] = prot_l
            major_high[i] = maj_h if np.isfinite(maj_h) else known_high
            major_low[i] = maj_l if np.isfinite(maj_l) else known_low

        df["structure"] = labels
        df["trend_state"] = trend
        df["structure_bias"] = trend
        df["bullish_bos"] = bullish_bos
        df["bearish_bos"] = bearish_bos
        df["bullish_choch"] = bullish_choch
        df["bearish_choch"] = bearish_choch
        df["double_zone_breakout"] = double_zone_breakout
        df["candidate_high"] = candidate_high
        df["candidate_low"] = candidate_low
        df["protected_high"] = protected_high
        df["protected_low"] = protected_low
        df["last_major_high"] = major_high
        df["last_major_low"] = major_low
        return df

    def analyze(self, df):
        missing = [c for c in ("high", "low", "close") if c not in df.columns]
        if missing:
            raise ValueError("Missing required market structure columns: " + ", ".join(missing))
        df = self.detect_swings(df.copy())
        df = self.classify_external_structure(df)
        bias = str(df["trend_state"].iloc[-1]) if len(df) else "neutral"
        return df, bias
