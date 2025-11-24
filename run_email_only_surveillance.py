#!/usr/bin/env python3
"""
Email-Only Trade Surveillance Processor
======================================
This script runs only the email surveillance part and generates the final unified report.
It skips audio analysis and uses existing audio results.
"""

import os
import sys
import subprocess
import time
from datetime import datetime

def print_header():
    """Print the header for the surveillance process."""
    print("🚀 EMAIL-ONLY TRADE SURVEILLANCE PROCESSOR")
    print("=" * 60)
    print("📅 Processing date: 01082025")
    print(f"🕐 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

def run_step(step_name, script_name, description):
    """Run a single step of the surveillance process."""
    print(f"🎯 Step: {step_name}")
    print("=" * 60)
    print(f"📜 Script: {script_name}")
    print(f"📝 Description: {description}")
    print()
    
    start_time = time.time()
    
    try:
        # Run the script
        result = subprocess.run(['python', script_name], 
                              capture_output=True, text=True, check=True)
        
        duration = time.time() - start_time
        
        print(f"✅ {step_name} completed successfully!")
        print(f"⏱️  Duration: {duration:.2f} seconds")
        print(f"📤 Output:\n{result.stdout}")
        
        return True, duration
        
    except subprocess.CalledProcessError as e:
        duration = time.time() - start_time
        
        print(f"❌ {step_name} failed!")
        print(f"⏱️  Duration: {duration:.2f} seconds")
        print(f"🔍 Error Code: {e.returncode}")
        print(f"📥 Error:\n{e.stderr}")
        
        return False, duration

def main():
    """Main function to run the email-only surveillance process."""
    
    if len(sys.argv) != 2:
        print("❌ Usage: python run_email_only_surveillance.py <date>")
        print("   Example: python run_email_only_surveillance.py 01082025")
        sys.exit(1)
    
    date_str = sys.argv[1]
    
    print_header()
    
    # Define steps
    steps = [
        {
            'name': 'Email Surveillance with GPT-4.1-Mini',
            'script': 'complete_email_surveillance_system_gpt41.py',
            'description': 'Process all emails with GPT-4.1-mini using full email body'
        },
        {
            'name': 'Email-Order Validation & Mapping',
            'script': 'email_order_validation_august_daily.py',
            'description': 'Match email trade instructions to KL orders using enhanced matching'
        },
        {
            'name': 'Final Required Columns Mapping',
            'script': 'add_required_columns_to_excel_august_daily.py',
            'description': 'Add email columns to final Excel report'
        }
    ]
    
    total_duration = 0
    successful_steps = 0
    failed_steps = []
    
    # Run each step
    for i, step in enumerate(steps, 1):
        print(f"🎯 Step {i}/{len(steps)}: {step['name']}")
        print("=" * 60)
        print(f"📜 Script: {step['script']}")
        print(f"📝 Description: {step['description']}")
        print()
        
        success, duration = run_step(step['name'], step['script'], step['description'])
        total_duration += duration
        
        if success:
            successful_steps += 1
        else:
            failed_steps.append(step['name'])
            print(f"❌ Step {i} failed. Stopping execution.")
            break
        
        print()
    
    # Print summary
    print("=" * 60)
    print("📊 EXECUTION SUMMARY")
    print("=" * 60)
    print(f"📅 Date: {date_str}")
    print(f"🕐 Total Duration: {total_duration:.2f} seconds ({total_duration/60:.1f} minutes)")
    print(f"✅ Successful Steps: {successful_steps}/{len(steps)}")
    print()
    
    if successful_steps == len(steps):
        print("🎉 FINAL REPORT CREATED!")
        print(f"📁 Location: August/Daily_Reports/{date_str}/order_transcript_analysis_{date_str}_with_required_columns.xlsx")
        print("📊 Check the Excel file for complete analysis results.")
        print()
        print("🎉 All steps completed successfully!")
    else:
        print("❌ Some steps failed. Check the output above for details.")
        if failed_steps:
            print("❌ Failed Steps:")
            for step in failed_steps:
                print(f"   ✗ {step}")

if __name__ == "__main__":
    main() 