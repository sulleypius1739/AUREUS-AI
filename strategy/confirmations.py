import numpy as np


class ConfirmationAnalyzer:
    """Causal candle/reversal confirmation layer.

    Vectorized implementation suitable for large M5 datasets.
    """

    def __init__(self, rejection_wick_ratio=1.5):
        self.rejection_wick_ratio = float(rejection_wick_ratio)

    def analyze(self, df):
        df = df.copy()

        o = df["open"].to_numpy(dtype=float)
        h = df["high"].to_numpy(dtype=float)
        l = df["low"].to_numpy(dtype=float)
        c = df["close"].to_numpy(dtype=float)
        n = len(df)

        be = np.zeros(n, dtype=bool)
        se = np.zeros(n, dtype=bool)

        if n >= 2:
            po = o[:-1]
            pc = c[:-1]
            co = o[1:]
            cc = c[1:]

            be[1:] = (
                (pc < po)
                & (cc > co)
                & (co <= pc)
                & (cc >= po)
            )

            se[1:] = (
                (pc > po)
                & (cc < co)
                & (co >= pc)
                & (cc <= po)
            )

        body = np.maximum(np.abs(c - o), 1e-12)
        upper = h - np.maximum(o, c)
        lower = np.minimum(o, c) - l

        br = (
            (lower >= body * self.rejection_wick_ratio)
            & (lower > upper)
        )
        sr = (
            (upper >= body * self.rejection_wick_ratio)
            & (upper > lower)
        )

        if "bullish_displacement" in df.columns:
            bullish_disp = df["bullish_displacement"].to_numpy(dtype=bool)
        else:
            bullish_disp = np.zeros(n, dtype=bool)

        if "bearish_displacement" in df.columns:
            bearish_disp = df["bearish_displacement"].to_numpy(dtype=bool)
        else:
            bearish_disp = np.zeros(n, dtype=bool)

        local_bull = np.zeros(n, dtype=bool)
        local_bear = np.zeros(n, dtype=bool)
        if n >= 2:
            local_bull[1:] = bullish_disp[1:] & (c[1:] > h[:-1])
            local_bear[1:] = bearish_disp[1:] & (c[1:] < l[:-1])

        df["bullish_engulfing"] = be
        df["bearish_engulfing"] = se
        df["bullish_rejection"] = br
        df["bearish_rejection"] = sr
        df["local_bullish_shift"] = local_bull
        df["local_bearish_shift"] = local_bear
        df["bullish_confirmation"] = be | br | local_bull
        df["bearish_confirmation"] = se | sr | local_bear
        return df
