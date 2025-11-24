#!/usr/bin/env python3
"""
Master OMS Surveillance Script
Orchestrates the complete OMS surveillance process from email fetching to Excel updates.
"""

import os
import sys
import json
import subprocess
import shutil
from datetime import datetime
from pathlib import Path
import logging

# Add the oms_surveillance directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fetch_oms_emails import OMSEmailFetcher
from oms_order_alert_processor import process_oms_emails_from_file
from oms_order_validation import OMSOrderValidator

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class OMSSurveillanceOrchestrator:
    """Orchestrates the complete OMS surveillance process."""
    
    def __init__(self):
        """Initialize the OMS surveillance orchestrator."""
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.temp_files = []
    
    def cleanup_temp_files(self):
        """Clean up temporary files created during processing."""
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    logger.info(f"🧹 Cleaned up temporary file: {temp_file}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to clean up {temp_file}: {e}")
        
        self.temp_files.clear()
    
    def step1_fetch_oms_emails(self, target_date: str) -> str:
        """
        Step 1: Fetch OMS emails from Microsoft Graph API.
        
        Args:
            target_date: Date in YYYY-MM-DD format
        
        Returns:
            Path to fetched emails file or None if failed
        """
        
        print("📧 Step 1: Fetching OMS emails from Microsoft Graph API...")
        print("-" * 60)
        
        try:
            fetcher = OMSEmailFetcher()
            output_file = fetcher.fetch_and_save_oms_emails(target_date)
            
            if output_file:
                # Make path absolute
                abs_path = os.path.abspath(output_file)
                self.temp_files.append(abs_path)
                print(f"✅ Step 1 completed: OMS emails processed and saved to {output_file}")
                return abs_path
            else:
                print("❌ Step 1 failed: OMS email processing failed")
                return None
                
        except Exception as e:
            logger.error(f"❌ Step 1 failed with error: {e}")
            return None
    
    def step2_parse_oms_emails(self, emails_file: str) -> str:
        """
        Step 2: Parse OMS emails using the OMS order alert processor.
        
        Args:
            emails_file: Path to the emails JSON file
        
        Returns:
            Path to parsed results file or None if failed
        """
        
        print("\n🔍 Step 2: Parsing OMS emails with order alert processor...")
        print("-" * 60)
        
        try:
            # Use the existing OMS order alert processor
            output_file = process_oms_emails_from_file(emails_file)
            
            if output_file:
                # Make path absolute
                abs_path = os.path.abspath(output_file)
                self.temp_files.append(abs_path)
                print(f"✅ Step 2 completed: OMS emails processed and saved to {output_file}")
                return abs_path
            else:
                print("❌ Step 2 failed: OMS email processing failed")
                return None
                
        except Exception as e:
            logger.error(f"❌ Step 2 failed with error: {e}")
            return None
    
    def step3_rename_parsed_results(self, parsed_file: str, target_date: str) -> str:
        """
        Step 3: Rename parsed results to standard format.
        
        Args:
            parsed_file: Path to the parsed results file
            target_date: Date in YYYY-MM-DD format
        
        Returns:
            Path to renamed file or None if failed
        """
        
        print("\n📝 Step 3: Renaming parsed results to standard format...")
        print("-" * 60)
        
        try:
            # STANDARDIZED FORMAT: Convert YYYY-MM-DD to DDMMYYYY format
            # This matches the format used throughout the surveillance system
            date_obj = datetime.strptime(target_date, '%Y-%m-%d')
            ddmmyyyy = date_obj.strftime('%d%m%Y')
            standard_name = f"oms_email_surveillance_{ddmmyyyy}.json"
            
            # CRITICAL: Save file in oms_surveillance directory (not root)
            # This is where step4_validate_oms_orders expects to find it
            oms_dir = os.path.dirname(os.path.abspath(__file__))
            standard_path = os.path.join(oms_dir, standard_name)
            
            # Copy to standard name in oms_surveillance directory
            shutil.copy2(parsed_file, standard_path)
            
            print(f"✅ Step 3 completed: Results renamed to {standard_name}")
            print(f"📁 File saved to: {standard_path}")
            return standard_path
            
        except Exception as e:
            logger.error(f"❌ Step 3 failed with error: {e}")
            return None
    
    def step4_validate_oms_orders(self, target_date: str) -> bool:
        """
        Step 4: Validate OMS orders and update Excel file.
        
        Args:
            target_date: Date in YYYY-MM-DD format
        
        Returns:
            True if successful, False otherwise
        """
        
        print("\n🎯 Step 4: Validating OMS orders and updating Excel file...")
        print("-" * 60)
        logger.info(f"🔍 [STEP4] Starting validation for date: {target_date}")
        
        try:
            # STANDARDIZED FORMAT: Convert YYYY-MM-DD to DDMMYYYY format
            # This matches the format used throughout the surveillance system
            date_obj = datetime.strptime(target_date, '%Y-%m-%d')
            ddmmyyyy = date_obj.strftime('%d%m%Y')
            logger.info(f"🔍 [STEP4] Converted date {target_date} to {ddmmyyyy}")
            
            print(f"🔍 [STEP4] Initializing OMS Order Validator...")
            logger.info(f"🔍 [STEP4] Initializing OMS Order Validator...")
            validator = OMSOrderValidator()
            
            print(f"🔍 [STEP4] Calling validate_oms_orders({ddmmyyyy})...")
            logger.info(f"🔍 [STEP4] Calling validate_oms_orders({ddmmyyyy})...")
            success = validator.validate_oms_orders(ddmmyyyy)
            
            logger.info(f"🔍 [STEP4] validate_oms_orders returned: {success}")
            
            if success:
                print("✅ Step 4 completed: OMS orders validated and Excel file updated")
                logger.info(f"✅ [STEP4] Validation completed successfully for {target_date}")
                
                # VERIFICATION: Check if matches were actually applied
                import os
                import pandas as pd
                month_num = date_obj.month
                month_names = {
                    1: "January", 2: "February", 3: "March", 4: "April",
                    5: "May", 6: "June", 7: "July", 8: "August",
                    9: "September", 10: "October", 11: "November", 12: "December"
                }
                month_name = month_names.get(month_num)
                excel_file = os.path.join(
                    os.path.dirname(os.path.dirname(__file__)),
                    month_name,
                    "Daily_Reports",
                    ddmmyyyy,
                    f"Final_Trade_Surveillance_Report_{ddmmyyyy}_with_Email_and_Trade_Analysis.xlsx"
                )
                
                if os.path.exists(excel_file):
                    try:
                        df = pd.read_excel(excel_file)
                        oms_matched = df[df['Email-Order Match Status'] == 'OMS_MATCH']
                        match_count = len(oms_matched)
                        logger.info(f"🔍 [STEP4] Verification: Found {match_count} OMS matches in Excel")
                        print(f"🔍 [STEP4] Verification: Found {match_count} OMS matches in Excel")
                        
                        if match_count == 0:
                            logger.warning(f"⚠️ [STEP4] WARNING: Validation returned success but no OMS matches found in Excel!")
                            print(f"⚠️ [STEP4] WARNING: Validation returned success but no OMS matches found in Excel!")
                    except Exception as verify_error:
                        logger.error(f"❌ [STEP4] Error during verification: {verify_error}")
                        print(f"❌ [STEP4] Error during verification: {verify_error}")
                else:
                    logger.warning(f"⚠️ [STEP4] Excel file not found for verification: {excel_file}")
                    print(f"⚠️ [STEP4] Excel file not found for verification: {excel_file}")
                
                return True
            else:
                print("❌ Step 4 failed: OMS order validation failed")
                logger.error(f"❌ [STEP4] Validation failed for {target_date}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Step 4 failed with error: {e}")
            import traceback
            logger.error(f"❌ [STEP4] Traceback: {traceback.format_exc()}")
            print(f"❌ [STEP4] Exception: {e}")
            print(f"❌ [STEP4] Traceback: {traceback.format_exc()}")
            return False
    
    def run_complete_oms_surveillance(self, target_date: str) -> bool:
        """
        Run the complete OMS surveillance process.
        
        Args:
            target_date: Date in YYYY-MM-DD format
        
        Returns:
            True if successful, False otherwise
        """
        
        print("🚀 OMS Surveillance System - Complete Process")
        print("=" * 70)
        print(f"📅 Target Date: {target_date}")
        print(f"🕐 Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)
        
        try:
            # Step 1: Fetch OMS emails
            emails_file = self.step1_fetch_oms_emails(target_date)
            if not emails_file:
                print("\n❌ OMS Surveillance failed at Step 1: Email fetching")
                return False
            
            # Step 2: Parse OMS emails
            parsed_file = self.step2_parse_oms_emails(emails_file)
            if not parsed_file:
                print("\n❌ OMS Surveillance failed at Step 2: Email parsing")
                return False
            
            # Step 3: Rename to standard format
            standard_file = self.step3_rename_parsed_results(parsed_file, target_date)
            if not standard_file:
                print("\n❌ OMS Surveillance failed at Step 3: File renaming")
                return False
            
            # Step 4: Validate orders and update Excel
            validation_success = self.step4_validate_oms_orders(target_date)
            if not validation_success:
                print("\n❌ OMS Surveillance failed at Step 4: Order validation")
                return False
            
            # Success!
            print("\n" + "=" * 70)
            print("✅ OMS SURVEILLANCE COMPLETED SUCCESSFULLY!")
            print("=" * 70)
            print(f"📅 Date Processed: {target_date}")
            print(f"🕐 End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"📁 Final Results: {standard_file}")
            print("=" * 70)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ OMS Surveillance failed with unexpected error: {e}")
            return False
        
        finally:
            # Always clean up temporary files
            self.cleanup_temp_files()
    
    def run_batch_oms_surveillance(self, date_list: list) -> dict:
        """
        Run OMS surveillance for multiple dates.
        
        Args:
            date_list: List of dates in YYYY-MM-DD format
        
        Returns:
            Dictionary with results for each date
        """
        
        print("🚀 OMS Surveillance System - Batch Processing")
        print("=" * 70)
        print(f"📅 Dates to Process: {len(date_list)}")
        print(f"🕐 Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)
        
        results = {}
        
        for i, target_date in enumerate(date_list, 1):
            print(f"\n📅 Processing Date {i}/{len(date_list)}: {target_date}")
            print("-" * 50)
            
            success = self.run_complete_oms_surveillance(target_date)
            results[target_date] = success
            
            if success:
                print(f"✅ Date {target_date} completed successfully")
            else:
                print(f"❌ Date {target_date} failed")
        
        # Summary
        successful_dates = [date for date, success in results.items() if success]
        failed_dates = [date for date, success in results.items() if not success]
        
        print("\n" + "=" * 70)
        print("📊 BATCH PROCESSING SUMMARY")
        print("=" * 70)
        print(f"✅ Successful: {len(successful_dates)} dates")
        print(f"❌ Failed: {len(failed_dates)} dates")
        
        if successful_dates:
            print(f"✅ Successful dates: {', '.join(successful_dates)}")
        
        if failed_dates:
            print(f"❌ Failed dates: {', '.join(failed_dates)}")
        
        print("=" * 70)
        
        return results

def main():
    """Main function for OMS surveillance."""
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Single date: python run_oms_surveillance.py YYYY-MM-DD")
        print("  Multiple dates: python run_oms_surveillance.py YYYY-MM-DD YYYY-MM-DD ...")
        print("")
        print("Examples:")
        print("  python run_oms_surveillance.py 2025-09-02")
        print("  python run_oms_surveillance.py 2025-09-01 2025-09-02 2025-09-03")
        sys.exit(1)
    
    # Parse command line arguments
    dates = sys.argv[1:]
    
    # Validate date formats
    valid_dates = []
    for date_str in dates:
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            valid_dates.append(date_str)
        except ValueError:
            print(f"❌ Invalid date format: {date_str}. Use YYYY-MM-DD format.")
            sys.exit(1)
    
    # Initialize orchestrator
    orchestrator = OMSSurveillanceOrchestrator()
    
    try:
        if len(valid_dates) == 1:
            # Single date processing
            success = orchestrator.run_complete_oms_surveillance(valid_dates[0])
            sys.exit(0 if success else 1)
        else:
            # Batch processing
            results = orchestrator.run_batch_oms_surveillance(valid_dates)
            all_successful = all(results.values())
            sys.exit(0 if all_successful else 1)
            
    except KeyboardInterrupt:
        print("\n⚠️ Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
