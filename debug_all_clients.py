import pandas as pd

# Load data
calls = pd.read_excel('August/Daily_Reports/18082025/audio_order_kl_orgtimestamp_validation_18082025.xlsx')
orders = pd.read_csv('August/Order Files/OrderBook-Closed-18082025.csv')

print("=== COMPREHENSIVE CLIENT ANALYSIS ===")

# Get all clients
call_clients = set(calls['client_id'].dropna())
order_clients = set(orders['ClientID'])
overlap = call_clients.intersection(order_clients)

print(f"Total call clients: {len(call_clients)}")
print(f"Total order clients: {len(order_clients)}")
print(f"Overlapping clients: {len(overlap)}")

print("\n=== ALL CALL CLIENTS ===")
for client in sorted(call_clients):
    client_calls = calls[calls['client_id'] == client]
    client_orders = orders[orders['ClientID'] == client]
    
    print(f"\nClient: {client}")
    print(f"  Calls: {len(client_calls)}")
    print(f"  Orders: {len(client_orders)}")
    
    if len(client_calls) > 0:
        print(f"  Call times: {client_calls['call_start'].tolist()}")
    
    if len(client_orders) > 0:
        print(f"  Order times: {client_orders['TimeStamp'].head(3).tolist()}")
    else:
        print(f"  Status: No orders found for this client")

print("\n=== OVERLAPPING CLIENTS (with timing analysis) ===")
for client in sorted(overlap):
    client_calls = calls[calls['client_id'] == client]
    client_orders = orders[orders['ClientID'] == client]
    
    print(f"\nClient: {client}")
    print(f"  Calls: {len(client_calls)}, Orders: {len(client_orders)}")
    
    if len(client_calls) > 0 and len(client_orders) > 0:
        call_time = client_calls['call_start'].iloc[0]
        order_time = pd.to_datetime(client_orders['TimeStamp'].iloc[0], format='%d-%m-%Y %H:%M:%S')
        time_diff_minutes = abs((call_time - order_time).total_seconds() / 60)
        
        print(f"  Call time: {call_time}")
        print(f"  Order time: {order_time}")
        print(f"  Time difference: {time_diff_minutes:.1f} minutes")
        print(f"  Within 5 min: {'Yes' if time_diff_minutes <= 5 else 'No'}")

print("\n=== SUMMARY ===")
print(f"Only {len(overlap)} out of {len(call_clients)} call clients have orders")
print("This suggests either:")
print("1. Many calls don't result in orders (normal)")
print("2. Client ID mapping issues")
print("3. Orders are in different files/dates")
