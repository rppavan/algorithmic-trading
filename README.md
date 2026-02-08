## Repository Architecture

### **`broker/`** - Broker Integration
- **`shoonya/`** - Shoonya API implementation (basicfunctions.py, config.py)

### **`data/`** - Data Management
- **`fetchers/`** - Data fetching modules (equity, fundamentals, implied_volatility)
- **`storage/`** - Data storage with symbol files (BFO, BSE, NFO, NSE) and tokens.csv
  - **`raw/`** - Raw market data
  - **`processed/`** - Processed data

### **`projects/`** - Trading Projects
Individual trading projects and strategies:
- **`p1-stock-action-classification-markov/`** - Markov chain stock classification
- **`p2-rv-iv-analysis/`** - Realized vs Implied volatility analysis
- **`p3-automated-trading-bot/`** - Automated scalping bot

### **`backtesting/`** - Backtesting Modules
Backtesting implementations for each strategy:
- **`rv-iv-analysis/`** - Volatility analysis backtests with results
- **`scalper/`** - Scalper strategy backtests
- **`stock-action-classification-markov/`** - Markov model backtests

### **`forward-testing/`** - Forward Testing
Forward testing modules and results.

### **`live/`** - Live Trading
Live trading implementations and configurations.

### **`utilities/`** - Utility Scripts
- **`telegram_bot.py`** - Telegram notification bot

### **Root Files**
- **`requirements.txt`** - Python dependencies
- **`.env.example`** - Environment variables template
- **`.gitignore`** - Git ignore rules
- **`README.md`** - This file