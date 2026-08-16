class NewsData {

    async getCalendar(
        start,
        end
    ) {

        return {

            start,

            end,

            events: [],

            status:
                "NEWS_PROVIDER_REQUIRED"

        };

    }


    compareActualForecast(
        actual,
        forecast
    ) {

        if (
            actual == null ||
            forecast == null
        ) {

            return null;

        }


        return (
            Number(actual) -
            Number(forecast)
        );

    }

}


if (typeof module !== "undefined") {
    module.exports = NewsData;
}
