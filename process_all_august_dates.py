#!/usr/bin/env python3
"""
Process all August dates that have order files
"""

import os
import subprocess
import sys
from datetime import datetime

def check_order_file_exists(date_str):
    """Check if order file exists for the given date"""
    order_file = f"August/Order Files/OrderBook-Closed-{date_str}.csv"
    return os.path.exists(order_file)

def process_date(date_str):
    """Process a single date"""
    print(f"\n{'='*60}")
    print(f"📅 PROCESSING {date_str}")
    print(f"{'='*60}")
    
    # Check if order file exists
    if not check_order_file_exists(date_str):
        print(f"❌ No order file found for {date_str}, skipping...")
        return False
    
    # Run the email processing script
    try:
        result = subprocess.run([
            sys.executable, "email_processing/process_emails_by_date.py", date_str
        ], capture_output=True, text=True)
        
        print(result.stdout)
        if result.stderr:
            print("Errors:", result.stderr)
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ Error processing {date_str}: {str(e)}")
        return False

def main():
    """Process all August dates"""
    print("🚀 PROCESSING ALL AUGUST DATES")
    print("=" * 60)
    
    # Dates to process (those that have order files)
    dates_to_process = [
        "2025-08-05",
        "2025-08-06", 
        "2025-08-07",
        "2025-08-08",
        "2025-08-11",
        "2025-08-12",
        "2025-08-13",
        "2025-08-14"
    ]
    
    successful_dates = []
    failed_dates = []
    
    for date_str in dates_to_process:
        success = process_date(date_str)
        if success:
            successful_dates.append(date_str)
        else:
            failed_dates.append(date_str)
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 FINAL SUMMARY")
    print(f"{'='*60}")
    print(f"✅ Successful: {len(successful_dates)} dates")
    print(f"❌ Failed: {len(failed_dates)} dates")
    
    if successful_dates:
        print(f"\n✅ Successfully processed:")
        for date in successful_dates:
            print(f"   - {date}")
    
    if failed_dates:
        print(f"\n❌ Failed to process:")
        for date in failed_dates:
            print(f"   - {date}")
    
    print(f"\n🎉 Processing complete!")

if __name__ == "__main__":
    main() 