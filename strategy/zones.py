import numpy as np
import pandas as pd


class ZoneAnalyzer:
    """Causal AUREUS V2 FVG, POI, order-block and zone-state engine."""

    def __init__(self, fvg_min_size=5.0, displacement_multiplier=1.5, baseline_window=20):
        self.fvg_min_size = float(fvg_min_size)
        self.displacement_multiplier = float(displacement_multiplier)
        self.baseline_window = int(baseline_window)
        if self.fvg_min_size < 0:
            raise ValueError("fvg_min_size must be >= 0")
        if self.baseline_window < 5:
            raise ValueError("baseline_window must be >= 5")

    def add_columns(self, df):
        df = df.copy()
        bool_cols = [
            "support", "resistance", "demand", "supply",
            "bullish_fvg", "bearish_fvg",
            "bullish_displacement", "bearish_displacement", "displacement",
            "bullish_order_block", "bearish_order_block",
            "bullish_order_block_available", "bearish_order_block_available",
            "bullish_order_block_fresh", "bearish_order_block_fresh",
            "bullish_order_block_retest", "bearish_order_block_retest",
            "bullish_poi", "bearish_poi",
            "bullish_poi_available", "bearish_poi_available",
            "bullish_poi_fresh", "bearish_poi_fresh",
            "bullish_poi_retest", "bearish_poi_retest",
            "demand_available", "supply_available",
        ]
        float_cols = [
            "bullish_fvg_size", "bearish_fvg_size",
            "bullish_ob_high", "bullish_ob_low", "bearish_ob_high", "bearish_ob_low",
            "bullish_poi_high", "bullish_poi_low", "bearish_poi_high", "bearish_poi_low",
            "bullish_poi_mid", "bearish_poi_mid",
            "active_bullish_zone_high", "active_bullish_zone_low",
            "active_bearish_zone_high", "active_bearish_zone_low",
            "retest_bullish_zone_high", "retest_bullish_zone_low",
            "retest_bearish_zone_high", "retest_bearish_zone_low",
        ]
        int_cols = [
            "bullish_ob_origin", "bearish_ob_origin",
            "bullish_poi_origin", "bearish_poi_origin",
        ]
        for c in bool_cols:
            if c not in df.columns:
                df[c] = False
        for c in float_cols:
            if c not in df.columns:
                df[c] = np.nan
        for c in int_cols:
            if c not in df.columns:
                df[c] = -1
        return df

    def detect_displacement(self, df):
        df = df.copy()
        o = df["open"].to_numpy(dtype=float)
        h = df["high"].to_numpy(dtype=float)
        l = df["low"].to_numpy(dtype=float)
        c = df["close"].to_numpy(dtype=float)
        rng = h - l
        baseline = pd.Series(rng).rolling(self.baseline_window, min_periods=8).median().shift(1).to_numpy()
        n = len(df)
        bull = np.zeros(n, dtype=bool)
        bear = np.zeros(n, dtype=bool)
        disp = np.zeros(n, dtype=bool)
        for i in range(n):
            if not np.isfinite(baseline[i]) or baseline[i] <= 0 or rng[i] <= 0:
                continue
            body_ratio = abs(c[i] - o[i]) / rng[i]
            if rng[i] >= baseline[i] * self.displacement_multiplier and body_ratio >= 0.55:
                disp[i] = True
                if c[i] > o[i]:
                    bull[i] = True
                elif c[i] < o[i]:
                    bear[i] = True
        df["bullish_displacement"] = bull
        df["bearish_displacement"] = bear
        df["displacement"] = disp
        return df

    def detect_fvg(self, df):
        df = df.copy()
        h = df["high"].to_numpy(dtype=float)
        l = df["low"].to_numpy(dtype=float)
        n = len(df)
        bull = np.zeros(n, dtype=bool)
        bear = np.zeros(n, dtype=bool)
        bs = np.zeros(n, dtype=float)
        rs = np.zeros(n, dtype=float)
        for i in range(2, n):
            bgap = l[i] - h[i - 2]
            rgap = l[i - 2] - h[i]
            if bgap > self.fvg_min_size:
                bull[i] = True
                bs[i] = bgap
            if rgap > self.fvg_min_size:
                bear[i] = True
                rs[i] = rgap
        df["bullish_fvg"] = bull
        df["bearish_fvg"] = bear
        df["bullish_fvg_size"] = bs
        df["bearish_fvg_size"] = rs
        return df

    def detect_order_blocks(self, df):
        df = df.copy()
        o = df["open"].to_numpy(dtype=float)
        h = df["high"].to_numpy(dtype=float)
        l = df["low"].to_numpy(dtype=float)
        c = df["close"].to_numpy(dtype=float)
        bull_disp = df["bullish_displacement"].to_numpy(dtype=bool)
        bear_disp = df["bearish_displacement"].to_numpy(dtype=bool)
        bull_fvg = df["bullish_fvg"].to_numpy(dtype=bool)
        bear_fvg = df["bearish_fvg"].to_numpy(dtype=bool)
        bull_bos = df["bullish_bos"].to_numpy(dtype=bool)
        bear_bos = df["bearish_bos"].to_numpy(dtype=bool)
        bull_choch = df["bullish_choch"].to_numpy(dtype=bool)
        bear_choch = df["bearish_choch"].to_numpy(dtype=bool)
        n = len(df)

        bo = np.zeros(n, dtype=bool); so = np.zeros(n, dtype=bool)
        bav = np.zeros(n, dtype=bool); sav = np.zeros(n, dtype=bool)
        bh = np.full(n, np.nan); bl = np.full(n, np.nan)
        sh = np.full(n, np.nan); sl = np.full(n, np.nan)
        borig = np.full(n, -1, dtype=int); sorig = np.full(n, -1, dtype=int)

        for i in range(1, n):
            # Bullish OB = last bearish candle before a strong bullish move,
            # with a local sell-side sweep, FVG/imbalance, and structural event.
            if bull_disp[i] and (bull_fvg[i] or bull_bos[i] or bull_choch[i]):
                for j in (i - 1, i - 2):
                    if j <= 0:
                        continue
                    if c[j] < o[j] and l[j] < l[j - 1]:
                        bo[i] = True; bav[i] = True; borig[i] = j
                        bh[i] = h[j]; bl[i] = l[j]
                        break

            # Bearish mirror.
            if bear_disp[i] and (bear_fvg[i] or bear_bos[i] or bear_choch[i]):
                for j in (i - 1, i - 2):
                    if j <= 0:
                        continue
                    if c[j] > o[j] and h[j] > h[j - 1]:
                        so[i] = True; sav[i] = True; sorig[i] = j
                        sh[i] = h[j]; sl[i] = l[j]
                        break

        df["bullish_order_block"] = bo
        df["bearish_order_block"] = so
        df["bullish_order_block_available"] = bav
        df["bearish_order_block_available"] = sav
        df["bullish_ob_high"] = bh; df["bullish_ob_low"] = bl
        df["bearish_ob_high"] = sh; df["bearish_ob_low"] = sl
        df["bullish_ob_origin"] = borig; df["bearish_ob_origin"] = sorig
        return df

    def detect_poi(self, df):
        df = df.copy()
        o = df["open"].to_numpy(dtype=float)
        h = df["high"].to_numpy(dtype=float)
        l = df["low"].to_numpy(dtype=float)
        c = df["close"].to_numpy(dtype=float)
        bull_disp = df["bullish_displacement"].to_numpy(dtype=bool)
        bear_disp = df["bearish_displacement"].to_numpy(dtype=bool)
        n = len(df)

        bull = np.zeros(n, dtype=bool); bear = np.zeros(n, dtype=bool)
        bav = np.zeros(n, dtype=bool); sav = np.zeros(n, dtype=bool)
        bh = np.full(n, np.nan); bl = np.full(n, np.nan)
        sh = np.full(n, np.nan); sl = np.full(n, np.nan)
        bmid = np.full(n, np.nan); smid = np.full(n, np.nan)
        borig = np.full(n, -1, dtype=int); sorig = np.full(n, -1, dtype=int)

        # Confirmation is written at the NEXT bar, because a POI cannot be
        # known until the sweep candle is followed by the expected rejection.
        for sweep in range(1, n - 1):
            confirm = sweep + 1

            # Bullish POI: sweep previous low, reclaim it, next candle remains
            # above the sweep low and displaces upward.
            if l[sweep] < l[sweep - 1] and c[sweep] > l[sweep - 1]:
                if l[confirm] >= l[sweep] and bull_disp[confirm]:
                    bull[confirm] = True; bav[confirm] = True; borig[confirm] = sweep
                    bh[confirm] = h[sweep]; bl[confirm] = l[sweep]
                    bmid[confirm] = (h[sweep] + l[sweep]) / 2.0

            # Bearish POI mirror.
            if h[sweep] > h[sweep - 1] and c[sweep] < h[sweep - 1]:
                if h[confirm] <= h[sweep] and bear_disp[confirm]:
                    bear[confirm] = True; sav[confirm] = True; sorig[confirm] = sweep
                    sh[confirm] = h[sweep]; sl[confirm] = l[sweep]
                    smid[confirm] = (h[sweep] + l[sweep]) / 2.0

        df["bullish_poi"] = bull
        df["bearish_poi"] = bear
        df["bullish_poi_available"] = bav
        df["bearish_poi_available"] = sav
        df["bullish_poi_high"] = bh; df["bullish_poi_low"] = bl
        df["bearish_poi_high"] = sh; df["bearish_poi_low"] = sl
        df["bullish_poi_mid"] = bmid; df["bearish_poi_mid"] = smid
        df["bullish_poi_origin"] = borig; df["bearish_poi_origin"] = sorig
        return df

    def _retest_events(self, df):
        df = df.copy()
        n = len(df)
        h = df["high"].to_numpy(dtype=float)
        l = df["low"].to_numpy(dtype=float)
        c = df["close"].to_numpy(dtype=float)
        o = df["open"].to_numpy(dtype=float)

        for col in ["bullish_poi_fresh", "bearish_poi_fresh", "bullish_order_block_fresh", "bearish_order_block_fresh"]:
            df[col] = False
        for col in ["bullish_poi_retest", "bearish_poi_retest", "bullish_order_block_retest", "bearish_order_block_retest"]:
            df[col] = False
        for col in [
            "active_bullish_zone_high", "active_bullish_zone_low",
            "active_bearish_zone_high", "active_bearish_zone_low",
            "retest_bullish_zone_high", "retest_bullish_zone_low",
            "retest_bearish_zone_high", "retest_bearish_zone_low",
        ]:
            df[col] = np.nan

        active = {"bull_poi": None, "bear_poi": None, "bull_ob": None, "bear_ob": None}

        for i in range(n):
            row = df.iloc[i]
            if bool(row["bullish_poi_available"]):
                active["bull_poi"] = (i, float(row["bullish_poi_high"]), float(row["bullish_poi_low"]))
            if bool(row["bearish_poi_available"]):
                active["bear_poi"] = (i, float(row["bearish_poi_high"]), float(row["bearish_poi_low"]))
            if bool(row["bullish_order_block_available"]):
                active["bull_ob"] = (i, float(row["bullish_ob_high"]), float(row["bullish_ob_low"]))
            if bool(row["bearish_order_block_available"]):
                active["bear_ob"] = (i, float(row["bearish_ob_high"]), float(row["bearish_ob_low"]))

            # Only later bars can retest a newly confirmed zone.
            for key, fresh_col, retest_col, direction in [
                ("bull_poi", "bullish_poi_fresh", "bullish_poi_retest", "bullish"),
                ("bear_poi", "bearish_poi_fresh", "bearish_poi_retest", "bearish"),
                ("bull_ob", "bullish_order_block_fresh", "bullish_order_block_retest", "bullish"),
                ("bear_ob", "bearish_order_block_fresh", "bearish_order_block_retest", "bearish"),
            ]:
                z = active[key]
                if z is None or i <= z[0]:
                    continue
                _, zhi, zlo = z
                touched = l[i] <= zhi and h[i] >= zlo
                if touched:
                    # First touch is the only fresh opportunity. The state is
                    # consumed immediately after this retest event.
                    df.at[df.index[i], retest_col] = True
                    if direction == "bullish":
                        df.at[df.index[i], "retest_bullish_zone_high"] = zhi
                        df.at[df.index[i], "retest_bullish_zone_low"] = zlo
                    else:
                        df.at[df.index[i], "retest_bearish_zone_high"] = zhi
                        df.at[df.index[i], "retest_bearish_zone_low"] = zlo
                    active[key] = None

            # Expose active zone bounds before the next bar consumes them.
            if active["bull_poi"] is not None:
                df.at[df.index[i], "active_bullish_zone_high"] = active["bull_poi"][1]
                df.at[df.index[i], "active_bullish_zone_low"] = active["bull_poi"][2]
                df.at[df.index[i], "bullish_poi_fresh"] = True
            if active["bull_ob"] is not None:
                df.at[df.index[i], "active_bullish_zone_high"] = active["bull_ob"][1]
                df.at[df.index[i], "active_bullish_zone_low"] = active["bull_ob"][2]
                df.at[df.index[i], "bullish_order_block_fresh"] = True
            if active["bear_poi"] is not None:
                df.at[df.index[i], "active_bearish_zone_high"] = active["bear_poi"][1]
                df.at[df.index[i], "active_bearish_zone_low"] = active["bear_poi"][2]
                df.at[df.index[i], "bearish_poi_fresh"] = True
            if active["bear_ob"] is not None:
                df.at[df.index[i], "active_bearish_zone_high"] = active["bear_ob"][1]
                df.at[df.index[i], "active_bearish_zone_low"] = active["bear_ob"][2]
                df.at[df.index[i], "bearish_order_block_fresh"] = True

        return df

    def detect_supply_demand(self, df):
        df = df.copy()
        df["demand"] = df["bullish_poi"].astype(bool) | df["bullish_order_block"].astype(bool)
        df["supply"] = df["bearish_poi"].astype(bool) | df["bearish_order_block"].astype(bool)
        df["demand_available"] = df["bullish_poi_available"].astype(bool) | df["bullish_order_block_available"].astype(bool)
        df["supply_available"] = df["bearish_poi_available"].astype(bool) | df["bearish_order_block_available"].astype(bool)
        return df

    def detect_support_resistance(self, df):
        df = df.copy()
        df["support"] = df["confirmed_swing_low"].astype(bool) if "confirmed_swing_low" in df.columns else False
        df["resistance"] = df["confirmed_swing_high"].astype(bool) if "confirmed_swing_high" in df.columns else False
        return df

    def analyze(self, df):
        required = ["open", "high", "low", "close"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError("Missing required zone columns: " + ", ".join(missing))
        df = self.add_columns(df.copy())
        df = self.detect_displacement(df)
        df = self.detect_fvg(df)
        df = self.detect_order_blocks(df)
        df = self.detect_poi(df)
        df = self._retest_events(df)
        df = self.detect_supply_demand(df)
        df = self.detect_support_resistance(df)
        return df
