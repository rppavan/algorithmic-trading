import os
from dotenv import load_dotenv
import requests
import json
import pandas as pd
import time

'''

List of some important instrument_keys

    1) NIFTY50  -   NSE_INDEX|Nifty 50
    2) SENSEX30 -   BSE_INDEX|SENSEX

'''

load_dotenv()

access_token = os.getenv("UPSTOX_ACCESS_TOKEN")

url = 'https://api.upstox.com/v2/expired-instruments/expiries'

headers = {
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {access_token}',
    'Accept': 'application/json'
}

instruments = {
    
    'NIFTY50': {'instrument_key': 'NSE_INDEX|Nifty 50'},
    'SENSEX30': {'instrument_key': 'BSE_INDEX|SENSEX'},
    'BANKNIFTY': {'instrument_key': 'NSE_INDEX|Nifty Bank'}

}

for name, info in instruments.items():

    print(f"Fetching expiries for: {name}")

    params = {
        'instrument_key': info['instrument_key']
    }

    response = requests.get(url, params=params, headers=headers)

    if response.status_code == 200:
        dates = sorted(response.json().get('data', []))
        instruments[name]['expiry_dates'] = dates
        # print(json.dumps(response.json(), indent=4))
    else:
        print(f"Error for {name}: {response.status_code} - {response.text}")

print()

# for name, info in instruments.items():
#     print(f"\n{name}:")
#     print(f"Instrument Key: {info['instrument_key']}")
#     for date in info['expiry_dates']:
#         # print(f"\tExpiry Date: {date}")
#         pass


url = 'https://api.upstox.com/v2/expired-instruments/option/contract'

contracts = []

for name, info in instruments.items():

    print(f"Fetching contracts for: {name}")

    instrument_key =  info['instrument_key']

    for expiry in info['expiry_dates']:

        params = {
            'instrument_key' : instrument_key,
            'expiry_date' : expiry
        }

        response = requests.get(url, params=params, headers=headers)

        if response.status_code == 200:
            data = response.json()
            for contract in data.get('data', []):
                contracts.append({
                    'underlying_symbol': contract['underlying_symbol'],
                    'strike_price': contract['strike_price'],
                    'option_type': contract['instrument_type'],
                    'expiry_date': contract['expiry'],
                    'trading_symbol': contract['trading_symbol'],
                    'expired_instrument_key': contract['instrument_key']
                })

                # for x, y in contracts[-1].items():
                #     print(f"{x:25} : {y}")
                # print()
        else:
            print(f"Error: {response.status_code} - {response.text}")

print()

x = 0
limit = 25

base_output_folder = r"data\storage\options\index"

print(f"Total Contracts: {len(contracts)}")
print("Started fetching data...\n")

start_time = time.time()
global_start = time.time()

success = 0
already = 0

rate_limited = 0

for contract in contracts:

    interval = '1minute'
    from_date = '2020-02-24'
    
    instrument_key = contract['expired_instrument_key']
    to_date = contract['expiry_date']

    strike = int(contract['strike_price'])
    underlying = contract['underlying_symbol'].lower()
    symbol = contract['trading_symbol'].replace(" ", "_")
    expiry = contract['expiry_date']

    output_folder = os.path.join(base_output_folder, underlying, expiry)
    os.makedirs(output_folder, exist_ok=True)

    url = f'https://api.upstox.com/v2/expired-instruments/historical-candle/{instrument_key}/{interval}/{to_date}/{from_date}'

    filename = os.path.join(output_folder, f"{symbol}.csv")

    if os.path.exists(filename):
        # x += 1
        # success += 1
        already += 1
        continue

    response = requests.get(url, headers=headers)

    if response.status_code == 200:

        data = response.json()

        df = pd.DataFrame(data.get('data', {}).get('candles', []), columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'oi'])

        df = df.iloc[::-1]
        df.to_csv(filename, index=False)
        
        success += 1

        # print(json.dumps(data, indent=4))

    else:

        print(f"\nError: {response.status_code} - {response.text}")

        if (response.status_code == 429):

            # wait 90 seconds before trying again if rate limited

            now = time.time()
            total_time = now - start_time
            
            wait_time = ((31 * 60) - total_time)

            rate_limited += 1
            if rate_limited == 10:
                print("\nRate limit exceeded 10 times, exiting...")
                break

            print(f"Fetched {success} contracts data in {total_time} time...")
            print(f"\nRate limiting, waiting for {wait_time:.2f} seconds...")

            time.sleep(wait_time)
            start_time = time.time()
            continue

        # break

    if (success % 250 == 0):
        print(f"Fetched {success} contracts so far...")
        time.sleep(2)

    if (success % 5000 == 0):
        print("Fetched 5000 contracts, exiting...")
        # time.sleep(60)
        break

    x += 1

end_time = time.time()
total_time = end_time - global_start

print(f"\nTotal time taken {total_time}.")
print(f"Average time per contract: {total_time/success if success > 0 else 0:.2f} seconds.")

print(f"\nAlready existing: {already} contracts.")
print(f"Successfully fetched data for {success} contracts.")