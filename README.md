# AUREUS AI

## Universal AI-Powered Market Intelligence & Trading System

Aureus AI is a multi-asset market analysis and trading research platform designed to continuously scan financial markets and identify high-quality trading opportunities using a combination of technical analysis, fundamental analysis, market structure, liquidity concepts, quantitative analysis, and historical performance data.

The system is designed to be universal rather than restricted to one trading pair.

It should search across available markets and determine which instruments currently provide the strongest valid setup.

---

# 1. Core Objective

Aureus AI should answer one fundamental question:

> "Across all available markets, where is there a technically and fundamentally aligned trading opportunity right now?"

The system should NOT force a trade.

If no market satisfies the required conditions, Aureus AI should return:

**NO TRADE**

Capital preservation is more important than generating a signal.

---

# 2. Supported Markets

The system should eventually scan multiple asset classes including:

### Forex
- EUR/USD
- GBP/USD
- USD/JPY
- USD/CHF
- AUD/USD
- NZD/USD
- USD/CAD
- EUR/GBP
- GBP/JPY
- EUR/JPY
- and other liquid pairs

### Metals
- XAU/USD
- XAG/USD

### Indices
- NAS100
- US30
- SPX500
- GER40
- UK100
- and other supported indices

### Other Markets

The architecture should allow future integration of:

- Stocks
- Commodities
- Futures
- Crypto
- ETFs

The scanner should rank opportunities across markets instead of assuming a particular instrument should be traded.

---

# 3. Top-Down Technical Analysis

Aureus AI should perform analysis from higher timeframes toward lower timeframes.

Example:

Daily
↓
4H
↓
1H
↓
15M
↓
5M

Higher timeframes establish the market context.

Lower timeframes are used for confirmation and execution.

---

# 4. Higher Timeframe Analysis

The system should identify:

- Overall market direction
- Market structure
- Swing highs and lows
- Support zones
- Resistance zones
- Supply zones
- Demand zones
- Order blocks
- Fair Value Gaps
- Imbalances
- Previous highs and lows
- Previous day high
- Previous day low
- Previous week high
- Previous week low
- Major liquidity pools
- Premium and discount areas
- Break of Structure (BOS)
- Change of Character (CHOCH)

The system should determine whether the higher-timeframe environment is:

- Bullish
- Bearish
- Neutral

---

# 5. Liquidity Analysis

Aureus AI should identify potential liquidity areas including:

- Equal highs
- Equal lows
- Previous highs
- Previous lows
- Session highs
- Session lows
- Buy-side liquidity
- Sell-side liquidity
- Stop-hunt areas
- Liquidity sweeps

A liquidity sweep should be treated as a confirmation event rather than automatically considered a trade signal.

---

# 6. Lower Timeframe Confirmation

After establishing the higher-timeframe bias, the system should search lower timeframes for confirmation.

Potential confirmations include:

- Liquidity sweep
- Rejection from key zone
- Break of Structure
- Change of Character
- Fair Value Gap formation
- Order block reaction
- Strong displacement
- Momentum confirmation
- Candlestick confirmation

Examples of candlestick confirmations:

- Engulfing candle
- Pin bar
- Hammer
- Shooting star
- Strong rejection candle
- Inside-bar breakout

Candlestick patterns should not be used independently.

They should be evaluated within the larger market context.

---

# 7. Technical Setup Requirements

A potential BUY setup may require conditions such as:

1. Higher-timeframe bullish bias
2. Price reaches a relevant demand/support area
3. Relevant liquidity exists
4. Liquidity sweep occurs
5. Market structure confirms bullish intent
6. Order block or FVG provides a valid entry area
7. Lower-timeframe confirmation occurs
8. Risk/reward is acceptable

A potential SELL setup follows the opposite logic.

These conditions should be configurable rather than permanently hard-coded.

---

# 8. Fundamental Analysis

Aureus AI should analyse macroeconomic conditions relevant to each instrument.

Important data includes:

- Interest rates
- Central bank decisions
- CPI
- PPI
- NFP
- Employment data
- GDP
- PMI
- Retail sales
- Unemployment
- Inflation expectations
- Consumer confidence
- Economic growth
- Bond yields
- Government bond markets
- Currency strength
- DXY
- Commodity relationships
- Central bank statements
- Monetary policy expectations

The system should distinguish between:

### Previous
Previously released value.

### Forecast
Market expectation.

### Actual
Released economic value.

The difference between actual and forecast should be considered when evaluating market reactions.

---

# 9. Fundamental Bias

For each instrument, Aureus AI should determine whether fundamentals are:

- Strongly bullish
- Bullish
- Neutral
- Bearish
- Strongly bearish

The fundamental bias should then be compared against the technical bias.

Example:

Technical = Bullish
Fundamental = Bullish

This produces strong alignment.

But:

Technical = Bullish
Fundamental = Bearish

should reduce the setup score and potentially invalidate the trade.

---

# 10. News Trading Engine

Aureus AI should have a dedicated news-analysis component.

Before major economic releases, the system should analyse:

- Event importance
- Previous result
- Forecast
- Market expectations
- Historical reactions
- Current market positioning where data is available
- Volatility
- Technical structure
- Existing liquidity
- Distance to important technical levels

The system should determine whether trading around the release is:

- Avoid
- High Risk
- Possible
- Strong Opportunity

The system should NOT automatically assume that a better-than-forecast result guarantees a particular price movement.

Historical market reactions should be analysed.

---

# 11. Signal Generation

Every potential trade should receive a setup score.

Example:

Technical Structure       25/25
Higher-Timeframe Bias     15/15
Liquidity                 15/15
Entry Confirmation        15/15
Fundamentals              15/15
Risk/Reward               10/10
News Environment           5/5

TOTAL                     100/100

The scoring system should be configurable and tested through backtesting.

A minimum score should be required before a signal is generated.

---

# 12. Trade Classification

Possible outputs:

### HIGH-CONVICTION BUY

### HIGH-CONVICTION SELL

### VALID BUY

### VALID SELL

### WATCHLIST

### NO TRADE

The system should be conservative.

A setup that does not meet the required conditions should not receive an artificial signal.

---

# 13. Entry, Stop Loss and Take Profit

For valid setups, Aureus AI should calculate:

- Entry zone
- Stop-loss level
- Take-profit levels
- Risk/reward ratio
- Distance to stop
- Distance to target
- Position size
- Maximum acceptable risk

The system should consider market structure when determining stops and targets.

Possible targets include:

- Liquidity pools
- Previous highs
- Previous lows
- Supply
- Demand
- Fair Value Gaps
- Major support/resistance
- Risk/reward targets

---

# 14. Universal Market Scanner

The scanner should continuously evaluate all available instruments.

Example:

GBP/USD       72/100
XAU/USD       86/100
NAS100        79/100
EUR/USD       51/100
USD/JPY       44/100
US30          68/100

The system should rank instruments by setup quality.

The highest-quality valid opportunity should be highlighted.

If nothing meets the minimum requirements:

NO TRADE

---

# 15. Trade Journal

Every decision made by Aureus AI should be recorded.

The journal should contain:

- Date
- Time
- Instrument
- Asset class
- Direction
- Timeframe
- Technical bias
- Fundamental bias
- Setup score
- Entry
- Stop loss
- Take profit
- Risk/reward
- Market conditions
- News conditions
- Reason for signal
- Screenshot/chart reference
- Result
- Profit/loss
- Maximum favourable excursion
- Maximum adverse excursion
- Reason for failure

The system should also record valid setups that were rejected.

This is important for understanding whether the filtering rules are working.

---

# 16. Backtesting

The strategy must be tested on historical data before live execution.

The backtesting system should support multiple years of historical data.

Target:

**At least 4 years of historical testing**

Metrics should include:

- Win rate
- Loss rate
- Profit factor
- Expectancy
- Average win
- Average loss
- Maximum drawdown
- Sharpe ratio
- Sortino ratio
- Number of trades
- Consecutive wins
- Consecutive losses
- Average R multiple
- Monthly performance
- Yearly performance
- Performance by instrument
- Performance by session
- Performance by setup type
- Performance around news events

---

# 17. Strategy Research

Aureus AI should record enough information to determine which conditions actually improve performance.

Examples:

Does a liquidity sweep improve win rate?

Does an FVG improve expectancy?

Does fundamental alignment improve performance?

Does trading during London outperform New York?

Does the strategy perform differently on gold compared with GBP/USD?

Does the strategy perform better when the Daily and 4H bias agree?

These questions should be answered using historical data rather than assumptions.

---

# 18. AI Improvement Layer

The AI component should analyse historical results and identify patterns.

It should help determine:

- Which setups perform best
- Which conditions produce unnecessary losses
- Which markets perform best
- Which sessions perform best
- Which news events should be avoided
- Which combinations of conditions produce the highest expectancy
- When the strategy should stand aside

The AI should assist strategy research rather than blindly changing trading rules.

All changes should be tested through backtesting before being considered for deployment.

---

# 19. Risk Management

Risk management is a core component of Aureus AI.

The system should support:

- Maximum risk per trade
- Maximum daily risk
- Maximum weekly risk
- Maximum number of simultaneous positions
- Maximum consecutive losses
- Maximum drawdown protection
- News-risk restrictions
- Correlation restrictions

The system should be able to prevent a trade even if the technical setup is valid when risk conditions are unacceptable.

---

# 20. Execution

The initial versions of Aureus AI will NOT automatically execute real trades.

Development stages:

### Stage 1
Analysis only.

### Stage 2
Signal generation.

### Stage 3
Paper trading.

### Stage 4
Historical backtesting.

### Stage 5
Forward testing.

### Stage 6
Broker integration.

### Stage 7
Optional automated execution with strict risk controls.

Automated execution should only be enabled after extensive testing.

---

# 21. Dashboard

The web dashboard should contain:

- Market Scanner
- Live Market Overview
- Technical Analysis
- Fundamental Analysis
- News Calendar
- Signals
- Trade Journal
- Backtesting
- Performance Analytics
- AI Research
- Settings

---

# 22. Technology

Initial prototype:

- HTML
- CSS
- JavaScript
- GitHub

Planned production architecture:

### Frontend
Next.js
TypeScript
Tailwind CSS

### Backend
Python
FastAPI

### Data Analysis
Python
Pandas
NumPy
Scikit-learn

### Database
PostgreSQL

### Backtesting
Python-based custom backtesting engine

### AI / Machine Learning
Python
Machine learning models where statistically justified

### Version Control
Git
GitHub

---

# 23. Development Philosophy

Aureus AI should be developed incrementally.

Every major strategy component must be:

1. Defined
2. Implemented
3. Tested
4. Backtested
5. Measured
6. Documented
7. Improved

The goal is not to create a bot that produces many trades.

The goal is to create a system that identifies high-quality opportunities while knowing when NOT to trade.

---

# 24. Long-Term Vision

Aureus AI should become a universal market intelligence system capable of scanning financial markets continuously and identifying the best risk-adjusted opportunities based on technical structure, fundamentals, liquidity, market conditions, news, and historical evidence.

The ultimate system should be able to say:

> "I analysed the available markets. These are the strongest opportunities, this is why they qualify, this is the risk, this is the expected reward, and these are the reasons I rejected everything else."

The system should prioritize evidence, testing, risk management, and disciplined execution over prediction.
