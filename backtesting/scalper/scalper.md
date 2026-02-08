# Scalping Trading Bot

## Overview
A high-frequency automated scalping bot that exploits market microstructure inefficiencies by analyzing real-time order flow imbalances. The system captures small price movements through sophisticated market depth analysis and lightning-fast execution.

## Core Strategy Logic

### 1. Market Microstructure Analysis
- **Real-time Order Flow**: WebSocket connection for sub-second market data
- **5-Level Market Depth**: Complete order book visibility (L2 data)
- **Institutional Footprints**: Tracks large order accumulation patterns

**Key Data Points:**
- Last Traded Price (LTP) - Current market price
- Total Buy/Sell Quantities - Overall market sentiment  
- Bid/Ask Levels 1-5 - Support/resistance zones
- Order Flow Imbalances - Directional pressure indicators

### 2. Advanced Signal Generation

#### Buy Signal Criteria
```
Buy Pressure: 70-95% of total volume
Order Book Ratio: Top 5 buy levels > 1.5x sell levels
Market Logic: Institutional accumulation with strong support
```

#### Sell Signal Criteria  
```
Sell Pressure: 70-95% of total volume
Order Book Ratio: Top 5 sell levels > 1.5x buy levels
Market Logic: Distribution phase with heavy resistance
```

#### Signal Processing
- **Multi-stock Analysis**: Simultaneous monitoring of entire universe
- **Strength Ranking**: Dominance percentage scoring (0-100%)
- **Best-of-breed Selection**: Only strongest signal gets executed
- **Adaptive Thresholds**: Configurable pressure bounds and multipliers

### 3. Risk Management Framework

#### Dynamic Position Sizing
- **Testing Mode**: Fixed 1 share per trade
- **Live Mode**: Percentage-based capital allocation
- **Balance Integration**: Real-time broker balance monitoring

#### Precision Risk Controls
- **Stop Loss**: 0.25% of entry price (tight risk control)
- **Take Profit**: 1.0% of entry price (4:1 reward ratio)
- **Tick-Perfect Pricing**: Exchange-compliant price rounding
- **Slippage Protection**: Market order execution with depth validation

#### Operational Safeguards
- **Daily Trade Limits**: Prevents overtrading and drawdown spirals
- **Connection Monitoring**: WebSocket health checks and reconnection
- **Order State Tracking**: Real-time fill/rejection handling
- **Emergency Exits**: Automatic position closure on system errors

### 4. Execution Architecture

#### Pre-Market Initialization
```
1. Load curated stock universe (high-volume, liquid stocks)
2. Establish WebSocket connection with error handling
3. Subscribe to L2 market depth for entire universe
4. Sync with market open (9:15 AM IST)
5. Initialize risk parameters and trade counters
```

#### Real-time Trading Engine
```
1. SCAN → Continuous market depth analysis across all stocks
2. RANK → Sort by signal strength (dominance percentage)
3. FILTER → Apply pressure thresholds and depth ratios
4. EXECUTE → Place market order with integrated stop-loss
5. MONITOR → Track order status and position management
```

#### Smart Order Management
- **Entry Logic**: Market orders for zero latency execution
- **Exit Strategy**: Bracket orders with automatic stop-loss
- **Feed Management**: Dynamic subscription/unsubscription
- **Error Recovery**: Automatic signal regeneration on rejections

### 5. Technical Features

#### Market Microstructure Edge
- **Order Flow Imbalance Detection**: Spots temporary supply/demand mismatches
- **Institutional Footprint Analysis**: Identifies large player accumulation/distribution
- **Multi-level Confirmation**: 5-level order book validation for signal quality
- **Pressure Gradient Analysis**: Measures momentum strength and sustainability

#### High-Performance Architecture
- **Sub-second Latency**: WebSocket-based real-time data processing
- **Concurrent Analysis**: Simultaneous multi-stock signal generation
- **Memory Efficient**: Optimized data structures for speed
- **Fault Tolerant**: Robust error handling and recovery mechanisms

#### Intelligent Automation
- **Adaptive Thresholds**: Configurable signal parameters
- **Smart Reconnection**: Automatic WebSocket recovery
- **Order State Machine**: Complete trade lifecycle management
- **Performance Logging**: Detailed execution and signal analytics

## Trading Philosophy

### Scalping Mastery
- **Speed is King**: Exploit microsecond price inefficiencies before they disappear
- **Liquidity Focus**: Trade only high-volume stocks with tight spreads
- **Momentum Surfing**: Ride institutional order flow waves
- **Quick Profits**: In-and-out execution minimizes market exposure

### Market Microstructure Advantage
- **Order Flow Reading**: Decode institutional buying/selling intentions
- **Depth Psychology**: Understand where big money is positioned
- **Imbalance Hunting**: Profit from temporary supply/demand disruptions
- **Tick-by-tick Edge**: Capture value from market maker inefficiencies

### Quantitative Edge
- **Statistical Validation**: Pressure thresholds based on historical analysis
- **Risk-Adjusted Returns**: Consistent 4:1 reward-to-risk ratios
- **Probability-based Entries**: Only trade highest-conviction signals
- **Systematic Execution**: Remove emotional bias through automation

## Risk Framework

### Market Risks
- **Latency Sensitivity**: Microsecond delays can impact profitability
- **Volatility Spikes**: Extreme market moves can cause slippage
- **Liquidity Gaps**: Low-volume periods reduce signal quality
- **Market Regime Changes**: Strategy performance varies with market conditions

### Technical Risks
- **Connection Failures**: WebSocket drops can miss critical signals
- **API Limitations**: Rate limits or broker downtime affect execution
- **Data Quality**: Feed delays or errors impact signal accuracy
- **System Resources**: High CPU/memory usage during market hours

### Operational Controls
- **Stock Universe**: Limited to liquid, high-volume securities only
- **Market Hours**: Active only during peak liquidity periods
- **Position Limits**: Maximum exposure caps prevent overconcentration
- **Performance Monitoring**: Real-time P&L and drawdown tracking

## Performance Metrics

### Key Performance Indicators
- **Win Rate**: Target >60% profitable trades
- **Risk-Reward**: Consistent 1:4 ratio (0.25% risk, 1% reward)
- **Sharpe Ratio**: Risk-adjusted return measurement
- **Maximum Drawdown**: Peak-to-trough loss control
- **Daily P&L**: Session-based profit/loss tracking
- **Signal Quality**: Dominance percentage distribution analysis

### Optimization Parameters
```python
# Signal Thresholds (configurable)
PRESSURE_LOWER_BOUND = 0.70  # Minimum pressure threshold
PRESSURE_UPPER_BOUND = 0.95  # Maximum pressure threshold  
DEPTH_MULTIPLIER = 1.50      # Order book dominance ratio

# Risk Management
STOP_LOSS_PCT = 0.0025       # 0.25% stop loss
TAKE_PROFIT_PCT = 0.01       # 1.0% take profit
MAX_TRADES_PER_DAY = 10      # Daily trade limit
```

### Strategy Tuning
- **Pressure Bounds**: Adjust based on market volatility
- **Depth Multiplier**: Fine-tune for different market regimes
- **Risk Percentages**: Scale based on account size and risk tolerance
- **Stock Universe**: Update based on liquidity and volume criteria
- **Time Filters**: Optimize for peak market activity periods

---

*Precision trading through market microstructure analysis*