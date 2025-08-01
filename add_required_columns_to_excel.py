import pandas as pd
import os

def get_dealer_id(order_id, all_orders):
    # Map Dealer ID from 'User' column using 'ExchOrderID' as key
    if not all_orders.empty and 'ExchOrderID' in all_orders.columns and 'User' in all_orders.columns:
        match = all_orders[all_orders['ExchOrderID'] == str(order_id)]
        if not match.empty:
            val = match.iloc[0]['User']
            if pd.notna(val):
                return val
    return ''

def get_order_executed(order_id, all_orders):
    if not all_orders.empty and 'ExchOrderID' in all_orders.columns and 'Status' in all_orders.columns:
        match = all_orders[all_orders['ExchOrderID'] == str(order_id)]
        if not match.empty:
            return match.iloc[0]['Status']
    return ''

def get_transcript(audio_file, transcripts_dir):
    transcript_file = os.path.join(transcripts_dir, audio_file + '.txt')
    if os.path.exists(transcript_file):
        with open(transcript_file, 'r', encoding='utf-8') as f:
            return f.read().strip()
    return ''

# File paths
BASE_FILE = 'June/order_transcript_analysis_mapping_all_dates_20250715_095106.xlsx'
ORDER_FILES_DIR = 'June/Order Files/'
CALL_INFO_PATH = 'June/call_info_output.xlsx'
TRANSCRIPTS_DIR = 'June/transcripts/'
OUTPUT_FILE = 'June/order_transcript_analysis_mapping_all_dates_20250715_095106_with_required_columns.xlsx'

# Load base file
df = pd.read_excel(BASE_FILE, dtype=str)
df = df.fillna('')

# Load all order files (for Dealer ID and Order Executed)
order_files = [os.path.join(ORDER_FILES_DIR, f) for f in os.listdir(ORDER_FILES_DIR) if f.endswith(('.xlsx', '.csv'))]
order_data = []
for file in order_files:
    if file.endswith('.xlsx'):
        odf = pd.read_excel(file, dtype=str)
    else:
        odf = pd.read_csv(file, dtype=str)
    odf['source_file'] = os.path.basename(file)
    order_data.append(odf)
all_orders = pd.concat(order_data, ignore_index=True) if order_data else pd.DataFrame()

# Load call info and create mapping by filename
call_info = pd.read_excel(CALL_INFO_PATH, dtype=str)
call_info = call_info.fillna('')
call_info_map = call_info.set_index('filename')

# Add missing columns
dealer_ids = []
mobile_nos = []
registered_statuses = []
order_executed_statuses = []
call_extracts = []
observations = []
for idx, row in df.iterrows():
    order_id = row.get('order_id', '')
    client_id = row.get('client_id', '')
    audio_file = row.get('audio_file', '')
    # Dealer ID
    dealer_ids.append(get_dealer_id(order_id, all_orders))
    # Mobile No. and Registered Number Status from call_info_output
    mobile_no = ''
    registered_status = ''
    if audio_file and audio_file in call_info_map.index:
        row_info = call_info_map.loc[audio_file]
        if isinstance(row_info, pd.DataFrame):
            row_info = row_info.iloc[0]
        mobile_no = row_info['mobile_number']
        registered_status = row_info['present_in_ucc']
    mobile_nos.append(mobile_no)
    registered_statuses.append(registered_status)
    # Order Executed
    order_executed_statuses.append(get_order_executed(order_id, all_orders))
    # Call Extract
    call_extracts.append(get_transcript(audio_file, TRANSCRIPTS_DIR))
    # Observation (AI analysis)
    observations.append(row.get('ai_reasoning', ''))

df['Dealer ID'] = dealer_ids
df['Mobile No.'] = mobile_nos
df['Call received from Registered Number (Y/N)'] = registered_statuses
df['Order Executed (Y/N)'] = order_executed_statuses
df['Call Extract'] = call_extracts
df['Observation'] = observations

df.to_excel(OUTPUT_FILE, index=False)
print(f"New Excel file created with all required columns: {OUTPUT_FILE}") 