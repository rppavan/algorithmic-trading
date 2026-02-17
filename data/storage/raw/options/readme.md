# 1-Minute Index Data – NIFTY & SENSEX (Upstox)

This directory contains mid-frequency (1-minute timeframe) historical index data for **NIFTY** and **SENSEX**, sourced via the **Upstox API**.

The dataset is intended for:

- Algorithmic trading research  
- Strategy backtesting  
- Intraday volatility studies  
- Portfolio simulations  
- Machine learning model training  

---

## Time Period Covered

- **Start Date:** October 03, 2024  
- **End Date:** February 10, 2026  
- **Total Duration:** ~16 Months (16 months + 7 days)

---

## Underlyings

- **NIFTY Index**
- **SENSEX Index**

---

## Timeframe

- **1-Minute Candlestick Data**

Each row represents one 1-minute candle.

---

## Data Access

[Access the dataset here](https://drive.google.com/drive/folders/1QM_NSWSF0ny5fv9BxPXmDxG6fh5BftRY?usp=sharing)

Further updates to the link will be done here only.

---

## Data Format

Each .csv file contains OHLCV data for a single index:

| Column | Description |
|--------|-------------|
| Date | Datetime of the data point |
| Open | Opening price |
| High | Highest price during the interval |
| Low | Lowest price during the interval |
| Close | Closing price |
| Volume | Volume traded during the interval |

---

## Timezone

All timestamps are in:

**IST (UTC +05:30)**

---

## Data Characteristics

- mid-frequency intraday index data  
- Suitable for:
  - Intraday backtesting  
  - Volatility modeling  
  - VWAP-based strategies  
  - Microstructure research  
  - Feature engineering for ML models  

---

## Data Source

**Upstox API**

---

## Notes

- Ensure proper timezone-aware parsing of timestamps.
- Handle missing minutes appropriately during backtesting.
- Volume may be zero for certain minutes.
- `oi` may be zero depending on index data availability.
- Recommended to validate trading session timings before analysis.

---

## Connect

[LinkedIn](https://www.linkedin.com/in/bh1rg1v/)
[Reddit](https://www.reddit.com/user/bh1rg1vr1m/)