"""
Scalping trading bot for automated equity trading.

This module implements an automated scalping strategy based on market depth analysis.
It connects to the Shoonya API for real-time data and order execution.
"""

import os
import sys
import logging
import pandas as pd
from datetime import datetime
from time import sleep
from NorenRestApiPy.NorenApi import FeedType

# Add root directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from broker.shoonya.config import *
import broker.shoonya.basicfunctions as bf

# Delay token subscription until 1 minute before market opens (9:14 AM)
while datetime.now().strftime("%H:%M:%S") < "09:14:00":
    logging.info("\nWaiting to subscribe to tokens until 09:14:00 🫠")
    sleep(1)

# Trading strategy parameters
TOTAL_STOCKS_FOR_SCAN = 990  # Number of stocks to analyze from the CSV file
MAX_TRADES_PER_DAY = 1       # Maximum number of trades allowed per day
trade_count = 0              # Counter to track daily trades

STOP_LOSS = -500             # Maximum loss per trade in rupees
TAKE_PROFIT = 3000           # Target profit per trade in rupees

SIZE_OF_EACH_TRADE = 500     # Investment amount per trade in rupees
START_ROW = 2                # Starting row in CSV (skip header)
END_ROW = START_ROW + TOTAL_STOCKS_FOR_SCAN - 1  # Ending row for stock selection

MIN_STOCK_PRICE = 50         # Minimum stock price filter
MAX_STOCK_PRICE = 200        # Maximum stock price filter

TRAILING_STEP = 0.0025       # Step size for trailing stop loss (0.25%)

# Global tracking variables
day_m2m = 0          # Daily mark-to-market profit/loss
feed_json = {}       # Storage for real-time market data from websocket

# File paths and naming
today_date = datetime.now().strftime("%d%m%y")  # Today's date in DDMMYY format
filename = 'tradable_equity.csv'                # Input file with stock data
mtm_graph = f'{today_date}_mtmgraph.csv'        # Daily P&L tracking file
log_file = f'{today_date}_logfile.log'          # Daily log file

# Setup logging to file with timestamp
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    filename=log_file,
    force=True
)

# Create P&L tracking file if it doesn't exist
if not os.path.exists(mtm_graph) or os.path.getsize(mtm_graph) == 0:
    try:
        with open(mtm_graph, 'w') as file:
            file.write("timestamp,day_m2m\n")
            logging.info(f"Headers added to {mtm_graph}")
    except Exception as e:
        logging.error(f"Error writing headers to {mtm_graph}: {e}")
else:
    logging.info(f"{mtm_graph} already exists and contains data. "
                 "Headers not added.")

# Load stock data from CSV file
try:
    df = pd.read_csv(filename)  # Load stock list with tokens and prices
except FileNotFoundError:
    logging.info("Stock data CSV file not found")
    exit()

# Filter and clean stock data
df = df.iloc[START_ROW - 1:END_ROW]  # Select specified range of stocks

# Clean and validate Last Traded Price data
df["LTP"] = pd.to_numeric(df["LTP"], errors="coerce")  # Convert to numbers, invalid becomes NaN
df = df.dropna(subset=["LTP"])  # Remove stocks with invalid prices
df = df[(df["LTP"] >= MIN_STOCK_PRICE) & (df["LTP"] <= MAX_STOCK_PRICE)]  # Apply price filters

logging.info(df)

# Get available trading balance from broker
try:
    limits = api.get_limits()
    cash = float(limits.get("cash", 0))
    # cash = SIZE_OF_EACH_TRADE  # Uncomment to use fixed amount for testing
    balance = float(cash)
    logging.info(f"\nAvailable Cash Balance: {balance}")
except Exception as e:
    logging.error(f"Failed to retrieve cash balance: {e}")


def round_to_tick(price, tick_size):
    """Round price to nearest valid tick size as per exchange rules."""
    return round(price / tick_size) * tick_size


# Track websocket connection status
feed_opened = False


def event_handler_feed_update(tick_data):
    """Handle incoming real-time market data from websocket."""
    required_keys = {
        'lp', 'tbq', 'tsq', 'bq1', 'bq2', 'bq3', 'bq4', 'bq5',
        'sq1', 'sq2', 'sq3', 'sq4', 'sq5'
    }
    
    # Check if all required market depth fields are present
    if all(key in tick_data for key in required_keys) and 'tk' in tick_data:
        try:
            # Store complete market depth data for this stock token
            feed_json[tick_data['tk']] = {
                'ltp': float(tick_data['lp']),     # Last traded price
                # 'pc': int(tick_data['pc']),     # Previous close (if needed)
                'tbq': int(tick_data['tbq']),     # Total buy quantity
                'tsq': int(tick_data['tsq']),     # Total sell quantity
                'bq1': int(tick_data['bq1']),     # Buy quantity at level 1
                'bq2': int(tick_data['bq2']),     # Buy quantity at level 2
                'bq3': int(tick_data['bq3']),     # Buy quantity at level 3
                'bq4': int(tick_data['bq4']),     # Buy quantity at level 4
                'bq5': int(tick_data['bq5']),     # Buy quantity at level 5
                'sq1': int(tick_data['sq1']),     # Sell quantity at level 1
                'sq2': int(tick_data['sq2']),     # Sell quantity at level 2
                'sq3': int(tick_data['sq3']),     # Sell quantity at level 3
                'sq4': int(tick_data['sq4']),     # Sell quantity at level 4
                'sq5': int(tick_data['sq5'])      # Sell quantity at level 5
            }

        except (ValueError, TypeError) as e:
            logging.info(f"Error converting market data to numbers: {e}")
    else:
        logging.info("Incomplete market data received:", tick_data)


def event_handler_order_update(tick_data):
    """Handle order status updates (fills, rejections, etc.)."""
    logging.info(f"Order update received: {tick_data}")


def open_callback():
    """Called when websocket connection is successfully established."""
    global feed_opened
    feed_opened = True


def close_callback():
    """Called when websocket connection is closed or lost."""
    global feed_opened
    feed_opened = False


# Start websocket connection with callback functions
api.start_websocket(
    order_update_callback=event_handler_order_update,  # For order status updates
    subscribe_callback=event_handler_feed_update,       # For market data updates
    socket_open_callback=open_callback                  # For connection events
)

# Wait until websocket connection is ready
while not feed_opened:
    logging.info("\nWaiting for WebSocket connection to open")
    pass

logging.info("\nWebSocket feed connection established successfully")

# Build list of stock tokens to subscribe for live data
tokens_to_subscribe = []
for _, row in df.iterrows():
    exchange = row['EXCHANGE']
    token = row['TOKEN']
    if pd.notna(exchange) and pd.notna(token):  # Skip rows with missing data
        tokens_to_subscribe.append(f"{exchange}|{token}")

# Subscribe to live market depth data for filtered stocks
if tokens_to_subscribe:
    api.subscribe(tokens_to_subscribe, feed_type=FeedType.SNAPQUOTE)
    logging.info(f"Subscribed to market depth data for: "
                 f"{tokens_to_subscribe}")
else:
    logging.info("No valid tokens found for subscription.")

# Add columns to store calculated trading signals
for col in ['ltp', 'trade_direction', 'dominant_percent']:
    if col not in df.columns:
        df[col] = None

sleep(3)

# Wait until market officially opens at 9:15 AM
while datetime.now().strftime("%H:%M:%S") < "09:15:01":
    logging.info("\nWaiting for market to open 🫠")
    sleep(1)


def generate_marketdepth_signal():
    """Analyze market depth to identify strong buy/sell signals."""
    global df
    
    # Signal threshold parameters
    PRESSURE_LOWER_BOUND = 0.70
    PRESSURE_UPPER_BOUND = 0.95
    DEPTH_MULTIPLIER = 1.50

    # Process each stock to calculate market depth signals
    for idx, row in df.iterrows():
        try:
            token = str(row['TOKEN'])
            ltp = round(float(feed_json[token]['ltp']), 2)  # Current market price
            tq = feed_json[token]['tbq'] + feed_json[token]['tsq']  # Total quantity
            # pc = round(float((feed_json[token]['pc'])), 2)  # Previous close if needed
            
            # Calculate buy and sell pressure percentages
            bp = round(float((feed_json[token]['tbq']) / tq), 2)  # Buy pressure ratio
            sp = round(float((feed_json[token]['tsq']) / tq), 2)  # Sell pressure ratio

            # Sum top 5 levels of buy and sell quantities
            top5bq = (feed_json[token]['bq1'] + feed_json[token]['bq2'] +
                     feed_json[token]['bq3'] + feed_json[token]['bq4'] +
                     feed_json[token]['bq5'])
            top5sq = (feed_json[token]['sq1'] + feed_json[token]['sq2'] +
                     feed_json[token]['sq3'] + feed_json[token]['sq4'] +
                     feed_json[token]['sq5'])

            # Generate trading signals based on market depth analysis
            if PRESSURE_UPPER_BOUND > bp > PRESSURE_LOWER_BOUND and top5bq > top5sq * DEPTH_MULTIPLIER:  # Strong buying interest
                trade_direction = 'B'  # Buy signal
                dominant_percent = bp
            elif PRESSURE_UPPER_BOUND > sp > PRESSURE_LOWER_BOUND and top5sq > top5bq * DEPTH_MULTIPLIER:  # Strong selling pressure
                trade_direction = 'S'  # Sell signal
                dominant_percent = sp
            else:
                trade_direction = None  # No clear signal
                dominant_percent = None

            # Store calculated values back to dataframe
            df.at[idx, 'ltp'] = ltp
            df.at[idx, 'trade_direction'] = trade_direction
            df.at[idx, 'dominant_percent'] = dominant_percent

            logging.info(f"Stock {idx}: Token {token}, Price {ltp}, "
                        f"Signal {trade_direction}, Strength: {dominant_percent}")
        except Exception as e:
            logging.info(f"Error analyzing token {token}: {e}")

    # logging.info(feed_json)  # Enable to debug raw market data

    # Rank stocks by signal strength (highest dominance first)
    df = df.sort_values(by='dominant_percent', ascending=False)
    df.reset_index(drop=True, inplace=True)  # Reset row numbers after sorting

    logging.info(df)
    logging.info(f"\nTop candidate: {df.loc[0]}")

    dominant_percent = df.loc[0, 'dominant_percent']

    # If no signals found, retry analysis
    if pd.isna(dominant_percent):
        logging.info("\nNo trading signals detected... Retrying analysis ;)\n")
        generate_marketdepth_signal()

    # Prepare trade parameters for the best signal
    price = df.loc[0, 'ltp']
    price = float(price)
    # qty = int(SIZE_OF_EACH_TRADE / price)  # Calculate shares based on investment amount
    qty = 1  # Fixed quantity for testing
    tsym = df.loc[0, 'Trading Symbol']
    token = df.loc[0, 'TOKEN']
    trade_direction = df.loc[0, 'trade_direction']
    exchange = df.loc[0, 'EXCHANGE']
    remarks = 'Scapling Trade'
    tick_size = df.loc[0, 'Tick Size']

    if trade_direction == 'B':
        sl_price = max(round_to_tick(((price * 0.0025)), tick_size), 1.00)
        # price -= 1  # Adjust entry price for buy orders
        tp_price = round_to_tick(((price * 0.01)), tick_size)
    elif trade_direction == 'S':
        sl_price = max(round_to_tick(((price * 0.0025)), tick_size), 1.00)
        # price += 1  # Adjust entry price for sell orders
        tp_price = round_to_tick(((price * 0.01)), tick_size)
    else:
        generate_marketdepth_signal()
    
    global trade_count

    if trade_count >= MAX_TRADES_PER_DAY:
        logging.info("Max trades per day reached. "
                    "Checking if there is an existing order...")
        manage_position()
        logging.info("No existing order found. Exiting the program")
        exit()


    api.place_order(
        buy_or_sell=trade_direction,
        product_type='H',
        exchange=exchange,
        tradingsymbol=tsym,
        quantity=qty,
        discloseqty=0,
        price_type='MKT',
        # price=price,
        price=0,
        retention='DAY',
        remarks=remarks,
        bookloss_price=sl_price
    )

    logging.info(f"\nPrice: {price}")
    logging.info(f"Quantity (qty): {qty}")
    logging.info(f"Trading Symbol (tsym): {tsym}")
    logging.info(f"Token: {token}")
    logging.info(f"Trade Direction: {trade_direction}")
    logging.info(f"Exchange: {exchange}")
    logging.info(f"Remarks: {remarks}")
    logging.info(f"Tick Size: {tick_size}\n")

    trade_count += 1

    api.unsubscribe(tokens_to_subscribe)

    # api.close_websocket()  # Close websocket connection if needed

    # while feed_opened :
    #     print("\nWaiting to close websocket connection")
    #     pass

    # api.subscribe(f'{exchange}|{token}', feed_type=FeedType.SNAPQUOTE)  # Re-subscribe to specific token

    # Retrieve the order book from the API
    orderbook = api.get_order_book()

    # Define the columns to extract from the order book
    orderbook_columns = [
        'norenordno', 'exch', 'tsym', 'rejby', 'qty', 'ordenttm', 'trantype',
        'prctypr', 'prc', 'ret', 'token', 'prcftr', 'ordersource', 'ti',
        'avgprc', 's_prdt_ali', 'prd', 'status', 'fillshares', 'rqty',
        'rorgqty', 'rorgprc', 'blprc', 'trgprc', 'snonum', 'snoordt',
        'rejreason'
    ]
        
    order_df = pd.DataFrame(orderbook, columns=orderbook_columns)

    # Check if all orders are in terminal states (rejected, completed, or canceled)
    # If order is rejected for any reason, regenerate trading signals
    if order_df['status'].isin({"REJECTED", "COMPLETE", "CANCELED"}).all():

        logging.info("\nOrder was rejected, "
                    "regenerating trading signals\n")

        # Identify tokens with margin shortfall rejection
        tokens_to_remove = order_df.loc[
            order_df['rejreason'].str.startswith("RED:Margin Shortfall", na=False), 
            'token'
        ]
        
        # Remove stocks with margin issues from trading list
        df = df[~df['token'].isin(tokens_to_remove)]

        trade_count -= 1
        generate_marketdepth_signal()

    elif (order_df['status'].isin({"REJECTED", "COMPLETE", "CANCELED"}).all() and 
          datetime.now().strftime("%H:%M:%S") > "09:20:00"):
        logging.info("There are no open positions and time is past 09:20:00, "
                    "so it isn't possible to open any new trades for the day, "
                    "exiting the program.")
        exit()
        pass

    manage_position()


def manage_position():
    """Monitor and manage active trading positions and orders."""
    while True:

        global day_m2m

        logging.info("\nMonitoring active positions...\n")

        ret = api.get_positions()
        mtm = 0
        pnl = 0
        for i in ret:
            mtm += float(i['urmtom'])
            pnl += float(i['rpnl'])
            day_m2m = mtm + pnl

        day_m2m = round(day_m2m, 2)

        logging.info(f'{day_m2m} is your Daily MTM')
        try:
            with open(mtm_graph, 'a') as file:
                timestamp = datetime.now().strftime('%H:%M:%S')
                file.write(f"{timestamp},{day_m2m}\n")
        except Exception as e:
            logging.error(f"Error writing to {mtm_graph}: {e}")

        if day_m2m > TAKE_PROFIT:
            logging.info(f"Take profit target reached: {day_m2m} is daily MTM. "
                        "Closing all positions.")
            bf.exitallpositions()

        # Retrieve the order book from the API
        orderbook = api.get_order_book()

        # Define the columns to extract from the order book
        orderbook_columns = [
            'norenordno', 'exch', 'tsym', 'rejby', 'qty', 'ordenttm', 'trantype',
            'prctypr', 'prc', 'ret', 'token', 'prcftr', 'ordersource', 'ti',
            'avgprc', 's_prdt_ali', 'prd', 'status', 'fillshares', 'rqty',
            'rorgqty', 'rorgprc', 'blprc', 'trgprc', 'snonum', 'snoordt'
        ]
        
        order_df = pd.DataFrame(orderbook, columns=orderbook_columns)

        global trade_count

        for _, row in order_df.iterrows():

            try:
                rqty = row['rqty']
                token = row['token']            # Stock token for price lookup
                exchange = row['exch']          # Trading exchange
                tsym = row['tsym']              # Trading symbol
                trantype = row['trantype']      # Transaction type: 'B' for Buy, 'S' for Sell
                # ltp = round(float(feed_json[token]['ltp']), 2)  # Last traded price
                tick_size = (round(float(row['ti']), 2) 
                           if not pd.isna(row['ti']) else 0.05)  # Minimum price movement
                orderno = row['norenordno']     # Order number

                # Trailing stop-loss management for buy orders
                if (trantype == 'B' and row['status'] == 'TRIGGER_PENDING' and 
                    int(row['snoordt']) == 1):

                    quote_info = api.get_quotes(exchange=exchange, token=token)
                    ltp = float(quote_info.get("lp", 0))

                    new_trigger_price = round_to_tick(ltp * (1 + TRAILING_STEP), 
                                                     tick_size)

                    # Only move stop-loss in favorable direction (upward for buy orders)
                    if new_trigger_price < round(float(row['trgprc']), 2):
                        api.modify_order(
                            exchange=exchange,
                            tradingsymbol=tsym,
                            orderno=row['norenordno'],
                            newquantity=rqty,
                            newprice_type='SL-MKT',
                            newprice=0.00,
                            newtrigger_price=round(new_trigger_price, 2)
                        )
                        logging.info(f"Modified SL for Buy order {row['norenordno']} "
                                   f"to {new_trigger_price}")

                    else:
                        # logging.info(f"No stop-loss adjustment needed for Buy order {row['norenordno']}")
                        pass

                # Trailing take-profit management for buy orders
                elif (trantype == 'B' and row['status'] == 'OPEN' and 
                      int(row['snoordt']) == 0):

                    quote_info = api.get_quotes(exchange=exchange, token=token)
                    ltp = float(quote_info.get("lp", 0))

                    new_tp_price = round_to_tick(ltp * (1 + TRAILING_STEP), 
                                               tick_size)

                    # Only move take-profit in favorable direction (upward for buy orders)
                    if new_tp_price < round(float(row['prc']), 2):
                        api.modify_order(
                            exchange=exchange,
                            tradingsymbol=tsym,
                            orderno=row['norenordno'],
                            newquantity=rqty,
                            newprice_type='LMT',
                            newprice=new_tp_price
                        )
                        logging.info(f"Modified take-profit for Buy order "
                                   f"{row['norenordno']} to {new_tp_price}")

                    else:
                        # logging.info(f"No take-profit adjustment needed for Buy order {row['norenordno']}")
                        pass

                # Trailing SL Leg for filled long-orders      # For Sell orders
                elif (trantype == 'S' and row['status'] == 'TRIGGER_PENDING' and 
                      int(row['snoordt']) == 1):

                    quote_info = api.get_quotes(exchange=exchange, token=token)
                    ltp = float(quote_info.get("lp", 0))
                    
                    new_trigger_price = round_to_tick(ltp * (1 - TRAILING_STEP), 
                                                     tick_size)

                    # Ensure SL is only increased
                    if new_trigger_price > round(float(row['trgprc']), 2):
                        api.modify_order(
                            exchange=exchange,
                            tradingsymbol=tsym,
                            orderno=row['norenordno'],
                            newquantity=rqty,
                            newprice_type='SL-MKT',
                            newprice=0.00,
                            newtrigger_price=round(new_trigger_price, 2)
                        )
                        logging.info(f"Modified SL for Sell order {row['norenordno']} "
                                   f"to {new_trigger_price}")

                    else:
                        # logging.info(f"No SL modification needed for Sell order (SL Leg) {row['norenordno']}")
                        pass

                # Trailing TP Leg for filled long-orders      # For Sell orders
                elif (trantype == 'S' and row['status'] == 'OPEN' and 
                      int(row['snoordt']) == 0):

                    quote_info = api.get_quotes(exchange=exchange, token=token)
                    ltp = float(quote_info.get("lp", 0))
                    
                    new_tp_price = round_to_tick(ltp * (1 - TRAILING_STEP), 
                                               tick_size)

                    # Ensure TP is only increased
                    if new_tp_price > round(float(row['prc']), 2):
                        api.modify_order(
                            exchange=exchange,
                            tradingsymbol=tsym,
                            orderno=row['norenordno'],
                            newquantity=rqty,
                            newprice_type='LMT',
                            newprice=new_tp_price
                        )
                        logging.info(f"Modified SL for Sell order (TP Leg) "
                                   f"{row['norenordno']} to {new_tp_price}")

                    else:
                        # logging.info(f"No SL modification needed for Sell order {row['norenordno']}")
                        pass

                # Cancelling Unfilled Orders
                elif row['status'] == 'OPEN' and pd.isna(row['snonum']):
                    if trantype == 'B':
                        quote_info = api.get_quotes(exchange=exchange, token=token)
                        ltp = float(quote_info.get("lp", 0))
                        orderprice = float(row['prc'])
                        if (orderprice + orderprice*0.005) < ltp:
                            api.cancel_order(orderno=orderno)
                            trade_count -= 1
                            logging.info(f"Cancelled Unfilled Buy Order {orderno}, "
                                       "and called generate_marketdepth_signal()")
                            generate_marketdepth_signal()
                        else:
                            pass
                    elif trantype == 'S':
                        quote_info = api.get_quotes(exchange=exchange, token=token)
                        ltp = float(quote_info.get("lp", 0))
                        orderprice = float(row['prc'])
                        if (orderprice - orderprice*0.005) > ltp:
                            api.cancel_order(orderno=orderno)
                            trade_count -= 1
                            logging.info(f"Cancelled Unfilled Sell order {orderno}, "
                                       "and called generate_marketdepth_signal()")
                            generate_marketdepth_signal()
                        else:
                            pass
                        
            except:
                logging.info("Critical Error in SL Trailing")
        
        # Check if all values in the 'status' column are in the given set
        if order_df['status'].isin({"REJECTED", "COMPLETE", "CANCELED"}).all():
            logging.info("\nNo Open Positions, Returning to main loop the program.\n")
            return


# Main execution loop
while True:
    try:
        if (trade_count < MAX_TRADES_PER_DAY and 
            STOP_LOSS < day_m2m < TAKE_PROFIT):
            generate_marketdepth_signal()
        else:
            logging.info("\nMaximum trades for the day reached or M2M loss is "
                        "too high or M2M gain breached take profit, "
                        "exiting the program.\n")
    except:
        logging.info("Error") 