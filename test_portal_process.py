#!/usr/bin/env python3
"""
Test script to simulate portal surveillance process and compare results
"""
import os
import sys
import json
import pandas as pd
from datetime import datetime

# Set gpt-4.1 as model (like portal does)
os.environ['EMAIL_MODEL'] = 'gpt-4.1'

date_str = '01092025'  # Sep-01
formatted_date = '2025-09-01'

print("=== TESTING PORTAL PROCESS FOR Sep-01 ===\n")
print("1. Running email processing (like portal would)...")

# Import and run email processing (same as portal)
from email_processing.process_emails_by_date import process_emails_for_date
success = process_emails_for_date(formatted_date)

if not success:
    print("❌ Email processing failed!")
    sys.exit(1)

print("✅ Email processing completed")

# Handle file naming
yyyymmdd = formatted_date.replace("-", "")
old_file = f'email_surveillance_{yyyymmdd}_gpt-4.1.json'
new_file = f'email_surveillance_{date_str}.json'

if os.path.exists(old_file):
    import shutil
    shutil.copy2(old_file, new_file)
    print(f"✅ Copied {old_file} to {new_file}")

print("\n2. Running email-order validation (like portal would)...")
os.system(f"python email_order_validation_august_daily.py {date_str}")

print("\n3. Comparing results...")
print("=" * 60)

# Compare JSON files
portal_json = f'email_surveillance_{date_str}.json'
backup_json = 'test_backup/01092025/email_surveillance_01092025.json'

if os.path.exists(portal_json) and os.path.exists(backup_json):
    with open(portal_json) as f:
        portal_data = json.load(f)
    with open(backup_json) as f:
        backup_data = json.load(f)
    
    portal_orders = 0
    backup_orders = 0
    
    for e in portal_data.get('all_results', []):
        det = e.get('ai_analysis', {}).get('ai_order_details', [])
        if isinstance(det, list):
            portal_orders += len(det)
        elif isinstance(det, dict):
            portal_orders += 1
    
    for e in backup_data.get('all_results', []):
        det = e.get('ai_analysis', {}).get('ai_order_details', [])
        if isinstance(det, list):
            backup_orders += len(det)
        elif isinstance(det, dict):
            backup_orders += 1
    
    print(f"JSON Orders Extracted:")
    print(f"  Portal run: {portal_orders}")
    print(f"  Backup: {backup_orders}")
    print(f"  Match: {'✅ YES' if portal_orders == backup_orders else '❌ NO'}")

# Compare Excel files
portal_excel = f'September/Daily_Reports/{date_str}/Final_Trade_Surveillance_Report_{date_str}_with_Email_and_Trade_Analysis.xlsx'
backup_excel = 'test_backup/01092025/Final_Trade_Surveillance_Report_01092025_with_Email_and_Trade_Analysis.xlsx'

if os.path.exists(portal_excel) and os.path.exists(backup_excel):
    portal_df = pd.read_excel(portal_excel)
    backup_df = pd.read_excel(backup_excel)
    
    portal_matched = len(portal_df[portal_df['Email-Order Match Status'] == 'Matched']) if 'Email-Order Match Status' in portal_df.columns else 0
    backup_matched = len(backup_df[backup_df['Email-Order Match Status'] == 'Matched']) if 'Email-Order Match Status' in backup_df.columns else 0
    
    portal_total = len(portal_df)
    backup_total = len(backup_df)
    
    print(f"\nExcel Match Results:")
    print(f"  Portal run: {portal_matched} matched / {portal_total} total")
    print(f"  Backup: {backup_matched} matched / {backup_total} total")
    print(f"  Match: {'✅ YES' if portal_matched == backup_matched and portal_total == backup_total else '❌ NO'}")
    
    if portal_matched != backup_matched or portal_total != backup_total:
        print(f"\n⚠️  Differences found!")
        print(f"   Matched diff: {portal_matched - backup_matched:+d}")
        print(f"   Total diff: {portal_total - backup_total:+d}")

print("\n" + "=" * 60)
print("✅ Portal process test complete!")

