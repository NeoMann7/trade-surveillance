import pandas as pd
import os
import openai
from datetime import datetime
from dotenv import load_dotenv
import json
from collections import defaultdict
import re
import numpy as np

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

def get_transcript_path(filename, transcripts_path):
    if filename.endswith('.wav'):
        return os.path.join(transcripts_path, filename + '.txt')
    elif filename.endswith('.wav.txt'):
        return os.path.join(transcripts_path, filename)
    else:
        return os.path.join(transcripts_path, filename + '.txt')

def build_ai_prompt(order_group, transcript_content, audio_file):
    prompt_orders = []
    for order in order_group:
        prompt_orders.append(f"Order ID: {order['order_id']}\n- Symbol: {order['symbol']}\n- Quantity: {order['quantity']}\n- Price: {order['price']}\n- Buy/Sell: {order['side']}\n- Order Time: {order['order_time']}")
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
- audio_mapped ("yes")
- order_discussed ("yes"/"no")
- discrepancy ("yes"/"no"/"none", with brief explanation if yes)
- complaint ("yes"/"no"/"none", with brief explanation if yes)
- action ("none"/"review"/"investigate"/"reverse")
- ai_reasoning (brief explanation)
Return a JSON array, one object per order. If an order is not discussed, set order_discussed to "no" and explain in ai_reasoning.
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
            
            # Use different parameters based on model
            if model_name == "o3":
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": "You are an expert financial compliance analyst. Analyze trading orders and call transcripts for compliance and audit purposes."},
                        {"role": "user", "content": prompt}
                    ]
                )
            else:
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": "You are an expert financial compliance analyst. Analyze trading orders and call transcripts for compliance and audit purposes."},
                        {"role": "user", "content": prompt}
                    ]
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
            print(f"  [AI] Switching to gpt-4 for {audio_file}...")
            # Try gpt-4 model
            for gpt_attempt in range(1, 3):
                result, error = call_openai_model("gpt-4", gpt_attempt, 2)
                if result is not None:
                    return result
                if gpt_attempt == 2:
                    print(f"  [AI] All retries failed for {audio_file} on gpt-4.")
                    return [{
                        'order_id': order.get('order_id', ''),
                        'audio_mapped': 'yes',
                        'order_discussed': 'no',
                        'discrepancy': 'none',
                        'complaint': 'none',
                        'action': 'none',
                        'ai_reasoning': f'AI response empty or invalid after retries on both o3 and gpt-4.'
                    } for order in order_group]

def analyze_orders_for_date(date_str):
    """
    Analyze orders with transcripts for a specific date in August or September
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
    audio_order_file = f"{month_name}/Daily_Reports/{date_str}/audio_order_kl_orgtimestamp_validation_{date_str}.xlsx"
    transcripts_path = f"{month_name}/Daily_Reports/{date_str}/transcripts_{date_str}"
    output_path = f"{month_name}/Daily_Reports/{date_str}/order_transcript_analysis_{date_str}.xlsx"
    progress_file = f"{month_name}/Daily_Reports/{date_str}/order_transcript_analysis_progress_{date_str}.jsonl"
    
    # Check if input files exist
    if not os.path.exists(audio_order_file):
        print(f"Audio-order validation file not found: {audio_order_file}")
        return None
    
    if not os.path.exists(transcripts_path):
        print(f"Transcripts directory not found: {transcripts_path}")
        return None
    
    # Load audio-order mapping
    try:
        mapping_df = pd.read_excel(audio_order_file, sheet_name='Order_Audio_Mapping')
        print(f"Loaded {len(mapping_df)} order-audio mappings")
    except Exception as e:
        print(f"Error loading audio-order mapping: {e}")
        return None
    
    # Get all KL orders and orders with audio
    all_kl_orders = mapping_df.copy()
    orders_with_audio = mapping_df[mapping_df['has_audio'] == 'Y'].copy()
    print(f"Found {len(all_kl_orders)} total KL orders")
    print(f"Found {len(orders_with_audio)} orders with audio")
    
    if len(all_kl_orders) == 0:
        print("No KL orders found")
        return None
    
    # Process orders with audio - consolidate audio clusters to avoid duplication
    consolidated_orders = []
    processed_orders = set()
    
    for _, order in orders_with_audio.iterrows():
        order_id = order['order_id']
        
        # Skip if already processed (to avoid duplicates)
        if order_id in processed_orders:
            continue
            
        audio_files = order['mapped_audio_filenames'].split(',') if pd.notna(order['mapped_audio_filenames']) else []
        audio_files = [f.strip() for f in audio_files if f.strip()]
        
        if audio_files:
            # Create consolidated order entry
            consolidated_order = order.copy()
            consolidated_order['audio_file'] = ','.join(audio_files)  # Store all audio files
            consolidated_order['audio_cluster'] = 'consolidated'  # Mark as consolidated
            consolidated_orders.append(consolidated_order)
            processed_orders.add(order_id)
    
    if not consolidated_orders:
        print("No orders with valid audio files found")
        # Still create report with all KL orders
        all_kl_orders['audio_mapped'] = 'no'
        all_kl_orders['order_discussed'] = 'no'
        all_kl_orders['discrepancy'] = 'none'
        all_kl_orders['complaint'] = 'none'
        all_kl_orders['action'] = 'none'
        all_kl_orders['ai_reasoning'] = 'No audio mapping found for this order'
        all_kl_orders['audio_file'] = ''
        
        # Rename columns
        all_kl_orders = all_kl_orders.rename(columns={
            'ExchOrderID': 'order_id',
            'Symbol': 'symbol',
            'Qty': 'quantity',
            'Price': 'price',
            'BuySell': 'side',
            'OrgTimeStamp': 'order_time',
            'User': 'user',
            'Status': 'status'
        })
        
        all_kl_orders.to_excel(output_path, index=False)
        print(f"\nAnalysis completed! Results saved to: {output_path}")
        print(f"Total KL orders in final report: {len(all_kl_orders)} (no audio mappings found)")
        return output_path
    
    # Convert to DataFrame
    orders_with_audio = pd.DataFrame(consolidated_orders)
    
    # Group orders by audio file (now consolidated)
    audio_groups = orders_with_audio.groupby('audio_file')
    
    # Initialize results list
    all_results = []
    
    # Load progress if exists
    processed_orders = set()
    if os.path.exists(progress_file):
        with open(progress_file, 'r') as f:
            for line in f:
                try:
                    data = json.loads(line.strip())
                    processed_orders.add(data.get('order_id', ''))
                except:
                    continue
        print(f"Loaded {len(processed_orders)} previously processed orders")
    
    # Process each audio file group
    for audio_file, group in audio_groups:
        print(f"\nProcessing audio file: {audio_file}")
        print(f"Orders in this audio: {len(group)}")
        print(f"DEBUG: About to check if orders already processed...")
        
        # Check if all orders in this group are already processed
        group_order_ids = set(group['order_id'].astype(str))
        if group_order_ids.issubset(processed_orders):
            print(f"All orders in {audio_file} already processed, skipping...")
            continue
        
        # Load transcript
        print(f"DEBUG: About to load transcript for {audio_file}")
        # Handle consolidated audio files (multiple files combined)
        if ',' in audio_file:  # Multiple audio files (consolidated)
            # Combine transcripts from multiple audio files
            audio_files_list = [f.strip() for f in audio_file.split(',')]
            combined_transcript = []
            
            for single_audio_file in audio_files_list:
                transcript_file = get_transcript_path(single_audio_file, transcripts_path)
                if os.path.exists(transcript_file):
                    transcript_content = read_transcript_file(transcript_file)
                    if transcript_content:
                        combined_transcript.append(f"=== {single_audio_file} ===")
                        combined_transcript.append(transcript_content)
                        combined_transcript.append("")  # Add separator
            
            transcript_content = "\n".join(combined_transcript)
            if not transcript_content.strip():
                print(f"Empty combined transcript for {audio_file}")
                continue
        else:  # Single audio file
            transcript_file = get_transcript_path(audio_file, transcripts_path)
            if not os.path.exists(transcript_file):
                print(f"Transcript not found: {transcript_file}")
                continue
            
            transcript_content = read_transcript_file(transcript_file)
            if not transcript_content:
                print(f"Empty transcript for {audio_file}")
                continue
        
        # Convert group to list of dictionaries for analysis
        order_group = []
        for _, order in group.iterrows():
            order_group.append({
                'order_id': order['order_id'],
                'symbol': order['symbol'],
                'quantity': order['quantity'],
                'price': order['price'],
                'side': order['side'],
                'order_time': order['order_time'],
                'user': order['user'],
                'status': order['status'],
                'audio_file': audio_file,
                'client_id': order['client_id']
            })
        
        # Analyze orders with AI
        print(f"DEBUG: About to call AI analysis for {len(order_group)} orders...")
        analysis_results = analyze_orders_with_audio(order_group, transcript_content, audio_file)
        print(f"DEBUG: AI analysis completed, got {len(analysis_results) if analysis_results else 0} results")
        
        if analysis_results:
            # Combine original order data with AI analysis
            for i, (_, order) in enumerate(group.iterrows()):
                if i < len(analysis_results):
                    ai_result = analysis_results[i]
                    result = {
                        'order_id': order['order_id'],
                        'symbol': order['symbol'],
                        'quantity': order['quantity'],
                        'price': order['price'],
                        'side': order['side'],
                        'order_time': order['order_time'],
                        'user': order['user'],
                        'status': order['status'],
                        'audio_file': audio_file,
                        'client_id': order['client_id'],
                        'audio_mapped': ai_result.get('audio_mapped', 'yes'),
                        'order_discussed': ai_result.get('order_discussed', 'no'),
                        'discrepancy': ai_result.get('discrepancy', 'none'),
                        'complaint': ai_result.get('complaint', 'none'),
                        'action': ai_result.get('action', 'none'),
                        'ai_reasoning': ai_result.get('ai_reasoning', '')
                    }
                    all_results.append(result)
                    
                    # Save progress (convert timestamp to string for JSON serialization)
                    progress_result = result.copy()
                    if 'order_time' in progress_result and pd.notna(progress_result['order_time']):
                        progress_result['order_time'] = str(progress_result['order_time'])
                    with open(progress_file, 'a') as f:
                        f.write(json.dumps(progress_result) + '\n')
                    
                    processed_orders.add(str(order['order_id']))
        else:
            print(f"Failed to analyze orders for {audio_file}")
    
    # Create final DataFrame with all KL orders
    if all_results:
        # Create DataFrame from analyzed orders
        analyzed_df = pd.DataFrame(all_results)
        
        # Get all KL orders that weren't analyzed (no audio mapping)
        analyzed_order_ids = set(analyzed_df['order_id'].astype(str))
        orders_without_audio = all_kl_orders[~all_kl_orders['order_id'].astype(str).isin(analyzed_order_ids)].copy()
        
        # Add default values for orders without audio
        if len(orders_without_audio) > 0:
            orders_without_audio['audio_mapped'] = 'no'
            orders_without_audio['order_discussed'] = 'no'
            orders_without_audio['discrepancy'] = 'none'
            orders_without_audio['complaint'] = 'none'
            orders_without_audio['action'] = 'none'
            orders_without_audio['ai_reasoning'] = 'No audio mapping found for this order'
            orders_without_audio['audio_file'] = ''
            
            # Rename columns to match analyzed_df
            orders_without_audio = orders_without_audio.rename(columns={
                'ExchOrderID': 'order_id',
                'Symbol': 'symbol',
                'Qty': 'quantity',
                'Price': 'price',
                'BuySell': 'side',
                'OrgTimeStamp': 'order_time',
                'User': 'user',
                'Status': 'status'
            })
            
            # Select only the columns that exist in analyzed_df
            common_columns = [col for col in orders_without_audio.columns if col in analyzed_df.columns]
            orders_without_audio = orders_without_audio[common_columns]
            
            # Combine analyzed and non-analyzed orders
            results_df = pd.concat([analyzed_df, orders_without_audio], ignore_index=True)
        else:
            results_df = analyzed_df
        
        results_df.to_excel(output_path, index=False)
        print(f"\nAnalysis completed! Results saved to: {output_path}")
        print(f"Total orders analyzed: {len(analyzed_df)}")
        print(f"Total orders without audio: {len(orders_without_audio) if len(orders_without_audio) > 0 else 0}")
        print(f"Total KL orders in final report: {len(results_df)}")
        return output_path
    else:
        # If no orders were analyzed, still create report with all KL orders
        all_kl_orders['audio_mapped'] = 'no'
        all_kl_orders['order_discussed'] = 'no'
        all_kl_orders['discrepancy'] = 'none'
        all_kl_orders['complaint'] = 'none'
        all_kl_orders['action'] = 'none'
        all_kl_orders['ai_reasoning'] = 'No audio mapping found for this order'
        all_kl_orders['audio_file'] = ''
        
        # Rename columns
        all_kl_orders = all_kl_orders.rename(columns={
            'ExchOrderID': 'order_id',
            'Symbol': 'symbol',
            'Qty': 'quantity',
            'Price': 'price',
            'BuySell': 'side',
            'OrgTimeStamp': 'order_time',
            'User': 'user',
            'Status': 'status'
        })
        
        all_kl_orders.to_excel(output_path, index=False)
        print(f"\nAnalysis completed! Results saved to: {output_path}")
        print(f"Total KL orders in final report: {len(all_kl_orders)} (no audio mappings found)")
        return output_path

if __name__ == "__main__":
    import sys
    
    # Get date from command line argument or use default
    if len(sys.argv) > 1:
        date_str = sys.argv[1]
    else:
        # Default date (August 7th, 2025)
        date_str = "07082025"
    
    result = analyze_orders_for_date(date_str)
    if result:
        print(f"Successfully processed {date_str}")
    else:
        print(f"Failed to process {date_str}")
        sys.exit(1) 