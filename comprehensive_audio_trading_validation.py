import pandas as pd
import os
import glob
from datetime import datetime, timedelta

CALL_INFO_FILE = 'June/call_info_output.xlsx'
ORDER_DIR = 'June/Order Files/'
UCC_FILE = 'June/UCC database.xlsx'
OUTPUT_FILE = 'June/audio_order_kl_orgtimestamp_validation.xlsx'

def parse_time(ts):
    try:
        return datetime.strptime(ts.strip(), '%Y-%m-%d %H:%M:%S')
    except Exception:
        try:
            return pd.to_datetime(ts, dayfirst=False, errors='coerce')
        except Exception:
            return pd.NaT

def create_mobile_to_client_mapping():
    """Create mapping from mobile numbers to all possible client IDs"""
    ucc_df = pd.read_excel(UCC_FILE, dtype=str)
    mobile_to_clients = {}
    for _, row in ucc_df.iterrows():
        mobile = str(row['MOBILE NUMBER']).replace(' ', '').replace('-', '')[-10:]  # Last 10 digits
        client_id = str(row['CLIENT CD'])
        if mobile not in mobile_to_clients:
            mobile_to_clients[mobile] = set()
        mobile_to_clients[mobile].add(client_id)
    return mobile_to_clients

def main():
    print("=== AUDIO-ORDER VALIDATION (KL users, OrgTimeStamp) ===\n")
    
    # Create mobile to client mapping
    mobile_to_clients = create_mobile_to_client_mapping()
    
    # Load audio files
    print("Loading audio files...")
    calls = pd.read_excel(CALL_INFO_FILE, dtype=str)
    calls['call_start_dt'] = pd.to_datetime(calls['call_start'], errors='coerce')
    calls['call_end_dt'] = pd.to_datetime(calls['call_end'], errors='coerce')
    calls['call_date'] = calls['call_start_dt'].dt.date
    
    # Add all possible client IDs for each audio file
    calls['all_client_ids'] = calls['mobile_number'].apply(
        lambda x: list(mobile_to_clients.get(str(x)[-10:], [])) if pd.notna(x) else []
    )
    
    # Load all orders (KL users only, use OrgTimeStamp)
    print("Loading order files (KL users only)...")
    all_order_files = glob.glob(os.path.join(ORDER_DIR, 'OrderBook-*.xlsx'))
    all_order_files += glob.glob(os.path.join(ORDER_DIR, 'OrderBook-*.csv'))
    all_orders = []
    for order_file in all_order_files:
        if order_file.endswith('.xlsx'):
            orders = pd.read_excel(order_file, dtype=str)
        else:
            orders = pd.read_csv(order_file, dtype=str)
        if 'User' in orders.columns:
            orders = orders[orders['User'].str.lower().str.startswith('kl', na=False)]
        if 'OrgTimeStamp' in orders.columns:
            orders['order_time'] = orders['OrgTimeStamp'].apply(parse_time)
        else:
            orders['order_time'] = pd.NaT
        orders['order_date'] = orders['order_time'].dt.date
        orders['order_id'] = orders.get('ExchOrderID', orders.index)
        orders['source_file'] = os.path.basename(order_file)
        all_orders.append(orders)
    orders_combined = pd.concat(all_orders, ignore_index=True)
    
    print(f"Loaded {len(orders_combined)} KL orders (should be 377)")
    print("First 10 order_ids:", orders_combined['order_id'].head(10).tolist())
    if len(orders_combined) != 377:
        print("WARNING: Number of KL orders loaded is not 377!")
    
    print(f"Loaded {len(calls)} audio files, {len(orders_combined)} KL orders (OrgTimeStamp used)")
    
    # Audio to Orders Matching
    print("\n=== AUDIO TO ORDERS MATCHING ===")
    audio_to_orders = []
    for _, call in calls.iterrows():
        all_client_ids = call['all_client_ids']
        call_date = call['call_date']
        call_start = call['call_start_dt']
        call_end = call['call_end_dt']
        
        # Find orders for ANY of the client IDs on this date
        client_orders = orders_combined[
            (orders_combined['ClientID'].isin(all_client_ids)) & 
            (orders_combined['order_date'] == call_date)
        ]
        
        if client_orders.empty:
            audio_to_orders.append({
                'audio_filename': call.get('filename', ''),
                'client_id': call.get('client_id', ''),
                'all_client_ids': ','.join(all_client_ids),
                'call_date': call_date,
                'call_start': call_start,
                'call_end': call_end,
                'order_match_status': 'no_orders_for_client_date',
                'matched_order_ids': '',
                'order_count': 0
            })
        else:
            # Check for ±5 min match using OrgTimeStamp
            match_window_start = call_start - timedelta(minutes=5)
            match_window_end = call_end + timedelta(minutes=5)
            matching_orders = client_orders[
                (client_orders['order_time'] >= match_window_start) & 
                (client_orders['order_time'] <= match_window_end)
            ]
            
            if matching_orders.empty:
                audio_to_orders.append({
                    'audio_filename': call.get('filename', ''),
                    'client_id': call.get('client_id', ''),
                    'all_client_ids': ','.join(all_client_ids),
                    'call_date': call_date,
                    'call_start': call_start,
                    'call_end': call_end,
                    'order_match_status': 'no_orders_within_5min',
                    'matched_order_ids': '',
                    'order_count': 0
                })
            else:
                audio_to_orders.append({
                    'audio_filename': call.get('filename', ''),
                    'client_id': call.get('client_id', ''),
                    'all_client_ids': ','.join(all_client_ids),
                    'call_date': call_date,
                    'call_start': call_start,
                    'call_end': call_end,
                    'order_match_status': 'matched',
                    'matched_order_ids': ','.join(matching_orders['order_id'].astype(str)),
                    'order_count': len(matching_orders)
                })
    
    # Orders to Audio Matching
    print("=== ORDERS TO AUDIO MATCHING ===")
    orders_to_audio = []
    for _, order in orders_combined.iterrows():
        client_id = order['ClientID']
        order_date = order['order_date']
        order_time = order['order_time']
        
        # Check if there's any audio for this client on this date (check all client IDs)
        client_audio = calls[calls['all_client_ids'].apply(lambda x: client_id in x) & (calls['call_date'] == order_date)]
        audio_count = len(client_audio)
        if client_audio.empty:
            orders_to_audio.append({
                'order_id': order['order_id'],
                'client_id': client_id,
                'order_date': order_date,
                'order_time': order_time,
                'source_file': order['source_file'],
                'audio_match_status': 'no_audio_for_client_date',
                'audio_count_for_date': 0,
                'matched_audio_filenames': '',
                'closest_audio_filename': '',
                'min_time_diff_seconds': '',
                'note': 'No audio files for this client on this date.'
            })
        else:
            # Check if order is within ±5 min of any call
            match_window_start = order_time - timedelta(minutes=5)
            match_window_end = order_time + timedelta(minutes=5)
            matching_calls = client_audio[
                (client_audio['call_start_dt'] <= match_window_end) & 
                (client_audio['call_end_dt'] >= match_window_start)
            ]
            if matching_calls.empty:
                # Find closest audio file(s) and time difference(s)
                client_audio = client_audio.copy()
                client_audio['time_diff'] = client_audio.apply(
                    lambda row: min(abs((order_time - row['call_start_dt']).total_seconds()), abs((order_time - row['call_end_dt']).total_seconds())), axis=1)
                min_diff = client_audio['time_diff'].min()
                closest_audios = client_audio[client_audio['time_diff'] == min_diff]
                closest_filenames = ','.join(closest_audios['filename'].astype(str))
                orders_to_audio.append({
                    'order_id': order['order_id'],
                    'client_id': client_id,
                    'order_date': order_date,
                    'order_time': order_time,
                    'source_file': order['source_file'],
                    'audio_match_status': 'no_audio_within_5min',
                    'audio_count_for_date': audio_count,
                    'matched_audio_filenames': '',
                    'closest_audio_filename': closest_filenames,
                    'min_time_diff_seconds': min_diff,
                    'note': f'Closest audio file(s): {closest_filenames} ({min_diff} seconds away)'
                })
            else:
                matched_filenames = ','.join(matching_calls['filename'].astype(str))
                orders_to_audio.append({
                    'order_id': order['order_id'],
                    'client_id': client_id,
                    'order_date': order_date,
                    'order_time': order_time,
                    'source_file': order['source_file'],
                    'audio_match_status': 'matched',
                    'audio_count_for_date': audio_count,
                    'matched_audio_filenames': matched_filenames,
                    'closest_audio_filename': '',
                    'min_time_diff_seconds': '',
                    'note': f'Matched audio file(s): {matched_filenames}'
                })
    
    # Summary
    total_audio = len(calls)
    total_orders = len(orders_combined)
    audio_with_orders = len([x for x in audio_to_orders if x['order_match_status'] == 'matched'])
    orders_with_audio = len([x for x in orders_to_audio if x['audio_match_status'] == 'matched'])
    
    print("\n=== SUMMARY ===")
    print(f"Total Audio Files: {total_audio}")
    print(f"Total KL Orders: {total_orders}")
    print(f"Audio with Orders: {audio_with_orders}/{total_audio} ({audio_with_orders/total_audio*100:.1f}%)")
    print(f"Orders with Audio: {orders_with_audio}/{total_orders} ({orders_with_audio/total_orders*100:.1f}%)")
    
    # Build Order_Audio_Mapping sheet
    print("Building Order_Audio_Mapping sheet...")
    order_audio_mapping = []
    matched_audio_files = set()
    for _, order in orders_combined.iterrows():
        client_id = order['ClientID']
        order_date = order['order_date']
        order_time = order['order_time']
        order_id = order['order_id']
        # Find all audio files for this client/date (check all client IDs)
        client_audio = calls[calls['all_client_ids'].apply(lambda x: client_id in x) & (calls['call_date'] == order_date)]
        if client_audio.empty:
            order_audio_mapping.append({
                'order_id': order_id,
                'client_id': client_id,
                'order_date': order_date,
                'order_time': order_time,
                'match_status': 'no_audio_matched',
                'mapped_audio_filenames': '',
                'min_time_diff_seconds': '',
                'note': 'No audio files for this client on this date.'
            })
        else:
            # Check for ±5 min match
            match_window_start = order_time - timedelta(minutes=5)
            match_window_end = order_time + timedelta(minutes=5)
            matching_calls = client_audio[(client_audio['call_start_dt'] <= match_window_end) & (client_audio['call_end_dt'] >= match_window_start)]
            if not matching_calls.empty:
                mapped_filenames = ','.join(matching_calls['filename'].astype(str))
                for fname in matching_calls['filename']:
                    matched_audio_files.add(fname)
                order_audio_mapping.append({
                    'order_id': order_id,
                    'client_id': client_id,
                    'order_date': order_date,
                    'order_time': order_time,
                    'match_status': 'matched_in_time_range',
                    'mapped_audio_filenames': mapped_filenames,
                    'min_time_diff_seconds': '',
                    'note': f'Matched within ±5 min: {mapped_filenames}'
                })
            else:
                # List all audio files for the day
                mapped_filenames = ','.join(client_audio['filename'].astype(str))
                for fname in client_audio['filename']:
                    matched_audio_files.add(fname)
                # Find closest audio file and time diff
                client_audio = client_audio.copy()
                client_audio['time_diff'] = client_audio.apply(
                    lambda row: min(abs((order_time - row['call_start_dt']).total_seconds()), abs((order_time - row['call_end_dt']).total_seconds())), axis=1)
                min_time_diff = client_audio['time_diff'].min()
                order_audio_mapping.append({
                    'order_id': order_id,
                    'client_id': client_id,
                    'order_date': order_date,
                    'order_time': order_time,
                    'match_status': 'audio_on_same_day',
                    'mapped_audio_filenames': mapped_filenames,
                    'min_time_diff_seconds': min_time_diff,
                    'note': f'Audio files on same day (not in ±5 min): {mapped_filenames}'
                })
    
    # Create output Excel with multiple sheets
    with pd.ExcelWriter(OUTPUT_FILE, engine='openpyxl') as writer:
        pd.DataFrame(audio_to_orders).to_excel(writer, sheet_name='Audio_To_Orders', index=False)
        pd.DataFrame(orders_to_audio).to_excel(writer, sheet_name='Orders_To_Audio', index=False)
        pd.DataFrame(order_audio_mapping).to_excel(writer, sheet_name='Order_Audio_Mapping', index=False)
        calls.to_excel(writer, sheet_name='All_Audio_Files', index=False)
        orders_combined.to_excel(writer, sheet_name='All_KL_Orders', index=False)
    
    # Print summary stats
    matched_in_range = len([x for x in order_audio_mapping if x['match_status'] == 'matched_in_time_range'])
    audio_same_day = len([x for x in order_audio_mapping if x['match_status'] == 'audio_on_same_day'])
    no_audio = len([x for x in order_audio_mapping if x['match_status'] == 'no_audio_matched'])
    
    print("\nOrder-Audio Mapping Stats:")
    print(f"Orders matched in time range: {matched_in_range}")
    print(f"Orders with audio on same day (not in time range): {audio_same_day}")
    print(f"Orders with no audio matched: {no_audio}")
    print(f"Unique audio files matched to at least one order: {len(matched_audio_files)}")
    
    print(f"\nDetailed analysis saved to: {OUTPUT_FILE}")

if __name__ == "__main__":
    main() 