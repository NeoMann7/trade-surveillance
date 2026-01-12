import pandas as pd
import os
import glob
from datetime import datetime, timedelta
import tempfile

# S3 support
USE_S3 = os.getenv('USE_S3', 'false').lower() == 'true'
S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME')
S3_BASE_PREFIX = os.getenv('S3_BASE_PREFIX', 'trade_surveillance')

S3_AVAILABLE = False
if USE_S3 and S3_BUCKET_NAME:
    try:
        from s3_utils import (
            read_excel_from_s3, read_csv_from_s3,
            upload_file_to_s3, get_s3_key, s3_file_exists, list_s3_objects
        )
        S3_AVAILABLE = True
    except ImportError:
        print("⚠️ S3 utilities not available, falling back to local filesystem")

def parse_time(ts):
    """Parse timestamp string to datetime object"""
    try:
        # Try DD-MM-YYYY format first (which is what the order files use)
        return datetime.strptime(ts.strip(), '%d-%m-%Y %H:%M:%S')
    except Exception:
        try:
            # Try YYYY-MM-DD format
            return datetime.strptime(ts.strip(), '%Y-%m-%d %H:%M:%S')
        except Exception:
            try:
                # Try pandas parsing with dayfirst=True for DD-MM-YYYY
                return pd.to_datetime(ts, dayfirst=True, errors='coerce')
            except Exception:
                return pd.NaT

def create_mobile_to_client_mapping(ucc_df):
    """Create mapping from mobile numbers to all possible client IDs"""
    mobile_to_clients = {}
    for _, row in ucc_df.iterrows():
        mobile = str(row['MOBILE']).replace(' ', '').replace('-', '')[-10:]  # Last 10 digits
        client_id = str(row['CLIENT CD'])
        if mobile not in mobile_to_clients:
            mobile_to_clients[mobile] = set()
        mobile_to_clients[mobile].add(client_id)
    return mobile_to_clients

def consolidate_audio_clusters(audio_files, audio_data, consolidation_window_minutes=3):
    """
    Group audio files that are within the consolidation window into clusters.
    Returns a list of audio clusters, where each cluster contains audio files that should be analyzed together.
    """
    if len(audio_files) <= 1:
        return [audio_files]
    
    # Sort audio files by time
    audio_times = []
    for audio_file in audio_files:
        # Extract timestamp from filename
        date_part = audio_file.split('-')[-1].replace('.wav', '')
        year = date_part[:4]
        month = date_part[4:6]
        day = date_part[6:8]
        hour = date_part[8:10]
        minute = date_part[10:12]
        second = date_part[12:14]
        audio_time = datetime.strptime(f'{year}-{month}-{day} {hour}:{minute}:{second}', '%Y-%m-%d %H:%M:%S')
        audio_times.append((audio_file, audio_time))
    
    audio_times.sort(key=lambda x: x[1])
    
    # Group audio files into clusters
    clusters = []
    current_cluster = [audio_times[0]]
    
    for i in range(1, len(audio_times)):
        current_audio = audio_times[i]
        last_audio_in_cluster = current_cluster[-1]
        
        time_diff = (current_audio[1] - last_audio_in_cluster[1]).total_seconds() / 60
        
        if time_diff <= consolidation_window_minutes:
            # Add to current cluster
            current_cluster.append(current_audio)
        else:
            # Start new cluster
            clusters.append([audio[0] for audio in current_cluster])
            current_cluster = [current_audio]
    
    # Add the last cluster
    clusters.append([audio[0] for audio in current_cluster])
    
    return clusters

def validate_audio_trading_for_date(date_str):
    """
    Validate audio-trading mapping for a specific date in August or September
    date_str format: '01082025' for August 1st, 2025 or '01092025' for September 1st, 2025
    """
    
    # Determine month and set paths accordingly
    month = int(date_str[2:4])
    month_names = {
        1: "January", 2: "February", 3: "March", 4: "April",
        5: "May", 6: "June", 7: "July", 8: "August",
        9: "September", 10: "October", 11: "November", 12: "December"
    }
    
    if month not in month_names:
        print(f"❌ Invalid month: {month}")
        return None
    
    month_name = month_names[month]
    
    # Define paths based on month
    call_info_path = f"{month_name}/Daily_Reports/{date_str}/call_info_output_{date_str}.xlsx"
    order_files_path = f"{month_name}/Order Files"
    ucc_db_path = f"{month_name}/UCC Database.xlsx"
    output_path = f"{month_name}/Daily_Reports/{date_str}/audio_order_kl_orgtimestamp_validation_{date_str}.xlsx"
    
    # Get S3 keys if using S3
    if USE_S3 and S3_AVAILABLE:
        call_info_s3_key = f"{S3_BASE_PREFIX}/{call_info_path}"
        ucc_db_s3_key = f"{S3_BASE_PREFIX}/{ucc_db_path}"
        output_s3_key = f"{S3_BASE_PREFIX}/{output_path}"
        
        # Check if call info file exists in S3
        if not s3_file_exists(call_info_s3_key):
            print(f"Call info file not found in S3: {call_info_s3_key}")
            return None
        
        # Load call info from S3
        try:
            calls = read_excel_from_s3(call_info_s3_key)
            calls = calls.astype(str)  # Convert to string dtype
        except Exception as e:
            print(f"Error loading call info from S3: {e}")
            return None
    else:
        # Local filesystem
        # Check if call info file exists
        if not os.path.exists(call_info_path):
            print(f"Call info file not found: {call_info_path}")
            return None
        
        # Load call info
        try:
            calls = pd.read_excel(call_info_path, dtype=str)
        except Exception as e:
            print(f"Error loading call info: {e}")
            return None
    
    # PERMANENT FIX: Handle empty call info file gracefully (no audio files for this date)
    if len(calls) == 0:
        print(f"ℹ️  Call info file is empty (no audio files for {date_str})")
        print(f"📝 Creating empty audio-order validation output file...")
        
        # Create empty output file with required structure
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
        try:
            with pd.ExcelWriter(temp_file.name, engine='openpyxl') as writer:
                # Create empty DataFrames with required columns for each sheet
                pd.DataFrame(columns=['audio_filename', 'client_id', 'all_client_ids', 'call_date', 'call_start', 'call_end', 'order_match_status', 'matched_order_ids', 'order_count']).to_excel(writer, sheet_name='Audio_To_Orders', index=False)
                pd.DataFrame(columns=['order_id', 'client_id', 'order_date', 'order_time', 'symbol', 'quantity', 'price', 'side', 'user', 'status', 'match_status', 'mapped_audio_filenames', 'min_time_diff_seconds', 'has_audio', 'note']).to_excel(writer, sheet_name='Order_Audio_Mapping', index=False)
                pd.DataFrame(columns=['filename', 'mobile_number', 'present_in_ucc', 'call_start', 'call_end', 'duration_seconds', 'client_id', 'call_start_dt', 'call_end_dt', 'call_date', 'all_client_ids']).to_excel(writer, sheet_name='All_Audio_Files', index=False)
            
            # Upload to S3 or save locally
            if USE_S3 and S3_AVAILABLE:
                upload_file_to_s3(temp_file.name, output_s3_key)
                print(f"✅ Created empty audio-order validation file in S3: {output_s3_key}")
            else:
                os.rename(temp_file.name, output_path)
                print(f"✅ Created empty audio-order validation file: {output_path}")
        finally:
            if os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
        
        print(f"✅ Audio-order validation completed (no audio files for this date)")
        return output_path
    
    calls['call_start_dt'] = pd.to_datetime(calls['call_start'], errors='coerce')
    calls['call_end_dt'] = pd.to_datetime(calls['call_end'], errors='coerce')
    calls['call_date'] = calls['call_start_dt'].dt.date
    print(f"Loaded call info with {len(calls)} records")
    
    # Load UCC database
    try:
        if USE_S3 and S3_AVAILABLE:
            ucc_df = read_excel_from_s3(ucc_db_s3_key)
            ucc_df = ucc_df.astype(str)  # Convert to string dtype
        else:
            ucc_df = pd.read_excel(ucc_db_path, dtype=str)
        print(f"Loaded UCC database with {len(ucc_df)} records")
    except Exception as e:
        print(f"Error loading UCC database: {e}")
        return None
    
    # Create mobile to client mapping
    mobile_to_clients = create_mobile_to_client_mapping(ucc_df)
    
    # Add all possible client IDs for each audio file
    calls['all_client_ids'] = calls['mobile_number'].apply(
        lambda x: list(mobile_to_clients.get(str(x)[-10:], [])) if pd.notna(x) else []
    )
    
    # Find order file for the specific date
    # Try both patterns for order files
    order_file_patterns = [
        f"OrderBook-Closed-{date_str}.csv",
        f"OrderBook_Closed-{date_str}.csv"
    ]
    order_file_path = None
    order_file_s3_key = None
    
    if USE_S3 and S3_AVAILABLE:
        # Check S3 for order files - try both Order Files and Daily_Reports locations
        order_locations = [
            f"{S3_BASE_PREFIX}/{order_files_path}/",  # Standard location
            f"{S3_BASE_PREFIX}/{month_name}/Daily_Reports/{date_str}/"  # Alternative location (where uploads go)
        ]
        for location in order_locations:
            for pattern in order_file_patterns:
                test_s3_key = f"{location}{pattern}"
                if s3_file_exists(test_s3_key):
                    order_file_s3_key = test_s3_key
                    print(f"Found order file in S3: {test_s3_key}")
                    break
            if order_file_s3_key:
                break
    else:
        # Check local filesystem - try both locations
        locations = [
            order_files_path,  # Standard location
            f"{month_name}/Daily_Reports/{date_str}"  # Alternative location
        ]
        for location in locations:
            for pattern in order_file_patterns:
                test_path = os.path.join(location, pattern)
                if os.path.exists(test_path):
                    order_file_path = test_path
                    print(f"Found order file: {test_path}")
                    break
            if order_file_path:
                break
    
    # PERMANENT FIX: Handle missing OrderBook file gracefully
    if not order_file_path and not order_file_s3_key:
        print(f"⚠️  Order file not found for any pattern: {order_file_patterns}")
        print(f"📝 Creating empty audio-order validation output file (no orders for this date)...")
        
        # Create empty output file with required structure
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
        try:
            with pd.ExcelWriter(temp_file.name, engine='openpyxl') as writer:
                # Create empty DataFrames with required columns for each sheet
                pd.DataFrame(columns=['audio_filename', 'client_id', 'all_client_ids', 'call_date', 'call_start', 'call_end', 'order_match_status', 'matched_order_ids', 'order_count']).to_excel(writer, sheet_name='Audio_To_Orders', index=False)
                pd.DataFrame(columns=['order_id', 'client_id', 'order_date', 'order_time', 'symbol', 'quantity', 'price', 'side', 'user', 'status', 'match_status', 'mapped_audio_filenames', 'min_time_diff_seconds', 'has_audio', 'note']).to_excel(writer, sheet_name='Order_Audio_Mapping', index=False)
                # Include calls DataFrame if it exists (even if empty)
                if len(calls) > 0:
                    calls.to_excel(writer, sheet_name='All_Audio_Files', index=False)
                else:
                    pd.DataFrame(columns=['filename', 'mobile_number', 'present_in_ucc', 'call_start', 'call_end', 'duration_seconds', 'client_id']).to_excel(writer, sheet_name='All_Audio_Files', index=False)
                # Empty KL orders sheet
                pd.DataFrame(columns=['order_id', 'client_id', 'order_date', 'order_time', 'symbol', 'quantity', 'price', 'side', 'user', 'status']).to_excel(writer, sheet_name='All_KL_Orders', index=False)
            
            # Upload to S3 or save locally
            if USE_S3 and S3_AVAILABLE:
                upload_file_to_s3(temp_file.name, output_s3_key)
                print(f"✅ Created empty audio-order validation file in S3: {output_s3_key}")
            else:
                os.rename(temp_file.name, output_path)
                print(f"✅ Created empty audio-order validation file: {output_path}")
        finally:
            if os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
        
        print(f"✅ Audio-order validation completed (no order file for this date)")
        return output_path
    
    # Load order data
    try:
        if USE_S3 and S3_AVAILABLE:
            orders = read_csv_from_s3(order_file_s3_key)
            orders = orders.astype(str)  # Convert to string dtype
        else:
            orders = pd.read_csv(order_file_path, dtype=str)
        print(f"Loaded order file with {len(orders)} records")
        print(f"Order file columns: {orders.columns.tolist()}")
    except Exception as e:
        print(f"Error loading order file: {e}")
        return None
    
    # Filter for KL users and process timestamps
    if 'User' in orders.columns:
        kl_orders = orders[orders['User'].str.contains('KL', na=False)]
        print(f"Found {len(kl_orders)} KL orders")
    else:
        kl_orders = orders
        print("No User column found, using all orders")
    
    # Process order timestamps
    if 'OrgTimeStamp' in kl_orders.columns:
        kl_orders['order_time'] = kl_orders['OrgTimeStamp'].apply(parse_time)
    else:
        kl_orders['order_time'] = pd.NaT
    
    kl_orders['order_date'] = kl_orders['order_time'].dt.date
    kl_orders['order_id'] = kl_orders.get('ExchOrderID', kl_orders.index)
    
    print(f"Loaded {len(calls)} audio files, {len(kl_orders)} KL orders (OrgTimeStamp used)")
    
    # Audio to Orders Matching
    print("\n=== AUDIO TO ORDERS MATCHING ===")
    audio_to_orders = []
    for _, call in calls.iterrows():
        all_client_ids = call['all_client_ids']
        call_date = call['call_date']
        call_start = call['call_start_dt']
        call_end = call['call_end_dt']
        
        # Find orders for ANY of the client IDs on this date
        client_orders = kl_orders[
            (kl_orders['ClientID'].isin(all_client_ids)) & 
            (kl_orders['order_date'] == call_date)
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
    for _, order in kl_orders.iterrows():
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
                'source_file': order_file_path,
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
                # FALLBACK: Match with ANY audio file from this client for the entire day
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
                    'source_file': order_file_path,
                    'audio_match_status': 'matched_daily_fallback',
                    'audio_count_for_date': audio_count,
                    'matched_audio_filenames': closest_filenames,
                    'closest_audio_filename': '',
                    'min_time_diff_seconds': min_diff,
                    'note': f'Matched with daily fallback: {closest_filenames} ({min_diff} seconds away)'
                })
            else:
                matched_filenames = ','.join(matching_calls['filename'].astype(str))
                orders_to_audio.append({
                    'order_id': order['order_id'],
                    'client_id': client_id,
                    'order_date': order_date,
                    'order_time': order_time,
                    'source_file': order_file_path,
                    'audio_match_status': 'matched',
                    'audio_count_for_date': audio_count,
                    'matched_audio_filenames': matched_filenames,
                    'closest_audio_filename': '',
                    'min_time_diff_seconds': '',
                    'note': f'Matched audio file(s): {matched_filenames}'
                })
    
    # Build Order_Audio_Mapping sheet
    print("Building Order_Audio_Mapping sheet...")
    order_audio_mapping = []
    matched_audio_files = set()
    for _, order in kl_orders.iterrows():
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
                'symbol': order.get('Symbol', ''),
                'quantity': order.get('Qty', ''),
                'price': order.get('Price', ''),
                'side': order.get('BuySell', ''),
                'user': order.get('User', ''),
                'status': order.get('Status', ''),
                'match_status': 'no_audio_matched',
                'mapped_audio_filenames': '',
                'min_time_diff_seconds': '',
                'has_audio': 'N',
                'note': 'No audio files for this client on this date.'
            })
        else:
            # DYNAMIC TIME WINDOWS based on order frequency
            # Count orders for this client on this date to determine frequency
            client_orders_count = len(orders[orders['ClientID'] == client_id])
            
            # Determine time window based on order frequency
            if client_orders_count >= 8:  # High-frequency scenario (like NEO130)
                time_window_minutes = 2
            elif client_orders_count >= 4:  # Normal scenario
                time_window_minutes = 5
            else:  # Low-frequency scenario
                time_window_minutes = 10
            
            # Check for dynamic time window match
            match_window_start = order_time - timedelta(minutes=time_window_minutes)
            match_window_end = order_time + timedelta(minutes=time_window_minutes)
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
                    'symbol': order.get('Symbol', ''),
                    'quantity': order.get('Qty', ''),
                    'price': order.get('Price', ''),
                    'side': order.get('BuySell', ''),
                    'user': order.get('User', ''),
                    'status': order.get('Status', ''),
                    'match_status': 'matched_in_time_range',
                    'mapped_audio_filenames': mapped_filenames,
                    'min_time_diff_seconds': '',
                    'has_audio': 'Y',
                    'note': f'Matched within ±{time_window_minutes} min: {mapped_filenames}'
                })
            else:
                # FALLBACK: Match with ANY audio file from this client for the entire day
                client_audio = client_audio.copy()
                client_audio['time_diff'] = client_audio.apply(
                    lambda row: min(abs((order_time - row['call_start_dt']).total_seconds()), abs((order_time - row['call_end_dt']).total_seconds())), axis=1)
                min_diff = client_audio['time_diff'].min()
                closest_audios = client_audio[client_audio['time_diff'] == min_diff]
                closest_filenames = ','.join(closest_audios['filename'].astype(str))
                for fname in closest_audios['filename']:
                    matched_audio_files.add(fname)
                order_audio_mapping.append({
                    'order_id': order_id,
                    'client_id': client_id,
                    'order_date': order_date,
                    'order_time': order_time,
                    'symbol': order.get('Symbol', ''),
                    'quantity': order.get('Qty', ''),
                    'price': order.get('Price', ''),
                    'side': order.get('BuySell', ''),
                    'user': order.get('User', ''),
                    'status': order.get('Status', ''),
                    'match_status': 'matched_daily_fallback',
                    'mapped_audio_filenames': closest_filenames,
                    'min_time_diff_seconds': min_diff,
                    'has_audio': 'Y',
                    'note': f'Matched with daily fallback: {closest_filenames} ({min_diff} seconds away)'
                })
    
    # Create output Excel with multiple sheets
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
    try:
        with pd.ExcelWriter(temp_file.name, engine='openpyxl') as writer:
            pd.DataFrame(audio_to_orders).to_excel(writer, sheet_name='Audio_To_Orders', index=False)
            pd.DataFrame(orders_to_audio).to_excel(writer, sheet_name='Orders_To_Audio', index=False)
            pd.DataFrame(order_audio_mapping).to_excel(writer, sheet_name='Order_Audio_Mapping', index=False)
            calls.to_excel(writer, sheet_name='All_Audio_Files', index=False)
            kl_orders.to_excel(writer, sheet_name='All_KL_Orders', index=False)
        
        # Upload to S3 or save locally
        if USE_S3 and S3_AVAILABLE:
            upload_file_to_s3(temp_file.name, output_s3_key)
            print(f"✅ Results saved to S3: {output_s3_key}")
        else:
            os.rename(temp_file.name, output_path)
            print(f"✅ Results saved to: {output_path}")
    finally:
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)
    
    # Print summary stats
    matched_in_range = len([x for x in order_audio_mapping if x['match_status'] == 'matched_in_time_range'])
    matched_daily_fallback = len([x for x in order_audio_mapping if x['match_status'] == 'matched_daily_fallback'])
    no_audio = len([x for x in order_audio_mapping if x['match_status'] == 'no_audio_matched'])
    
    print(f"\nAudio-order validation saved to: {output_path}")
    print(f"Audio to Orders: {len(audio_to_orders)} records")
    print(f"Orders to Audio: {len(orders_to_audio)} records")
    print(f"Order Audio Mapping: {len(order_audio_mapping)} records")
    print(f"All Audio Files: {len(calls)} records")
    print(f"All KL Orders: {len(kl_orders)} records")
    
    print("\nOrder-Audio Mapping Stats:")
    print(f"Orders matched in time range (±5 min): {matched_in_range}")
    print(f"Orders matched with daily fallback: {matched_daily_fallback}")
    print(f"Orders with no audio matched: {no_audio}")
    print(f"Total orders with audio: {matched_in_range + matched_daily_fallback}")
    print(f"Unique audio files matched to at least one order: {len(matched_audio_files)}")
    
    return output_path

if __name__ == "__main__":
    import sys
    
    # Get date from command line argument or use default
    if len(sys.argv) > 1:
        date_str = sys.argv[1]
    else:
        # Default date (August 7th, 2025)
        date_str = "07082025"
    
    result = validate_audio_trading_for_date(date_str)
    if result:
        print(f"Successfully processed {date_str}")
    else:
        print(f"Failed to process {date_str}")
        sys.exit(1) 