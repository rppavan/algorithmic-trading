import os
import sys
import logging
import pandas as pd
import requests
import zipfile
import asyncio
from datetime import datetime
from time import sleep
from NorenRestApiPy.NorenApi import FeedType

# Add root directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from broker.shoonya.config import *
# import broker.shoonya.basicfunctions as bf
from utilities.telegram_bot import send_to_me

# Login to Shoonya API
logging.info("Logging into Shoonya API...")
try:
    # login()
    limits = api.get_limits()
    logging.info(f"Login successful. Available cash: {limits.get('cash', 0)}")
except Exception as e:
    logging.error(f"Login failed: {e}")
    exit()

# Download and load symbol files
urls = {
    'NSE_symbols.txt': 'https://api.shoonya.com/NSE_symbols.txt.zip',
    'NFO_symbols.txt': 'https://api.shoonya.com/NFO_symbols.txt.zip',
    'BSE_symbols.txt': 'https://api.shoonya.com/BSE_symbols.txt.zip',
    'BFO_symbols.txt': 'https://api.shoonya.com/BFO_symbols.txt.zip'
}

# Download and extract symbol files
for filename, url in urls.items():
    try:
        if os.path.exists(filename):
            os.remove(filename)
        zip_filename = filename + '.zip'
        response = requests.get(url)
        with open(zip_filename, 'wb') as f:
            f.write(response.content)
        with zipfile.ZipFile(zip_filename, 'r') as zip_ref:
            zip_ref.extractall('.')
        os.remove(zip_filename)
    except PermissionError:
        logging.info(f"Could not overwrite {filename}, using existing file")

# Load symbol dataframes
try:
    nse_df = pd.read_csv('NSE_symbols.txt')
    nfo_df = pd.read_csv('NFO_symbols.txt')
    bse_df = pd.read_csv('BSE_symbols.txt')
    bfo_df = pd.read_csv('BFO_symbols.txt')
except PermissionError as e:
    logging.error(f"Cannot read symbol files: {e}. Please close any programs using these files.")
    exit()

logging.info(f"Loaded {len(nse_df)} NSE symbols, {len(nfo_df)} NFO symbols, {len(bse_df)} BSE symbols, {len(bfo_df)} BFO symbols")

print(nse_df.head())
print(nfo_df.head())
print(bse_df.head(20))
print(bfo_df.head())

# Filter NSE dataframe for INDEX instruments
index_df = nfo_df[nfo_df['Instrument'] == 'OPTIDX']
print("\nINDEX instruments:")
print(index_df)

# Filter for nearest expiry dates for each symbol
index_df['Expiry'] = pd.to_datetime(index_df['Expiry'], format='%d-%b-%Y')
nearest_expiry_df = index_df.loc[index_df.groupby('Symbol')['Expiry'].idxmin()]
print("\nNearest expiry for each symbol:")
print(nearest_expiry_df[['Symbol', 'TradingSymbol', 'Expiry']].drop_duplicates())

# Get unique symbols with exchange
unique_symbols = index_df[['Symbol', 'Exchange']].drop_duplicates()
print("\nUnique symbols with exchange:")
print(unique_symbols)

# Find token numbers from NSE symbols
index_tokens = nse_df[nse_df['Symbol'].isin(unique_symbols['Symbol'])][['Symbol', 'Token', 'Exchange']]
print("\nIndex tokens from NSE:")
print(index_tokens)

# # Print unique instruments in BSE dataframe
# print("\nUnique instruments in BSE:")
# print(bse_df['Instrument'].unique())
# # print(list(bse_df['Symbol'].unique()))

# print(bfo_df['Instrument'].unique())

# # Filter unique symbols with OPTIDX == Instrument in bfo_df
# bfo_idx = bfo_df[bfo_df['Instrument'] == 'OPTIDX']['Symbol'].unique()
# print("\nUnique OPTIDX symbols in BFO:")
# print(bfo_idx)

# # print(bfo_df['Instrument'].unique())


# Create dict of exchange and token from NSE INDEX instruments (excluding INDIAVIX)
index_nse = nse_df[(nse_df['Instrument'] == 'INDEX') & (nse_df['Symbol'] != 'INDIAVIX')]
index_dict = dict(zip(index_nse['Symbol'], zip(index_nse['Exchange'], index_nse['Token'])))
print("\nIndex dictionary (Symbol: [Exchange, Token]):")
print(index_dict)

# Create mapping between NSE index symbols and NFO option symbols
symbol_mapping = {
    'Nifty 50': 'NIFTY',
    'Nifty Bank': 'BANKNIFTY', 
    'Nifty Fin Services': 'FINNIFTY',
    'NIFTY MID SELECT': 'MIDCPNIFTY',
    'Nifty Next 50': 'NIFTYNXT50'
}
print("\nSymbol mapping:")
print(symbol_mapping)

def calculate_long_straddle_price(symbol='Nifty 50'):
    """Calculate long straddle price for given symbol."""
    if symbol not in index_dict:
        print(f"Symbol {symbol} not found in index dictionary")
        return None
        
    exchange, token = index_dict[symbol]

    from datetime import datetime
    
    try:
        ret = api.get_quotes(exchange=exchange, token=str(token))
        if ret and ret.get('stat') == 'Ok':
            ltp = ret.get('lp', '0.00')
            time_str = datetime.now().strftime('%H:%M:%S')
            print(f"{symbol:<25} {exchange:<10} {token:<10} {ltp:<10} {time_str:<10}")
            
            # Fetch option chain using current price as strike price
            start_time = datetime.now()
            nfo_symbol = symbol_mapping.get(symbol, symbol)
            
            # Get trading symbol from nearest expiry data
            trading_symbol_row = nearest_expiry_df[nearest_expiry_df['Symbol'] == nfo_symbol]
            if not trading_symbol_row.empty:
                trading_symbol = trading_symbol_row['TradingSymbol'].iloc[0]
                expiry_date = trading_symbol_row['Expiry'].iloc[0]
                expiry_day = expiry_date.strftime('%A')
            else:
                trading_symbol = nfo_symbol
                expiry_date = None
                expiry_day = None
                
            rounded_strike = round(float(ltp) / 50) * 50
            option_chain = api.get_option_chain(exchange='NFO', tradingsymbol=trading_symbol, strikeprice=rounded_strike, count=6)
            
            if option_chain and option_chain.get('stat') == 'Ok':
                # Group options by strike price
                strikes = {}
                for option in option_chain.get('values', []):
                    strike = option.get('strprc', '')
                    if strike not in strikes:
                        strikes[strike] = {'CE': '', 'PE': ''}
                    
                    try:
                        option_token = option.get('token', '')
                        option_exchange = option.get('exch', 'NFO')
                        option_price_ret = api.get_quotes(exchange=option_exchange, token=option_token)
                        option_price = option_price_ret.get('lp', '0.00') if option_price_ret and option_price_ret.get('stat') == 'Ok' else '0.00'
                        strikes[strike][option.get('optt', '')] = option_price
                    except Exception as e:
                        strikes[strike][option.get('optt', '')] = 'N/A'
                
                # Calculate 0.5% above and below LTP for OTM options
                ltp_float = float(ltp)
                otm_ce_target = ltp_float * 1.005  # 0.5% above
                otm_pe_target = ltp_float * 0.995  # 0.5% below
                
                # Find nearest strikes
                otm_ce_strike = round(otm_ce_target / 50) * 50
                otm_pe_strike = round(otm_pe_target / 50) * 50
                
                # Find costs from the strikes dictionary
                ce_cost = strikes.get(f"{otm_ce_strike:.2f}", {}).get('CE', 'N/A')
                pe_cost = strikes.get(f"{otm_pe_strike:.2f}", {}).get('PE', 'N/A')
                
                result = {
                    'symbol': symbol,
                    'ltp': float(ltp),
                    'ce_strike': otm_ce_strike,
                    'pe_strike': otm_pe_strike,
                    'ce_cost': ce_cost,
                    'pe_cost': pe_cost,
                    'total_cost': None,
                    'expiry_date': expiry_date.strftime('%Y-%m-%d') if expiry_date else None,
                    'expiry_day': expiry_day
                }
                
                if ce_cost != 'N/A' and pe_cost != 'N/A':
                    try:
                        total_cost = float(ce_cost) + float(pe_cost)
                        result['total_cost'] = total_cost
                        message = f"\nLong Straddle Cost:\nCE {otm_ce_strike}: {ce_cost}\nPE {otm_pe_strike}: {pe_cost}\nTotal Cost: {total_cost:.2f}"
                        print(message)
                        # asyncio.run(send_to_me(message))
                    except ValueError:
                        message = f"\nLong Straddle Cost:\nCE {otm_ce_strike}: {ce_cost}\nPE {otm_pe_strike}: {pe_cost}"
                        print(message)
                        # asyncio.run(send_to_me(message))
                else:
                    message = f"\nLong Straddle Cost:\nCE {otm_ce_strike}: {ce_cost}\nPE {otm_pe_strike}: {pe_cost}"
                    print(message)
                    # asyncio.run(send_to_me(message))
                
                return result
            else:
                print(f"Failed to fetch option chain failed: {option_chain.get('emsg', 'Unknown')}")
                return None
        else:
            error_msg = ret.get('emsg', 'Unknown') if ret else 'No response'
            print(f"Failed to get quotes: {error_msg}")
            return None
    except Exception as e:
        print(f"Error calculating straddle price for {symbol}: {str(e)}")
        return None


if __name__ == '__main__':
    # Fetch and display LTP for index symbols every 5 seconds
    while datetime.now().strftime('%H:%M') < '15:51':
        result = calculate_long_straddle_price('Nifty 50')
        if result:
            print(f"Straddle calculation completed for {result['symbol']}")
        sleep(5)

# Create a list of tokens of indexes to keep track of...

# Subscribe to spot prices of those tokens via websocket

# Subscribe the a range of put and call options of the indexes

# Use the df stored to see if the prices are too much underpriced and
# promising profitablbity of atleast 10% with a probability of >95%