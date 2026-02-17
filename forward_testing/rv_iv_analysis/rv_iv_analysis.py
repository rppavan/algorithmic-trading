'''

To do in this script:

    1) Fetch option-chain for a particular script
    2) Calculate the relavant metrics
        a) Setup Cost
        b) Breakeven Price
        c) Target Price
        d) Probability of Profit
    3) If the 0.5% Straddle is profitable for 90% probability
    4) Open a trade & store it in a csv, and send it as a message to telegram bot.

'''

'''

To Do:

    0) Document the code. ✅

    1) Remove the redundant, commented parts. ✅
    2) Make a function to start finding for trades from 15:00/15:10 to 15:30 ✅
    3) Store the message and send the messages after opening trades, to reduce the slippages. ✅

    4) Add the logic to have a single active trade in each index, and save trades to a csv.✅
    5) If trades are opened, track the prices of options that are bought.

    6) Add telegram messages for unvoluntary exits from script ✅

    7) Automate everything to deploy of docker
    8) Deploy on docker

Remaining tasks:

    1) Write code for monitoring prices of open trades using websockets
    2) The current piece of code is a shit piece, make a modular, try to have only 200 LOC in a single file :)
    3) Know how to depoly it on docker and depoly it :)

'''

import requests
import os
import json
import sys
import asyncio
import time
import pytz
from dotenv import load_dotenv
from datetime import datetime
import threading
import websockets

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from backtesting.rv_iv_analysis.rv_iv_analysis import *
from utilities.telegram_bot import send_to_me

load_dotenv()
access_token = os.getenv("UPSTOX_ACCESS_TOKEN")

underlying_instruments = {
    'NIFTY50': {'instrument_key': 'NSE_INDEX|Nifty 50'},
    'SENSEX30': {'instrument_key': 'BSE_INDEX|SENSEX'}
}

today = datetime.today().strftime("%A")
# print(f"Today is {today}")

nifty_data = process_volatility_analysis(specific_file="0000_NIFTY.csv", start_day=today, end_day="Tuesday")
sensex_data = process_volatility_analysis(specific_file="0000_SENSEX.csv", start_day=today, end_day="Thursday")

df_nifty = pd.DataFrame(nifty_data)
df_sensex = pd.DataFrame(sensex_data)

underlying_instruments["NIFTY50"]["rv_data"] = df_nifty
underlying_instruments["SENSEX30"]["rv_data"] = df_sensex

# Code to get LTP of the underlying instruments


base_url = "https://api.upstox.com/v3/market-quote/ltp"

headers = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Authorization": f"Bearer {access_token}"
}

for name, details in underlying_instruments.items():

    params = {
        "instrument_key": details["instrument_key"]
    }

    response = requests.get(base_url, headers=headers, params=params)

    print(f"Fetching LTP for {name}...")

    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        exit()

    data = response.json().get("data", {})

    if not data:
        print("No data returned")
        continue

    # Get the first (and only) key dynamically
    instrument_data = next(iter(data.values()))

    ltp = instrument_data.get("last_price")

    underlying_instruments[name]["ltp"] = ltp

    # print(f"LTP of {name}: {ltp}\n")

    # try:
    #     print(json.dumps(response.json(), indent=4))
    # except ValueError:
    #     print(response.text)

# print()

# Code get option contracts i.e expiries & lot sizes for each underlying

option_contract_url = "https://api.upstox.com/v2/option/contract"

for name, details in underlying_instruments.items():

    params = {
        "instrument_key": details["instrument_key"]
    }

    response = requests.get(option_contract_url, headers=headers, params=params)

    # print(f"Fetching expiries for {name}...")

    try:
        data = response.json()
        contracts = data.get("data", [])

        # Extract unique expiries
        expiries = sorted({
            contract["expiry"]
            for contract in contracts
            if "expiry" in contract
        })

        # Store back into dictionary

        underlying_instruments[name]["expiries"] = expiries
        underlying_instruments[name]["latest_expiry"] = expiries[0]
        underlying_instruments[name]["lot_size"] = contracts[0]["lot_size"]

        # print(f"Stored {len(expiries)} expiries")
        # print("\n", expiries)
        # print(f"\nLatest Expiry: {underlying_instruments[name]["latest_expiry"]}")

    except ValueError:
        print("Invalid JSON response")
        print(response.text)


# Code fetch option chains

def analyse():

    trade_opening_days = {
        'Thursday': 'Friday',
        'Tuesday': 'Wednesday'
    }

    option_chain_url = "https://api.upstox.com/v2/option/chain"

    all_msgs = []
    msg = []

    for name, details in underlying_instruments.items():

        if msg:
            all_msgs.append(msg[:])

        msg = []

        def print_msg(s, text=msg):
            print(s)
            text.append(s)

        # Check for existing open trades
        OUTPUT_FOLDER = r"forward_testing\rv_iv_analysis"
        trades_file = os.path.join(OUTPUT_FOLDER, 'trades.csv')
        
        if os.path.exists(trades_file):

            existing_trades = pd.read_csv(trades_file)
            open_trades = existing_trades[(existing_trades['Symbol'] == name) & (existing_trades['Status'] == 'Open')]
            
            if not open_trades.empty:
                print_msg(f"Skipping RV analysis for {name} - Active open trades exist\n")
                asyncio.run(send_to_me("\n".join(msg)))
                msg = []
                continue

        instrument_key = details["instrument_key"]
        expiry_date = details.get("latest_expiry")

        rv_data = details.get("rv_data", [])

        if not expiry_date:
            print_msg(f"No expiry found for {name}")
            asyncio.run(send_to_me("\n".join(msg)))
            msg = []
            continue

        # Convert expiry string to weekday
        expiry_day = datetime.strptime(expiry_date, "%Y-%m-%d").strftime("%A")

        # Check if expiry day exists in mapping
        # if expiry_day not in trade_opening_days:
        #     print_msg(f"{name} expiry on {expiry_day} → Skipping (not configured)")
        #     asyncio.run(send_to_me("\n".join(msg)))
        #     msg = []
        #     continue

        trade_open_day = trade_opening_days[expiry_day]

        # Check if today is correct opening day
        # if today != trade_open_day:
        #     print_msg(f"{name} expiry on {expiry_day}, trade opens on {trade_open_day} → Today mismatch, skipping\n")
        #     asyncio.run(send_to_me("\n".join(msg)))
        #     msg = []
        #     continue

        # If conditions satisfied → Fetch Option Chain

        print_msg(f"RV analysis for {name}\n")

        params = {
            "instrument_key": instrument_key,
            "expiry_date": expiry_date
        }

        # print_msg(f"\nFetching option chain for {name} | Expiry: {expiry_date}\n")

        response = requests.get(option_chain_url, headers=headers, params=params)

        if response.status_code != 200:
            print_msg(f"Error fetching option chain: {response.status_code}\n")
            continue

        try:
            chain_data = response.json().get("data", [])
            underlying_instruments[name]["option_chain"] = chain_data

            print

            # print_msg(f"Fetched {len(chain_data)} strikes for {name}")
            print_msg(f"Spot Price of {name}: {underlying_instruments[name]["ltp"]}")
            print_msg(f"Latest Expiry: {underlying_instruments[name]["latest_expiry"]}")
            print_msg(f"Lot Size: {underlying_instruments[name]["lot_size"]}\n")

            ltp = underlying_instruments[name]["ltp"]

            call_target = ltp * 1.005     # 0.5% OTM CALL
            put_target  = ltp * 0.995     # 0.5% OTM PUT

            nearest_call = None
            nearest_put = None

            min_call_diff = float("inf")
            min_put_diff = float("inf")

            for strike_data in chain_data:

                strike = strike_data["strike_price"]

                # CALL → strike just above 0.5%
                if strike >= call_target:
                    diff = strike - call_target
                    if diff < min_call_diff:
                        min_call_diff = diff
                        nearest_call = strike_data

                # PUT → strike just below 0.5%
                if strike <= put_target:
                    diff = put_target - strike
                    if diff < min_put_diff:
                        min_put_diff = diff
                        nearest_put = strike_data

            # print_msg("\n===== 0.5% OTM Selection =====")

            if nearest_call:
                call_cost = nearest_call['call_options']['market_data']['ltp']
                print_msg(f"Call Strike: {nearest_call['strike_price']}")
                print_msg(f"Call LTP: {call_cost}\n")

            if nearest_put:
                put_cost = nearest_put['put_options']['market_data']['ltp']
                print_msg(f"Put Strike: {nearest_put['strike_price']}")
                print_msg(f"Put LTP: {put_cost}\n")

            if nearest_call and nearest_put:

                call_strike = nearest_call['strike_price']
                put_strike = nearest_put['strike_price']

                total_cost = call_cost + put_cost
                cost_percent = (total_cost / ltp) * 100

                upper_breakeven = call_strike + total_cost
                lower_breakeven = put_strike - total_cost

                upper_be_percent = ((upper_breakeven - ltp) / ltp) * 100
                lower_be_percent = ((ltp - lower_breakeven) / ltp) * 100

                upper_target = call_strike + (2 * total_cost)
                lower_target = put_strike - (2 * total_cost)

                upper_target_percent = ((upper_target - ltp) / ltp) * 100
                lower_target_percent = ((ltp - lower_target) / ltp) * 100

                abs_max_move = max(upper_target_percent, lower_target_percent)

                target = abs_max_move

                row = rv_data[rv_data['Peak Abs Change Percentage'] >= target].iloc[-1]
                target_percentile = row['Percentile']

                print_msg(f"Total Cost of Setup = {total_cost}")
                print_msg(f"Cost as % of Spot = {cost_percent:.2f}%\n")
                
                print_msg(f"Upper Breakeven = {upper_breakeven}  (+{upper_be_percent:.2f}%)")
                print_msg(f"Lower Breakeven = {lower_breakeven}  (-{lower_be_percent:.2f}%)\n")

                print_msg("100% Profit Targets")
                print_msg(f"Upper Target = {upper_target}  (+{upper_target_percent:.2f}%)")
                print_msg(f"Lower Target = {lower_target}  (-{lower_target_percent:.2f}%)\n")

                print_msg(f"Required Target Change {target:.2f}%")
                print_msg(f"Probability is {target_percentile}%")

                if msg:  # Only send if msg is not empty
                    asyncio.run(send_to_me("\n".join(msg)))
                msg = []

                # print(f"\nMaximum Abs Move = {abs_max_move:.2f}%")

                required_probability = 90

                # exit()

                if target_percentile >= required_probability:

                    trade_data = []

                    print_msg(f"\nFound a profitabile setup for {name}\n", trade_data)
                    print_msg(f"Probability of 100% Profit = {target_percentile}% (≥ {required_probability}%)", trade_data)
                    # print_msg("Trade is opened\n", trade_data)

                    print_msg(f"Trade Details", trade_data)
                    print_msg(f"Spot Price - {ltp}\n", trade_data)

                    print_msg(f"Call Strike - {call_strike}", trade_data)
                    print_msg(f"Call LTP - {call_cost}\n", trade_data)
                    
                    print_msg(f"Put Strike - {put_strike}", trade_data)
                    print_msg(f"Put LTP - {put_cost}\n", trade_data)

                    print_msg(f"Total Cost - {total_cost}\n", trade_data)

                    print_msg(f"Upper Breakeven - {upper_breakeven} (+{upper_be_percent:.2f}%)", trade_data)
                    print_msg(f"Upper Target - {upper_target} (+{upper_target_percent:.2f}%)\n", trade_data)

                    print_msg(f"Lower Breakeven - {lower_breakeven} (-{lower_be_percent:.2f}%)", trade_data)
                    print_msg(f"Lower Target - {lower_target} (-{lower_target_percent:.2f}%)\n", trade_data)

                    
                    call_instrument_key = nearest_call['call_options']['instrument_key']
                    put_instrument_key = nearest_put['put_options']['instrument_key']

                    # print(call_instrument_key)
                    # print(put_instrument_key)
                    
                    trades_df = pd.DataFrame([
                        {
                            'Symbol': name,
                            'Option Type': 'CE',
                            'Strike Price': call_strike,
                            'Buy Price': call_cost,
                            'Status': 'Open',
                            'Target': upper_target,
                            'Breakeven': upper_breakeven,
                            'Instrument Key': call_instrument_key,
                            'Sell Price': ''
                        },
                        {
                            'Symbol': name,
                            'Option Type': 'PE',
                            'Strike Price': put_strike,
                            'Buy Price': put_cost,
                            'Status': 'Open',
                            'Target': lower_target,
                            'Breakeven': lower_breakeven,
                            'Instrument Key': put_instrument_key,
                            'Sell Price': ''
                        }
                    ])

                    # Save trades to CSV
                    OUTPUT_FOLDER = r"forward_testing\rv_iv_analysis"
                    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
                    
                    trades_file = os.path.join(OUTPUT_FOLDER, 'trades.csv')
                    trades_df.to_csv(trades_file, mode='a', header=not os.path.exists(trades_file), index=False)
                    
                    if trade_data:  # Only send if trade_data is not empty
                        asyncio.run(send_to_me("\n".join(trade_data)))

        except ValueError:
            print("Invalid JSON response")
            print(response.text)

async def monitor():

    return

    msg = []

    def print_msg(s, text=msg):
        print(s)
        text.append(s)

    def send_msg():
        asyncio.run(send_to_me("\n".join(msg)))
        msg = []

    OUTPUT_FOLDER = r"forward_testing\rv_iv_analysis"
    trades_file = os.path.join(OUTPUT_FOLDER, 'trades.csv')

    if not os.path.exists(trades_file):
        print_msg("No trades file found")
        send_msg()
        return

    trades_df = pd.read_csv(trades_file)

    # print(trades_df)

    open_trades = trades_df[trades_df['Status'] == 'Open']

    if open_trades.empty:
        print("No open trades found")
        send_msg()
        return

    instrument_targets = {}
    for _, trade in open_trades.iterrows():
        instrument_targets[trade['Instrument Key']] = trade['Target']

    print(instrument_targets)

    instrument_keys = list(instrument_targets.keys())

    print("Subscribing to:", instrument_keys)

    # WebSocket Connection

    url = "wss://api.upstox.com/v3/feed/market-data-feed"

    async with websockets.connect(
        url,
        extra_headers={
            "Authorization": f"Bearer {access_token}"
        }
    ) as ws:

        # Subscription payload
        subscribe_payload = {
            "guid": "monitor-guid",
            "method": "sub",
            "data": {
                "mode": "ltp",
                "instrumentKeys": instrument_keys
            }
        }

        await ws.send(json.dumps(subscribe_payload))
        print("Subscribed successfully")

        while instrument_targets:

            message = await ws.recv()
            data = json.loads(message)

            # Structure depends on feed format
            if "data" not in data:
                continue

            for instrument_key, tick_data in data["data"].items():

                ltp = tick_data.get("ltp")

                if instrument_key not in instrument_targets:
                    continue

                row_index, target = instrument_targets[instrument_key]

                if ltp >= target:

                    print(f"Target hit for {instrument_key} at {ltp}")

                    trades_df.loc[row_index, 'Status'] = "Close"
                    trades_df.loc[row_index, 'Sell Price'] = ltp

                    trades_df.to_csv(trades_file, index=False)

                    # Remove from tracking
                    del instrument_targets[instrument_key]

        print("All targets completed.")

    # time.sleep(45)

ist = pytz.timezone('Asia/Kolkata')

def run_analyse():

    trading_window_start = datetime.strptime('15:00', '%H:%M').time()
    trading_window_end = datetime.strptime('15:29:59', '%H:%M:%S').time()

    while True:
        now = datetime.now(ist)
        current_time = now.time()

        if trading_window_start <= current_time <= trading_window_end:
            analyse()
            time.sleep(15)
        else:
            time.sleep(1)


def run_monitor():

    monitor_start = datetime.strptime('09:15:03', '%H:%M:%S').time()
    monitor_end = datetime.strptime('15:30:00', '%H:%M:%S').time()

    while True:
        now = datetime.now(ist)
        current_time = now.time()

        if monitor_start <= current_time <= monitor_end:
            monitor()
            time.sleep(1)
        else:
            time.sleep(1)

def main():

    t1 = threading.Thread(target=run_analyse)
    t2 = threading.Thread(target=run_monitor)

    t1.start()
    t2.start()

    t1.join()
    t2.join()


if __name__ == "__main__":
    main()