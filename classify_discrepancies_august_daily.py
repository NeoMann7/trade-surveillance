#!/usr/bin/env python3
"""
Discrepancy Classification Script
Classifies discrepancies into 'actual' vs 'reporting' using GPT-4.1

Usage:
    python classify_discrepancies_august_daily.py 25082025
"""

import sys
import os
import pandas as pd
from openai import OpenAI
from datetime import datetime
import time
import json
import tempfile
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# S3 Configuration
USE_S3 = os.getenv('USE_S3', 'false').lower() == 'true'
S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME')
S3_BASE_PREFIX = os.getenv('S3_BASE_PREFIX', 'trade_surveillance')

# Check if S3 is available (boto3 imported successfully)
S3_AVAILABLE = False
try:
    import boto3
    from s3_utils import (
        s3_file_exists, read_excel_from_s3, upload_file_to_s3
    )
    S3_AVAILABLE = True
except ImportError:
    print("Boto3 not installed, S3 functions will not be available.")
except Exception as e:
    print(f"Error importing S3 utilities: {e}")

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def classify_discrepancy_with_ai(discrepancy_text):
    """
    Classify a discrepancy using GPT-4.1
    
    Returns:
        dict: {'type': 'actual'|'reporting', 'confidence': 0.0-1.0}
    """
    
    prompt = f"""
You are a trade surveillance expert. Classify the discrepancy below into one of two categories based on these definitions:

ACTUAL DISCREPANCY — The dealer's execution/booking does not match the client's instruction (e.g., wrong price/quantity/side/instrument; limit breached; over/under-fill; booked price/qty differs from executed fills). This reflects a trading error that affected the trade.

REPORTING DISCREPANCY — The trade was executed and booked correctly per the client's instruction, but the dealer misstated the price/quantity in communications back to the client (chat/email/phone), e.g., client asked "market," OMS shows ₹100, dealer told client "₹102."

IMPORTANT: Minor price differences (≤₹1-2) with client consent are REPORTING discrepancies, not actual discrepancies.

Decision Rules

If execution or booking deviates from the client's instruction → classify actual.

If execution and booking match the instruction, and only the communicated quote/confirmation is wrong → classify reporting.

If execution correctness is unclear/ambiguous → classify actual.

If price difference is minimal (≤₹1-2) and client consented → classify reporting.

Discrepancy to classify:
"{discrepancy_text}"

Respond with ONLY this JSON:
{{
"type": "actual" or "reporting",
"confidence": 0.0 to 1.0
}}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {"role": "system", "content": "You are a trade surveillance expert. Respond only with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=100
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # Parse JSON response
        try:
            result = json.loads(result_text)
            return {
                'type': result.get('type', 'actual'),
                'confidence': float(result.get('confidence', 0.8))
            }
        except json.JSONDecodeError:
            print(f"⚠️  Invalid JSON response: {result_text}")
            return {'type': 'actual', 'confidence': 0.5}
            
    except Exception as e:
        print(f"⚠️  AI classification failed: {e}")
        return {'type': 'actual', 'confidence': 0.5}

def classify_discrepancies_for_date(date_str):
    """
    Classify discrepancies for a specific date
    """
    print(f"🔍 Starting discrepancy classification for {date_str}")
    
    # Determine month and set paths
    month = int(date_str[2:4])
    month_names = {
        1: "January", 2: "February", 3: "March", 4: "April",
        5: "May", 6: "June", 7: "July", 8: "August",
        9: "September", 10: "October", 11: "November", 12: "December"
    }
    
    if month not in month_names:
        print(f"❌ Invalid month: {month}")
        return False
    
    month_name = month_names[month]
    excel_file = f"{month_name}/Daily_Reports/{date_str}/Final_Trade_Surveillance_Report_{date_str}_with_Email_and_Trade_Analysis.xlsx"
    
    # Get S3 key if using S3
    if USE_S3 and S3_AVAILABLE:
        excel_s3_key = f"{S3_BASE_PREFIX}/{excel_file}"
        
        # Check if file exists in S3
        if not s3_file_exists(excel_s3_key):
            print(f"❌ Excel file not found in S3: {excel_s3_key}")
            return False
        
        # Load Excel file from S3
        try:
            df = read_excel_from_s3(excel_s3_key)
            print(f"📊 Loaded Excel file from S3 with {len(df)} rows")
        except Exception as e:
            print(f"❌ Error loading Excel file from S3: {e}")
            import traceback
            traceback.print_exc()
            return False
    else:
        # Local filesystem
        # Check if file exists
        if not os.path.exists(excel_file):
            print(f"❌ Excel file not found: {excel_file}")
            return False
        
        # Load Excel file
        try:
            df = pd.read_excel(excel_file)
            print(f"📊 Loaded Excel file with {len(df)} rows")
        except Exception as e:
            print(f"❌ Error loading Excel file: {e}")
            return False
    
    # Check if discrepancy column exists
    if 'discrepancy' not in df.columns:
        print(f"❌ 'discrepancy' column not found in Excel file")
        return False
    
    # Filter rows with actual discrepancies
    discrepancy_rows = df[df['discrepancy'].notna() & (df['discrepancy'] != 'none') & (df['discrepancy'] != 'no')]
    print(f"🔍 Found {len(discrepancy_rows)} discrepancies to classify")
    
    if len(discrepancy_rows) == 0:
        print(f"ℹ️  No discrepancies found to classify")
        # Still add empty columns
        df['discrepancy_type'] = None
        df['discrepancy_confidence'] = None
    else:
        # Initialize classification columns
        df['discrepancy_type'] = None
        df['discrepancy_confidence'] = None
        
        # Classify each discrepancy
        for idx, row in discrepancy_rows.iterrows():
            discrepancy_text = str(row['discrepancy'])
            print(f"🤖 Classifying: {discrepancy_text[:100]}...")
            
            # Get AI classification
            classification = classify_discrepancy_with_ai(discrepancy_text)
            
            # Update DataFrame
            df.at[idx, 'discrepancy_type'] = classification['type']
            df.at[idx, 'discrepancy_confidence'] = classification['confidence']
            
            print(f"   ✅ Classified as: {classification['type']} (confidence: {classification['confidence']:.2f})")
            
            # Small delay to avoid rate limiting
            time.sleep(0.5)
    
    # Save updated Excel file
    try:
        # Save to temporary file first
        temp_output_file = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
        df.to_excel(temp_output_file.name, index=False)
        
        # Upload to S3 or save locally
        if USE_S3 and S3_AVAILABLE:
            upload_file_to_s3(temp_output_file.name, excel_s3_key)
            print(f"💾 Updated Excel file saved to S3: {excel_s3_key}")
        else:
            import shutil
            shutil.move(temp_output_file.name, excel_file)
            print(f"💾 Updated Excel file saved: {excel_file}")
        
        # Clean up temp file
        if os.path.exists(temp_output_file.name):
            os.unlink(temp_output_file.name)
        
        # Print summary
        if 'discrepancy_type' in df.columns:
            actual_count = len(df[df['discrepancy_type'] == 'actual'])
            reporting_count = len(df[df['discrepancy_type'] == 'reporting'])
            print(f"📊 Classification Summary:")
            print(f"   Actual discrepancies: {actual_count}")
            print(f"   Reporting discrepancies: {reporting_count}")
            print(f"   Total classified: {actual_count + reporting_count}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error saving Excel file: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main execution function"""
    print("🤖 DISCREPANCY CLASSIFICATION SYSTEM")
    print("=" * 50)
    
    # Check command line arguments
    if len(sys.argv) != 2:
        print("❌ Usage: python classify_discrepancies_august_daily.py <DATE>")
        print("📅 Example: python classify_discrepancies_august_daily.py 25082025")
        print("📅 Date format: DDMMYYYY (e.g., 25082025 for August 25, 2025)")
        sys.exit(1)
    
    date_str = sys.argv[1]
    
    # Validate date format
    if len(date_str) != 8:
        print(f"❌ Invalid date format: {date_str}")
        print("📅 Expected format: DDMMYYYY (e.g., 25082025)")
        sys.exit(1)
    
    print(f"📅 Processing date: {date_str}")
    print(f"🕐 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check OpenAI API key
    if not os.getenv('OPENAI_API_KEY'):
        print("❌ OpenAI API key not found. Please set OPENAI_API_KEY in .env file")
        sys.exit(1)
    
    # Run classification
    start_time = time.time()
    success = classify_discrepancies_for_date(date_str)
    end_time = time.time()
    
    duration = end_time - start_time
    print(f"⏱️  Classification took {duration:.2f} seconds ({duration/60:.1f} minutes)")
    
    if success:
        print(f"🎉 Discrepancy classification completed successfully!")
        sys.exit(0)
    else:
        print(f"❌ Discrepancy classification failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
