import pandas as pd
from datetime import datetime
from rv_iv_analysis import process_volatility_analysis
from track_prices import *
from utilities.telegram_bot import send_to_me
import time
import asyncio

# Trading window configuration
WINDOW_START = '00:00'
WINDOW_END = '15:31'

def fetch_straddle_data():
    """Fetch straddle data with retry logic"""
    straddle = None
    start_time = time.time()
    while straddle is None:
        straddle = calculate_long_straddle_price()
        
        if straddle is None:
            if time.time() - start_time >= 600:
                print("It is taking too long to fetch the data. Exiting the script.")
                asyncio.run(send_to_me("It is taking too long to fetch the data. Exiting the script."))
                exit()
            else:
                time.sleep(3)
    return straddle

def calculate_profit_metrics(nifty_df, ltp, ce_strike, pe_strike, total_cost):
    """Calculate peak moneyness and profit columns"""
    val = (nifty_df['Peak Abs Change Percentage'] / 100) * ltp
    call = val + ltp
    put = ltp - val
    nifty_df['Peak Moneyness'] = pd.concat([call - ce_strike, pe_strike - put], axis=1).min(axis=1)
    nifty_df['Peak Profit'] = (nifty_df['Peak Moneyness'] - total_cost) / total_cost * 100
    return nifty_df

def create_messages(straddle, nifty_df, today, expiry):
    """Create formatted messages for telegram"""
    df_filtered = nifty_df[['Percentile', 'Peak Abs Change Percentage', 'Peak Moneyness', 'Peak Profit']].tail(25)
    df_display = df_filtered.rename(columns={'Peak Abs Change Percentage': 'Peak Abs Change %'}).round(2)
    min_percentile = nifty_df[nifty_df['Peak Profit'] >= 10]['Percentile'].max()
    
    message1 = f"""Symbol: {straddle['symbol']}
LTP: {straddle['ltp']}
CE Strike: {straddle['ce_strike']}, CE Cost: {straddle['ce_cost']}
PE Strike: {straddle['pe_strike']}, PE Cost: {straddle['pe_cost']}
Total Cost of Straddle: {straddle['total_cost']}

Start Day - {today}
End Day - {expiry}

There {min_percentile}% chance of being at least 10% profitable if we setup a long straddle now with the above mentioned prices"""
    
    message2 = df_display.to_string(index=False)
    return message1, message2

def analyze_straddle(nifty_df):
    """Analyze straddle and send messages based on conditions"""
    straddle = fetch_straddle_data()
    
    today = datetime.now().strftime("%A")
    expiry = straddle['expiry_day']
    
    nifty_df = calculate_profit_metrics(nifty_df, straddle['ltp'], straddle['ce_strike'], straddle['pe_strike'], straddle['total_cost'])
    min_percentile = nifty_df[nifty_df['Peak Profit'] >= 10]['Percentile'].max()
    
    message1, message2 = create_messages(straddle, nifty_df, today, expiry)
    
    print(message1)
    print(message2)
    
    return min_percentile, message1, message2

from datetime import datetime

def scheduler():
    """Run analysis every 5 seconds between 15:00-15:31"""
    # Generate volatility analysis once at start
    today = datetime.now().strftime("%A")
    straddle = fetch_straddle_data()
    expiry = straddle['expiry_day']
    process_volatility_analysis(specific_file="0000_NIFTY.csv", start_day=today, end_day=expiry)
    nifty_df = pd.read_csv("results/rv-iv-analysis/NIFTY.csv")
    
    last_message_time = 0
    
    while True:
        now = datetime.now()
        current_time = now.time()
        
        # Check if current time is within trading window
        if current_time >= datetime.strptime(WINDOW_START, '%H:%M').time() and current_time <= datetime.strptime(WINDOW_END, '%H:%M').time():
            min_percentile, message1, message2 = analyze_straddle(nifty_df)
            
            # Send message if min_percentile >= 95 or every 5 minutes
            if min_percentile >= 95 or (time.time() - last_message_time) >= 3600:
                asyncio.run(send_to_me(message1))
                asyncio.run(send_to_me(message2))
                last_message_time = time.time()
            
            time.sleep(5)
        else:
            print(f"Outside trading window ({WINDOW_START}-{WINDOW_END}). Waiting...")
            time.sleep(60)

if __name__ == "__main__":
    scheduler()