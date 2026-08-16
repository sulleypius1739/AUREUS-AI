class NewsFilter:

    HIGH_IMPACT = "high"
    MEDIUM_IMPACT = "medium"
    LOW_IMPACT = "low"

    def __init__(self):

        self.events = []

    def add_event(
        self,
        timestamp,
        currency,
        impact,
        event,
        forecast=None,
        previous=None,
        actual=None
    ):

        self.events.append({

            "timestamp": timestamp,
            "currency": currency,
            "impact": impact,
            "event": event,
            "forecast": forecast,
            "previous": previous,
            "actual": actual

        })

    def get_events(self):

        return self.events

    def high_impact_events(self):

        return [
            event
            for event in self.events
            if event["impact"] == self.HIGH_IMPACT
        ]

    def event_risk(
        self,
        currency=None
    ):

        events = self.high_impact_events()

        if currency:

            events = [
                event
                for event in events
                if event["currency"] == currency
            ]

        if events:

            return "high"

        return "low"

    def fundamental_direction(
        self,
        actual,
        forecast
    ):

        if actual is None or forecast is None:

            return "unknown"

        if actual > forecast:

            return "positive"

        if actual < forecast:

            return "negative"

        return "neutral"
