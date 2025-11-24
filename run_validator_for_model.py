#!/usr/bin/env python3
"""
Run email-order validator for a specific model's results.
This allows comparing match results between o3 and gpt-4.1.
"""
import os
import sys
import subprocess
import shutil
from datetime import datetime


def run_validator_for_model(date_str: str, model: str):
    """
    Run validator for a specific model.
    
    Args:
        date_str: Date in DDMMYYYY format (e.g., "01092025")
        model: Model name ("o3" or "gpt-4.1")
    """
    # Convert DDMMYYYY to YYYYMMDD for JSON filename
    date_obj = datetime.strptime(date_str, '%d%m%Y')
    yyyymmdd = date_obj.strftime('%Y%m%d')
    
    # Model-specific JSON file
    model_json = f"email_surveillance_{yyyymmdd}_{model}.json"
    standard_json = f"email_surveillance_{date_str}.json"
    
    if not os.path.exists(model_json):
        print(f"❌ Model JSON file not found: {model_json}")
        return False
    
    # Backup existing standard JSON if it exists
    backup_json = None
    if os.path.exists(standard_json):
        backup_json = f"{standard_json}.backup"
        shutil.copy2(standard_json, backup_json)
    
    # Copy model-specific JSON to standard location for validator
    shutil.copy2(model_json, standard_json)
    
    try:
        # Run validator (it will use the standard JSON filename)
        print(f"📊 Running validator for {model} on {date_str}...")
        result = subprocess.run(
            [sys.executable, "email_order_validation_august_daily.py", date_str],
            capture_output=False,
            text=True
        )
        
        if result.returncode == 0:
            # Move Excel output to model-specific directory
            excel_source = f"September/Daily_Reports/{date_str}/Final_Trade_Surveillance_Report_{date_str}_with_Email_and_Trade_Analysis.xlsx"
            excel_dest_dir = f"September/Daily_Reports_{model}/{date_str}/"
            mapping_json_source = f"September/Daily_Reports/{date_str}/email_order_mapping_{date_str}.json"
            
            if os.path.exists(excel_source):
                os.makedirs(excel_dest_dir, exist_ok=True)
                excel_dest = f"{excel_dest_dir}Final_Trade_Surveillance_Report_{date_str}_with_Email_and_Trade_Analysis.xlsx"
                shutil.copy2(excel_source, excel_dest)
                print(f"✅ Saved Excel to: {excel_dest}")
            
            if os.path.exists(mapping_json_source):
                os.makedirs(excel_dest_dir, exist_ok=True)
                mapping_dest = f"{excel_dest_dir}email_order_mapping_{date_str}.json"
                shutil.copy2(mapping_json_source, mapping_dest)
                print(f"✅ Saved mapping JSON to: {mapping_dest}")
            
            return True
        else:
            print(f"❌ Validator failed with exit code {result.returncode}")
            return False
            
    finally:
        # Restore original JSON file
        if backup_json and os.path.exists(backup_json):
            shutil.move(backup_json, standard_json)
        elif os.path.exists(standard_json):
            # If no backup, just remove the temporary copy
            os.remove(standard_json)


def main():
    if len(sys.argv) != 3:
        print("Usage: python run_validator_for_model.py <DDMMYYYY> <model>")
        print("Example: python run_validator_for_model.py 01092025 o3")
        sys.exit(1)
    
    date_str = sys.argv[1]
    model = sys.argv[2]
    
    if model not in ['o3', 'gpt-4.1']:
        print(f"❌ Invalid model: {model}. Must be 'o3' or 'gpt-4.1'")
        sys.exit(1)
    
    success = run_validator_for_model(date_str, model)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()

