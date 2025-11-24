#!/usr/bin/env python3
"""
Master script for daily trade surveillance processing.
Executes all 7 steps automatically for a given date.

Usage:
    python run_daily_trade_surveillance.py 07082025
    python run_daily_trade_surveillance.py 01082025
"""

import sys
import os
import subprocess
import time
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import email processing function
try:
    from email_processing.process_emails_by_date import process_emails_for_date
    EMAIL_PROCESSING_AVAILABLE = True
except ImportError:
    EMAIL_PROCESSING_AVAILABLE = False

# Import file discovery mapper
try:
    from file_discovery_mapper import FileDiscoveryMapper
    FILE_DISCOVERY_AVAILABLE = True
except ImportError:
    FILE_DISCOVERY_AVAILABLE = False

def run_file_discovery_step(date_str):
    """Run file discovery and mapping step."""
    print(f"\n{'='*60}")
    print(f"🔄 STEP: File Discovery & Mapping")
    print(f"📅 Date: {date_str}")
    print(f"📜 Function: FileDiscoveryMapper")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    try:
        if not FILE_DISCOVERY_AVAILABLE:
            print(f"⚠️  File discovery module not available, skipping...")
            return True
        
        # Convert YYYYMMDD to YYYY-MM-DD format
        date_obj = datetime.strptime(date_str, '%d%m%Y')
        formatted_date = date_obj.strftime('%Y-%m-%d')
        
        print(f"🔍 Discovering uploaded files for {formatted_date}...")
        
        # Initialize file discovery mapper
        mapper = FileDiscoveryMapper()
        
        # Process uploaded files
        success, file_mappings = mapper.process_uploaded_files(formatted_date, replace_existing=True)
        
        if success:
            if file_mappings:
                print(f"✅ File discovery completed successfully")
                print(f"📁 Mapped {len(file_mappings)} files:")
                for original, target in file_mappings.items():
                    print(f"   📄 {os.path.basename(original)} -> {os.path.basename(target)}")
            else:
                print(f"ℹ️  No uploaded files found, using existing files")
        else:
            print(f"❌ File discovery failed")
            
    except Exception as e:
        print(f"❌ File discovery error: {e}")
        success = False
    
    end_time = time.time()
    duration = end_time - start_time
    print(f"⏱️  File discovery took {duration:.2f} seconds")
    
    return success

def run_email_processing_step(date_str):
    """Run email processing step using existing function."""
    print(f"\n{'='*60}")
    print(f"🔄 STEP: Email Processing")
    print(f"📅 Date: {date_str}")
    print(f"📜 Function: process_emails_for_date")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    try:
        # Convert YYYYMMDD to YYYY-MM-DD format
        date_obj = datetime.strptime(date_str, '%d%m%Y')
        formatted_date = date_obj.strftime('%Y-%m-%d')
        
        print(f"📧 Processing emails for {formatted_date}...")
        
        # Call existing email processing function
        success = process_emails_for_date(formatted_date)
        
        if success:
            # Rename output file to expected format
            old_file = f'email_surveillance_{formatted_date.replace("-", "")}.json'
            new_file = f'email_surveillance_{date_str}.json'
            
            if os.path.exists(old_file):
                os.rename(old_file, new_file)
                print(f"📁 Renamed {old_file} to {new_file}")
            
            end_time = time.time()
            duration = end_time - start_time
            
            print(f"✅ Email Processing completed successfully!")
            print(f"⏱️  Duration: {duration:.2f} seconds")
            return True
        else:
            end_time = time.time()
            duration = end_time - start_time
            
            print(f"❌ Email Processing failed!")
            print(f"⏱️  Duration: {duration:.2f} seconds")
            return False
            
    except Exception as e:
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"❌ Email Processing failed!")
        print(f"⏱️  Duration: {duration:.2f} seconds")
        print(f"📥 Error: {str(e)}")
        return False

def run_step(step_name, script_name, date_str):
    """Run a single step and return success status."""
    print(f"\n{'='*60}")
    print(f"🔄 STEP: {step_name}")
    print(f"📅 Date: {date_str}")
    print(f"📜 Script: {script_name}")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    try:
        # Run the script using subprocess with date parameter
        result = subprocess.run([
            sys.executable, script_name, date_str
        ], capture_output=True, text=True, check=True)
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"✅ {step_name} completed successfully!")
        print(f"⏱️  Duration: {duration:.2f} seconds")
        
        # Print any output from the script
        if result.stdout.strip():
            print(f"📤 Output:\n{result.stdout}")
        
        return True
        
    except subprocess.CalledProcessError as e:
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"❌ {step_name} failed!")
        print(f"⏱️  Duration: {duration:.2f} seconds")
        print(f"🔍 Error Code: {e.returncode}")
        
        if e.stdout.strip():
            print(f"📤 Output:\n{e.stdout}")
        if e.stderr.strip():
            print(f"📥 Error:\n{e.stderr}")
        
        return False
    except Exception as e:
        print(f"❌ Unexpected error in {step_name}: {str(e)}")
        return False

def validate_date_format(date_str):
    """Validate the date format (DDMMYYYY)."""
    if len(date_str) != 8:
        return False
    
    try:
        day = int(date_str[:2])
        month = int(date_str[2:4])
        year = int(date_str[4:])
        
        if day < 1 or day > 31:
            return False
        if month < 1 or month > 12:
            return False
        if year < 2000 or year > 2099:
            return False
            
        return True
    except ValueError:
        return False

def check_data_exists(date_str):
    """Check if required data files exist for the given date."""
    # Determine month and set paths accordingly
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
    call_dir = f"{month_name}/Call Records/Call_{date_str}"
    order_file = f"{month_name}/Order Files/OrderBook-Closed-{date_str}.csv"
    
    if not os.path.exists(call_dir):
        print(f"❌ Call records directory not found: {call_dir}")
        return False
    
    if not os.path.exists(order_file):
        print(f"❌ Order file not found: {order_file}")
        return False
    
    # Check if there are audio files (including .729 files)
    audio_files = [f for f in os.listdir(call_dir) if f.endswith(('.wav', '.mp3', '.729'))]
    if not audio_files:
        print(f"❌ No audio files found in: {call_dir}")
        return False
    
    print(f"✅ Found {len(audio_files)} audio files")
    return True

def main():
    """Main execution function."""
    print("🚀 DAILY TRADE SURVEILLANCE PROCESSOR")
    print("=" * 60)
    
    # Check command line arguments
    if len(sys.argv) != 2:
        print("❌ Usage: python run_daily_trade_surveillance.py <DATE>")
        print("📅 Example: python run_daily_trade_surveillance.py 07082025")
        print("📅 Date format: DDMMYYYY (e.g., 07082025 for August 7, 2025)")
        sys.exit(1)
    
    date_str = sys.argv[1]
    
    # Validate date format
    if not validate_date_format(date_str):
        print(f"❌ Invalid date format: {date_str}")
        print("📅 Expected format: DDMMYYYY (e.g., 07082025)")
        sys.exit(1)
    
    print(f"📅 Processing date: {date_str}")
    print(f"🕐 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check if data exists
    if not check_data_exists(date_str):
        print("❌ Required data not found. Exiting.")
        sys.exit(1)
    
    # Define the 10 steps (including file discovery, email processing, OMS, and classification)
    steps = [
        {
            "name": "File Discovery & Mapping",
            "script": "file_discovery_mapper.py",
            "is_file_discovery_step": True
        },
        {
            "name": "Email Processing",
            "script": "email_processing/process_emails_by_date.py",
            "is_email_step": True
        },
        {
            "name": "Audio File Processing",
            "script": "extract_call_info_august_daily.py"
        },
        {
            "name": "Audio-Order Validation & Mapping", 
            "script": "comprehensive_audio_trading_validation_august_daily.py"
        },
        {
            "name": "Audio Transcription",
            "script": "transcribe_calls_august_daily.py"
        },
        {
            "name": "AI Analysis",
            "script": "order_transcript_analysis_august_daily.py"
        },
        {
            "name": "Email-Order Validation & Mapping",
            "script": "email_order_validation_august_daily.py"
        },
        {
            "name": "OMS Surveillance",
            "script": "oms_surveillance/run_oms_surveillance.py",
            "is_oms_step": True
        },
        {
            "name": "Final Required Columns Mapping",
            "script": "add_required_columns_to_excel_august_daily.py"
        },
        {
            "name": "Discrepancy Classification",
            "script": "classify_discrepancies_august_daily.py"
        }
    ]
    
    # Track results
    results = []
    start_time = time.time()
    
    # Execute each step
    for i, step in enumerate(steps, 1):
        print(f"\n🎯 Step {i}/10: {step['name']}")
        
        # Check if this is the file discovery step
        if step.get('is_file_discovery_step', False):
            if not FILE_DISCOVERY_AVAILABLE:
                print(f"❌ File discovery not available. Skipping step.")
                results.append({
                    "step": step['name'],
                    "success": False,
                    "script": step['script']
                })
                continue
            
            # Run file discovery step
            success = run_file_discovery_step(date_str)
            results.append({
                "step": step['name'],
                "success": success,
                "script": step['script']
            })
            continue
        
        # Check if this is the email processing step
        elif step.get('is_email_step', False):
            if not EMAIL_PROCESSING_AVAILABLE:
                print(f"❌ Email processing not available. Skipping step.")
                results.append({
                    "step": step['name'],
                    "success": False,
                    "script": step['script']
                })
                continue
            
            # Check if email surveillance file already exists
            email_file = f'email_surveillance_{date_str}.json'
            if os.path.exists(email_file):
                print(f"✅ Email surveillance file already exists: {email_file}")
                print(f"⏭️  Skipping email processing step.")
                results.append({
                    "step": step['name'],
                    "success": True,
                    "script": step['script']
                })
                continue
            
            # Run email processing step
            success = run_email_processing_step(date_str)
            results.append({
                "step": step['name'],
                "success": success,
                "script": step['script']
            })
            
            if not success:
                print(f"\n❌ Step {i} failed. Stopping execution.")
                break
        
        # Check if this is the OMS surveillance step
        elif step.get('is_oms_step', False):
            # Check if OMS surveillance file already exists
            oms_file = f'oms_surveillance/oms_email_surveillance_{date_str}.json'
            if os.path.exists(oms_file):
                print(f"✅ OMS surveillance file already exists: {oms_file}")
                print(f"⏭️  Skipping OMS surveillance step.")
                results.append({
                    "step": step['name'],
                    "success": True,
                    "script": step['script']
                })
                continue
            
            # Convert DDMMYYYY to YYYY-MM-DD for OMS surveillance
            date_obj = datetime.strptime(date_str, '%d%m%Y')
            oms_date_str = date_obj.strftime('%Y-%m-%d')
            
            # Run OMS surveillance step with converted date
            script_path = step['script']
            if os.path.exists(script_path):
                success = run_step(step['name'], script_path, oms_date_str)
                results.append({
                    "step": step['name'],
                    "success": success,
                    "script": script_path
                })
                
                if not success:
                    print(f"\n❌ Step {i} failed. Stopping execution.")
                    break
            else:
                print(f"❌ Script not found: {script_path}")
                results.append({
                    "step": step['name'],
                    "success": False,
                    "script": script_path
                })
                break
        
        # Check if this is the discrepancy classification step
        elif step['name'] == 'Discrepancy Classification':
            # Check if classification has already been done
            month = int(date_str[2:4])
            month_names = {
                1: "January", 2: "February", 3: "March", 4: "April",
                5: "May", 6: "June", 7: "July", 8: "August",
                9: "September", 10: "October", 11: "November", 12: "December"
            }
            month_name = month_names.get(month, "August")
            excel_file = f"{month_name}/Daily_Reports/{date_str}/Final_Trade_Surveillance_Report_{date_str}_with_Email_and_Trade_Analysis.xlsx"
            
            if os.path.exists(excel_file):
                # Check if classification columns already exist
                try:
                    import pandas as pd
                    df = pd.read_excel(excel_file)
                    if 'discrepancy_type' in df.columns and 'discrepancy_confidence' in df.columns:
                        print(f"✅ Discrepancy classification already completed for {date_str}")
                        print(f"⏭️  Skipping classification step.")
                        results.append({
                            "step": step['name'],
                            "success": True,
                            "script": step['script']
                        })
                        continue
                except Exception as e:
                    print(f"⚠️  Could not check existing classification: {e}")
            
            # Run classification step
            script_path = step['script']
            if os.path.exists(script_path):
                success = run_step(step['name'], script_path, date_str)
                results.append({
                    "step": step['name'],
                    "success": success,
                    "script": script_path
                })
                
                if not success:
                    print(f"\n❌ Step {i} failed. Stopping execution.")
                    break
            else:
                print(f"❌ Script not found: {script_path}")
                results.append({
                    "step": step['name'],
                    "success": False,
                    "script": script_path
                })
                break
        else:
            # Regular step execution
            script_path = step['script']
            if os.path.exists(script_path):
                success = run_step(step['name'], script_path, date_str)
                results.append({
                    "step": step['name'],
                    "success": success,
                    "script": script_path
                })
                
                if not success:
                    print(f"\n❌ Step {i} failed. Stopping execution.")
                    break
            else:
                print(f"❌ Script not found: {script_path}")
                results.append({
                    "step": step['name'],
                    "success": False,
                    "script": script_path
                })
                break
    
    # Final summary
    end_time = time.time()
    total_duration = end_time - start_time
    
    print(f"\n{'='*60}")
    print("📊 EXECUTION SUMMARY")
    print(f"{'='*60}")
    print(f"📅 Date: {date_str}")
    print(f"🕐 Total Duration: {total_duration:.2f} seconds ({total_duration/60:.1f} minutes)")
    print(f"✅ Successful Steps: {sum(1 for r in results if r['success'])}/10")
    
    successful_steps = [r for r in results if r['success']]
    failed_steps = [r for r in results if not r['success']]
    
    if successful_steps:
        print("\n✅ Successful Steps:")
        for result in successful_steps:
            print(f"   ✓ {result['step']}")
    
    if failed_steps:
        print("\n❌ Failed Steps:")
        for result in failed_steps:
            print(f"   ✗ {result['step']}")
    
    # Check if final report was created
    month = int(date_str[2:4])
    month_names = {
        1: "January", 2: "February", 3: "March", 4: "April",
        5: "May", 6: "June", 7: "July", 8: "August",
        9: "September", 10: "October", 11: "November", 12: "December"
    }
    
    month_name = month_names.get(month, "August")  # Default to August if invalid month
    final_report_path = f"{month_name}/Daily_Reports/{date_str}/Final_Trade_Surveillance_Report_{date_str}_with_Email_and_Trade_Analysis.xlsx"
    if os.path.exists(final_report_path):
        print(f"\n🎉 FINAL REPORT CREATED!")
        print(f"📁 Location: {final_report_path}")
        print(f"📊 Check the Excel file for complete analysis results.")
    else:
        print(f"\n⚠️  Final report not found at: {final_report_path}")
    
    # Exit with appropriate code
    if all(r['success'] for r in results):
        print(f"\n🎉 All steps completed successfully!")
        sys.exit(0)
    else:
        print(f"\n❌ Some steps failed. Check the output above for details.")
        sys.exit(1)

if __name__ == "__main__":
    main() 