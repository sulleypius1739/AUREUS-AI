class FundamentalData {

    async getMacroData() {

        return {

            inflation: null,

            employment: null,

            GDP: null,

            interestRates: null,

            bondYields: null,

            currencyStrength: null,

            status:
                "FUNDAMENTAL_PROVIDER_REQUIRED"

        };

    }

}


if (typeof module !== "undefined") {
    module.exports = FundamentalData;
}
