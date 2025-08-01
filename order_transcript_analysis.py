import pandas as pd
import os
import openai
from datetime import datetime
from dotenv import load_dotenv
import json
from collections import defaultdict
import re
import numpy as np

# === CONFIGURATION ===
# Set to None to process all dates, or specify a date like '2025-07-05 00:00:00'
PROCESS_DATE = None  # Process all dates
AUDIO_MAPPING_FILE = 'July/audio_order_kl_orgtimestamp_validation.xlsx'
TRANSCRIPTS_DIR = 'July/transcripts/'
PROGRESS_JSONL = f'order_transcript_analysis_progress_july_all_dates.jsonl'
# Load existing progress from June 5th file to avoid reprocessing
EXISTING_PROGRESS_FILE = 'order_transcript_analysis_progress_2025-06-05 00:00:00.jsonl'

# Load environment variables
load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')

def read_transcript_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return ""

def get_transcript_path(filename):
    if filename.endswith('.wav'):
        return os.path.join(TRANSCRIPTS_DIR, filename + '.txt')
    elif filename.endswith('.wav.txt'):
        return os.path.join(TRANSCRIPTS_DIR, filename)
    else:
        return os.path.join(TRANSCRIPTS_DIR, filename + '.txt')

def build_ai_prompt(order_group, transcript_content, audio_file):
    prompt_orders = []
    for order in order_group:
        prompt_orders.append(f"Order ID: {order['order_id']}\n- Symbol: {order['Symbol']}\n- Quantity: {order['Qty']}\n- Price: {order['Price']}\n- Buy/Sell: {order['BuySell']}\n- Order Time: {order['order_time']}")
    prompt = f"""
The following orders are mapped to this call transcript (audio file: {audio_file}):

{chr(10).join(prompt_orders)}

Transcript:
{transcript_content}

Instructions:
For each order, return a JSON object with these fields:
- order_id
- symbol
- qty
- price
- buy_sell
- order_time
- audio_mapped (\"yes\")
- order_discussed (\"yes\"/\"no\")
- discrepancy (\"yes\"/\"no\"/\"none\", with brief explanation if yes)
- complaint (\"yes\"/\"no\"/\"none\", with brief explanation if yes)
- action (\"none\"/\"review\"/\"investigate\"/\"reverse\")
- ai_reasoning (brief explanation)
Return a JSON array, one object per order. If an order is not discussed, set order_discussed to \"no\" and explain in ai_reasoning.
"""
    return prompt

def analyze_orders_with_audio(order_group, transcript_content, audio_file):
    prompt = build_ai_prompt(order_group, transcript_content, audio_file)
    prompt_length_chars = len(prompt)
    prompt_length_words = len(prompt.split())
    prompt_length_tokens = int(prompt_length_words * 0.75)  # rough estimate
    print(f"[DEBUG] Prompt length for {audio_file}: {prompt_length_chars} chars, {prompt_length_words} words, ~{prompt_length_tokens} tokens")

    def extract_json_array(text):
        """
        Extracts the first JSON array from a string.
        Returns the JSON string, or None if not found.
        """
        match = re.search(r'\[\s*{.*?}\s*\]', text, re.DOTALL)
        if match:
            return match.group(0)
        return None

    def call_openai_model(model_name, attempt, max_retries):
        try:
            client = openai.OpenAI()
            print(f"  [AI] Analyzing {audio_file} with {len(order_group)} orders... (Attempt {attempt}, Model: {model_name})")
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "You are an expert financial compliance analyst. Analyze trading orders and call transcripts for compliance and audit purposes."},
                    {"role": "user", "content": prompt}
                ],
                max_completion_tokens=1500
            )
            print(f"  [AI] Analysis complete.")
            # Try to parse JSON from response
            content = response.choices[0].message.content
            if not content or not content.strip():
                raise ValueError("Empty AI response")
            json_str = extract_json_array(content)
            if not json_str:
                # fallback: try to parse from first [
                json_start = content.find('[')
                if json_start == -1:
                    raise ValueError("No JSON array found in AI response")
                json_str = content[json_start:]
            result = json.loads(json_str)
            return result, None
        except Exception as e:
            print(f"  [AI] JSON parse error (Attempt {attempt}, Model: {model_name}): {e}")
            print(f"  [AI] Prompt was:\n{prompt}\n")
            if 'response' in locals():
                print(f"  [AI] Raw response was:\n{response.choices[0].message.content}\n")
            if attempt == max_retries:
                print(f"  [AI] All retries failed for {audio_file} on model {model_name}.")
            else:
                print(f"  [AI] Retrying...")
            return None, e
    # First try o3 model
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        result, error = call_openai_model("o3", attempt, max_retries)
        if result is not None:
            return result
        if attempt == max_retries:
            print(f"  [AI] Switching to gpt-4.1 for {audio_file}...")
            # Try gpt-4.1 model
            for gpt_attempt in range(1, 3):
                result, error = call_openai_model("gpt-4.1", gpt_attempt, 2)
                if result is not None:
                    return result
                if gpt_attempt == 2:
                    print(f"  [AI] All retries failed for {audio_file} on gpt-4-1106-preview.")
                    return [{
                        'order_id': order.get('order_id', ''),
                        'audio_mapped': 'yes',
                        'order_discussed': 'no',
                        'discrepancy': 'none',
                        'complaint': 'none',
                        'action': 'none',
                        'ai_reasoning': f'AI response empty or invalid after retries on both o3 and gpt-4-1106-preview.'
                    } for order in order_group]

def process_orders_with_mapping():
    date_filter = f" for {PROCESS_DATE}" if PROCESS_DATE else " (All Dates)"
    print(f"=== ORDER-TRANSCRIPT AI ANALYSIS (Grouped by Audio{date_filter}) ===\n")
    
    # Load existing progress to avoid reprocessing
    processed_orders = set()
    if os.path.exists(PROGRESS_JSONL):
        print(f"Loading existing progress from {PROGRESS_JSONL}...")
        with open(PROGRESS_JSONL, 'r') as f:
            for line in f:
                if line.strip():
                    try:
                        data = json.loads(line)
                        order_id = data.get('order_id', '')
                        if order_id:
                            processed_orders.add(str(order_id))
                    except:
                        continue
        print(f"Found {len(processed_orders)} already processed orders")
    
    # Load mapping
    mapping = pd.read_excel(AUDIO_MAPPING_FILE, sheet_name='Order_Audio_Mapping', dtype=str)
    if PROCESS_DATE:
        mapping = mapping[mapping['order_date'] == PROCESS_DATE]
    # Load all orders for extra details
    all_orders = pd.read_excel(AUDIO_MAPPING_FILE, sheet_name='All_KL_Orders', dtype=str)
    all_orders = all_orders.set_index('ExchOrderID')
    # Build: audio_file -> list of orders
    audio_to_orders = defaultdict(list)
    orderid_to_audiofiles = defaultdict(list)
    mapping_rows = {row['order_id']: row for _, row in mapping.iterrows()}
    for idx, row in mapping.iterrows():
        order_id = row['order_id']
        # Skip if already processed
        if str(order_id) in processed_orders:
            continue
        match_status = row['match_status']
        mapped_audio_filenames = row['mapped_audio_filenames']
        if match_status == 'matched_in_time_range' and pd.notna(mapped_audio_filenames) and mapped_audio_filenames:
            audio_files = [f.strip() for f in mapped_audio_filenames.split(',') if f.strip()]
            for audio_file in audio_files:
                # Get order details
                if order_id in all_orders.index:
                    order_details = all_orders.loc[order_id]
                    # Start with all columns from mapping row
                    order_dict = dict(row)
                    # Add/overwrite with extra columns from order details
                    order_dict.update({
                        'Symbol': order_details.get('Symbol', ''),
                        'Instrument': order_details.get('Instrument', ''),
                        'OpType': order_details.get('OpType', ''),
                        'Futures_Options': order_details.get('Futures_Options', ''),
                        'Qty': order_details.get('Qty', ''),
                        'Price': order_details.get('Price', ''),
                        'BuySell': order_details.get('BuySell', ''),
                        'order_time': order_details.get('order_time', ''),
                    })
                    audio_to_orders[audio_file].append(order_dict)
                    orderid_to_audiofiles[order_id].append(audio_file)
    # Track which orders have been analyzed/found
    order_results = {}
    # Append to existing file instead of overwriting
    with open(PROGRESS_JSONL, 'a') as jsonl_file:
        # For each audio file, analyze all mapped orders together
        for audio_file, order_group in audio_to_orders.items():
            transcript_path = get_transcript_path(audio_file)
            if not os.path.exists(transcript_path):
                print(f"[SKIP] Transcript not found for audio: {audio_file}")
                continue
            transcript_content = read_transcript_file(transcript_path)
            ai_results = analyze_orders_with_audio(order_group, transcript_content, audio_file)
            # For each order in this group, if not already found, record result
            for order_result in ai_results:
                oid = str(order_result.get('order_id'))
                if oid not in order_results or order_results[oid]['order_discussed'] != 'yes':
                    # Start with all columns from mapping row
                    base_row = dict(mapping_rows.get(oid, {}))
                    # Add/overwrite with extra columns from order details
                    if oid in all_orders.index:
                        order_details = all_orders.loc[oid]
                        base_row.update({
                            'Symbol': order_details.get('Symbol', ''),
                            'Instrument': order_details.get('Instrument', ''),
                            'OpType': order_details.get('OpType', ''),
                            'Futures_Options': order_details.get('Futures_Options', ''),
                            'Qty': order_details.get('Qty', ''),
                            'Price': order_details.get('Price', ''),
                            'BuySell': order_details.get('BuySell', ''),
                            'order_time': order_details.get('order_time', ''),
                        })
                    # Add/overwrite with AI results and audio file
                    base_row.update(order_result)
                    base_row['audio_file'] = audio_file
                    order_results[oid] = base_row
                    # Convert any pandas Series to simple values for JSON serialization
                    clean_row = {}
                    for key, value in base_row.items():
                        if isinstance(value, (pd.Series, np.ndarray, list)):
                            clean_row[key] = value.tolist() if hasattr(value, 'tolist') else list(value)
                        elif hasattr(value, 'item'):
                            try:
                                clean_row[key] = value.item()
                            except Exception:
                                clean_row[key] = str(value)
                        else:
                            clean_row[key] = value
                    jsonl_file.write(json.dumps(clean_row, ensure_ascii=False) + '\n')
                    jsonl_file.flush()
        # For orders not mapped to any audio, mark as 'No audio mapped'
        all_order_ids = set(mapping['order_id'])
        for oid in all_order_ids:
            if oid not in order_results:
                base_row = dict(mapping_rows.get(oid, {}))
                if oid in all_orders.index:
                    order_details = all_orders.loc[oid]
                    base_row.update({
                        'Symbol': order_details.get('Symbol', ''),
                        'Instrument': order_details.get('Instrument', ''),
                        'OpType': order_details.get('OpType', ''),
                        'Futures_Options': order_details.get('Futures_Options', ''),
                        'Qty': order_details.get('Qty', ''),
                        'Price': order_details.get('Price', ''),
                        'BuySell': order_details.get('BuySell', ''),
                        'order_time': order_details.get('order_time', ''),
                    })
                base_row.update({
                    'audio_file': '',
                    'audio_mapped': 'no',
                    'order_discussed': 'no',
                    'discrepancy': 'none',
                    'complaint': 'none',
                    'action': 'none',
                    'ai_reasoning': 'No audio mapped for this order.'
                })
                order_results[oid] = base_row
                # Convert any pandas Series to simple values for JSON serialization
                clean_row = {}
                for key, value in base_row.items():
                    if isinstance(value, (pd.Series, np.ndarray, list)):
                        clean_row[key] = value.tolist() if hasattr(value, 'tolist') else list(value)
                    elif hasattr(value, 'item'):
                        try:
                            clean_row[key] = value.item()
                        except Exception:
                            clean_row[key] = str(value)
                    else:
                        clean_row[key] = value
                jsonl_file.write(json.dumps(clean_row, ensure_ascii=False) + '\n')
                jsonl_file.flush()
    # Save results to Excel
    date_suffix = f"_{PROCESS_DATE}" if PROCESS_DATE else "_all_dates"
    output_file = f"July/order_transcript_analysis_mapping{date_suffix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    df_out = pd.DataFrame(list(order_results.values()))
    # Preserve the order of the original mapping sheet
    order_id_order = [oid for oid in mapping['order_id'] if pd.notna(oid)]
    df_out['order_id'] = pd.Categorical(df_out['order_id'], categories=order_id_order, ordered=True)
    df_out = df_out.sort_values('order_id')
    df_out.to_excel(output_file, index=False)
    print(f"\n=== ANALYSIS COMPLETE ===")
    date_info = f" for {PROCESS_DATE}" if PROCESS_DATE else " (All Dates)"
    print(f"Processed {len(df_out)} orders{date_info}")
    print(f"Results saved to: {output_file}")
    print(f"Progress log: {PROGRESS_JSONL}")

def main():
    process_orders_with_mapping()

if __name__ == "__main__":
    main() 