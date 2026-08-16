class ConfirmationAnalyzer:

    def analyze_candles(self, df):

        df = df.copy()

        df["bullish_engulfing"] = False
        df["bearish_engulfing"] = False
        df["bullish_rejection"] = False
        df["bearish_rejection"] = False

        for i in range(1, len(df)):

            previous = df.iloc[i-1]
            current = df.iloc[i]

            previous_body = abs(
                previous["close"] - previous["open"]
            )

            current_body = abs(
                current["close"] - current["open"]
            )

            # Bullish engulfing
            if (
                previous["close"] < previous["open"]
                and
                current["close"] > current["open"]
                and
                current["open"] <= previous["close"]
                and
                current["close"] >= previous["open"]
            ):

                df.iloc[
                    i,
                    df.columns.get_loc(
                        "bullish_engulfing"
                    )
                ] = True

            # Bearish engulfing
            if (
                previous["close"] > previous["open"]
                and
                current["close"] < current["open"]
                and
                current["open"] >= previous["close"]
                and
                current["close"] <= previous["open"]
            ):

                df.iloc[
                    i,
                    df.columns.get_loc(
                        "bearish_engulfing"
                    )
                ] = True

            candle_range = (
                current["high"] - current["low"]
            )

            if candle_range <= 0:
                continue

            upper_wick = (
                current["high"]
                -
                max(current["open"], current["close"])
            )

            lower_wick = (
                min(current["open"], current["close"])
                -
                current["low"]
            )

            if lower_wick >= candle_range * 0.5:

                df.iloc[
                    i,
                    df.columns.get_loc(
                        "bullish_rejection"
                    )
                ] = True

            if upper_wick >= candle_range * 0.5:

                df.iloc[
                    i,
                    df.columns.get_loc(
                        "bearish_rejection"
                    )
                ] = True

        return df

    def analyze(self, df):

        return self.analyze_candles(df)
