#!/usr/bin/env python3
"""
Daily Email Fetch Job
Runs locally (outside Docker) to fetch emails from Graph API and store to S3

Usage:
    python email_fetch_daily_job.py 2025-12-23
    python email_fetch_daily_job.py 23122025
"""

import sys
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path (for dashboard.backend imports)
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
# Add email_processing to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the existing email processing function
from email_processing.process_emails_by_date import process_emails_for_date

# S3 Configuration
USE_S3 = os.getenv('USE_S3', 'true').lower() == 'true'
S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME', 'icmemo-documents-prod')
S3_BASE_PREFIX = os.getenv('S3_BASE_PREFIX', 'trade_surveillance')

# Import S3 utilities
S3_AVAILABLE = False
try:
    import boto3
    # Try importing from dashboard.backend first (if running from project root)
    try:
        from dashboard.backend.s3_utils import upload_file_to_s3, s3_file_exists
    except ImportError:
        # Try importing directly (if s3_utils is in path)
        from s3_utils import upload_file_to_s3, s3_file_exists
    S3_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ S3 utilities not available: {e}")
    print("💡 Install boto3: pip install boto3")
    print("💡 Ensure dashboard/backend/s3_utils.py is accessible")
    sys.exit(1)

def upload_email_data_to_s3(date_str, local_json_path):
    """
    Upload processed email JSON to S3
    
    Args:
        date_str: Date in DDMMYYYY format (e.g., '23122025')
        local_json_path: Path to local JSON file
    """
    try:
        # Parse date to get year and month
        date_obj = datetime.strptime(date_str, '%d%m%Y')
        year = date_obj.strftime('%Y')
        month_names = {
            1: "January", 2: "February", 3: "March", 4: "April",
            5: "May", 6: "June", 7: "July", 8: "August",
            9: "September", 10: "October", 11: "November", 12: "December"
        }
        month_name = month_names[date_obj.month]
        
        # S3 path: trade_surveillance/Email_Data/{year}/{month}/email_surveillance_{date}.json
        s3_key = f"{S3_BASE_PREFIX}/Email_Data/{year}/{month_name}/email_surveillance_{date_str}.json"
        
        # Upload to S3
        upload_file_to_s3(local_json_path, s3_key)
        print(f"✅ Uploaded email data to S3: s3://{S3_BUCKET_NAME}/{s3_key}")
        return s3_key
        
    except Exception as e:
        print(f"❌ Error uploading to S3: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """Main execution function"""
    print("📧 Daily Email Fetch Job")
    print("=" * 50)
    
    # Parse date argument
    if len(sys.argv) < 2:
        print("❌ Usage: python email_fetch_daily_job.py <DATE>")
        print("📅 Examples:")
        print("   python email_fetch_daily_job.py 2025-12-23")
        print("   python email_fetch_daily_job.py 23122025")
        sys.exit(1)
    
    date_input = sys.argv[1]
    
    # Convert date to required formats
    try:
        # Try YYYY-MM-DD format first
        if '-' in date_input:
            date_obj = datetime.strptime(date_input, '%Y-%m-%d')
            formatted_date = date_input  # YYYY-MM-DD for process_emails_for_date
            date_str = date_obj.strftime('%d%m%Y')  # DDMMYYYY for file naming
        else:
            # Assume DDMMYYYY format
            date_obj = datetime.strptime(date_input, '%d%m%Y')
            date_str = date_input  # DDMMYYYY
            formatted_date = date_obj.strftime('%Y-%m-%d')  # YYYY-MM-DD
    except ValueError:
        print(f"❌ Invalid date format: {date_input}")
        print("📅 Expected format: YYYY-MM-DD or DDMMYYYY")
        sys.exit(1)
    
    print(f"📅 Processing date: {formatted_date} ({date_str})")
    print(f"🕐 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("")
    
    # Check S3 availability
    if not USE_S3 or not S3_AVAILABLE:
        print("❌ S3 is not available. Please configure S3 credentials.")
        sys.exit(1)
    
    # Step 1: Process emails using existing logic (same as before)
    print("📧 Step 1: Fetching and processing emails from Graph API...")
    print("-" * 50)
    
    success = process_emails_for_date(formatted_date)
    
    if not success:
        print("❌ Email processing failed!")
        sys.exit(1)
    
    # Step 2: Find the generated JSON file
    # The process_emails_for_date function saves to: email_surveillance_{date_str}.json
    # Check current directory first, then check if it's in a specific location
    local_json_file = f"email_surveillance_{date_str}.json"
    
    if not os.path.exists(local_json_file):
        # Try in email_processing directory
        email_processing_dir = os.path.join(os.path.dirname(__file__), 'email_processing')
        local_json_file = os.path.join(email_processing_dir, f"email_surveillance_{date_str}.json")
        
        if not os.path.exists(local_json_file):
            # Try in current working directory with full path
            import glob
            possible_files = glob.glob(f"**/email_surveillance_{date_str}.json", recursive=True)
            if possible_files:
                local_json_file = possible_files[0]
            else:
                print(f"❌ Could not find generated email file: email_surveillance_{date_str}.json")
                print("🔍 Searched in current directory and email_processing directory")
                sys.exit(1)
    
    print(f"✅ Found email data file: {local_json_file}")
    
    # Step 3: Upload to S3
    print("")
    print("📦 Step 2: Uploading to S3...")
    print("-" * 50)
    
    s3_key = upload_email_data_to_s3(date_str, local_json_file)
    
    if not s3_key:
        print("❌ Failed to upload to S3!")
        sys.exit(1)
    
    # Step 4: Summary
    print("")
    print("=" * 50)
    print("✅ Daily email fetch job completed successfully!")
    print(f"📁 S3 Location: s3://{S3_BUCKET_NAME}/{s3_key}")
    print(f"🕐 Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("")
    print("💡 The email data is now available in S3 for the surveillance pipeline.")

if __name__ == "__main__":
    main()

