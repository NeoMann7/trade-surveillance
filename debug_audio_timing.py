import pandas as pd
from datetime import datetime

# Load data
calls = pd.read_excel('August/Daily_Reports/18082025/audio_order_kl_orgtimestamp_validation_18082025.xlsx')
orders = pd.read_csv('August/Order Files/OrderBook-Closed-18082025.csv')

print("=== AUDIO-ORDER TIMING DEBUG ===")

# Check time differences for clients with both calls and orders
for client in ['NEOWM00129', 'NEOWP00087', 'NEOWP00413']:
    client_calls = calls[calls['client_id'] == client]
    client_orders = orders[orders['ClientID'] == client]
    
    print(f"\nClient: {client}")
    print(f"Calls: {len(client_calls)}, Orders: {len(client_orders)}")
    
    if len(client_calls) > 0 and len(client_orders) > 0:
        # Get first call and first order
        call_time = client_calls['call_start'].iloc[0]
        order_time = pd.to_datetime(client_orders['TimeStamp'].iloc[0], format='%d-%m-%Y %H:%M:%S')
        time_diff_minutes = abs((call_time - order_time).total_seconds() / 60)
        
        print(f"Call time: {call_time}")
        print(f"Order time: {order_time}")
        print(f"Time difference: {time_diff_minutes:.1f} minutes")
        print(f"Within 5 min window: {'Yes' if time_diff_minutes <= 5 else 'No'}")

print("\n=== RECOMMENDATION ===")
print("The ±5 minute window is too restrictive for real-world trading scenarios.")
print("Consider expanding the window to ±15-30 minutes to capture more realistic matches.")
print("Many orders are placed during calls but executed with some delay.")
