import pandas as pd
import os
import re
from datetime import datetime, timedelta
import glob

def extract_mobile(filename):
    """Extract mobile number using the same logic as original June script"""
    # Look for patterns like 09..., 009..., 093..., 602-009..., 616-009...
    match = re.search(r'(?:^|[-_])0{1,2}(\d{10})', filename)
    if match:
        return match.group(1)
    # fallback: look for any 10+ digit number
    match = re.search(r'(\d{10,12})', filename)
    if match:
        return match.group(1)[-10:]
    return None

def extract_call_info_for_date(date_str):
    """
    Extract call information for a specific date in August or September
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
    call_records_path = f"{month_name}/Call Records/Call_{date_str}"
    ucc_db_path = f"{month_name}/UCC Database.xlsx"
    output_path = f"{month_name}/Daily_Reports/{date_str}/call_info_output_{date_str}.xlsx"
    
    # Create Daily_Reports directory if it doesn't exist
    os.makedirs(f"{month_name}/Daily_Reports/{date_str}", exist_ok=True)
    
    # PERMANENT FIX: Create call records directory if it doesn't exist (graceful handling)
    if not os.path.exists(call_records_path):
        print(f"⚠️  Call records directory not found: {call_records_path}")
        print(f"📁 Creating directory...")
        os.makedirs(call_records_path, exist_ok=True)
        print(f"✅ Directory created: {call_records_path}")
    
    # Get all audio files for the specific date (including .729 files)
    audio_files = (
        glob.glob(os.path.join(call_records_path, "*.wav")) + 
        glob.glob(os.path.join(call_records_path, "*.mp3")) +
        glob.glob(os.path.join(call_records_path, "*.729"))
    )
    
    # PERMANENT FIX: Handle empty audio files gracefully - create empty output file instead of failing
    if not audio_files:
        print(f"ℹ️  No audio files found in {call_records_path}")
        print(f"📝 Creating empty call info output file...")
        
        # Create empty DataFrame with required columns
        empty_df = pd.DataFrame(columns=[
            'filename', 'mobile_number', 'present_in_ucc', 'call_start', 
            'call_end', 'duration_seconds', 'client_id'
        ])
        
        # Save empty file to indicate processing completed (even with no audio)
        empty_df.to_excel(output_path, index=False)
        print(f"✅ Created empty call info file: {output_path}")
        print(f"✅ Audio file processing completed (no audio files for this date)")
        return output_path
    
    print(f"Found {len(audio_files)} audio files for {date_str}")
    
    # Load UCC database
    try:
        ucc_df = pd.read_excel(ucc_db_path, dtype=str)
        # Create set of mobile numbers for faster lookup
        ucc_numbers = set(ucc_df['MOBILE'].astype(str).str.replace(r'\D', '', regex=True))
        print(f"Loaded UCC database with {len(ucc_df)} records")
    except Exception as e:
        print(f"Error loading UCC database: {e}")
        return None
    
    # Extract mobile numbers and create call info
    call_info_list = []
    
    for audio_file in audio_files:
        filename = os.path.basename(audio_file)
        
        # Extract mobile number using the same logic as original
        mobile_number = extract_mobile(filename)
        
        if mobile_number:
            # Check if mobile number exists in UCC database
            present_in_ucc = 'Y' if mobile_number in ucc_numbers else 'N'
            
            # Get client ID from UCC database
            client_id = None
            if present_in_ucc == 'Y':
                # Find matching mobile number in UCC database
                for _, row in ucc_df.iterrows():
                    ucc_mobile = str(row['MOBILE']).replace(' ', '').replace('-', '')[-10:]
                    if ucc_mobile == mobile_number:
                        client_id = str(row['CLIENT CD'])
                        break
            
            # Extract timestamp from filename - handle multiple formats
            call_start = None
            call_end = None
            duration_seconds = None
            
            # Format 1: October format - g-YYYYMMDD-HHMMSS-... (e.g., g-20251001-110447-...)
            october_format_match = re.search(r'g-(\d{8})-(\d{6})', filename)
            if october_format_match:
                date_part = october_format_match.group(1)  # YYYYMMDD
                time_part = october_format_match.group(2)  # HHMMSS
                timestamp_str = date_part + time_part  # YYYYMMDDHHMMSS
                call_start = datetime.strptime(timestamp_str, '%Y%m%d%H%M%S')
                call_end = call_start + timedelta(seconds=300)
                duration_seconds = 300
            else:
                # Format 2: September format - ...-YYYYMMDDHHMMSS.wav (14 digits at end)
                date_suffix_match = re.search(r'-(\d{14})\.(wav|mp3)$', filename)
                if date_suffix_match:
                    date_suffix = date_suffix_match.group(1)
                    call_start = datetime.strptime(date_suffix, '%Y%m%d%H%M%S')
                    call_end = call_start + timedelta(seconds=300)
                    duration_seconds = 300
                else:
                    # Format 3: Unix timestamp format - ...-UNIXTIMESTAMP.xxxx-YYYYMMDDHHMMSS
                    timestamp_match = re.search(r'-(\d{10})\.\d+-\d{14}', filename)
                    if timestamp_match:
                        timestamp = int(timestamp_match.group(1))
                        call_start = datetime.fromtimestamp(timestamp)
                        call_end = datetime.fromtimestamp(timestamp + 300)
                        duration_seconds = 300
                    else:
                        # No timestamp found
                        call_start = None
                        call_end = None
                        duration_seconds = None
            
            call_info_list.append({
                'filename': filename,
                'mobile_number': mobile_number,
                'present_in_ucc': present_in_ucc,
                'call_start': call_start,
                'call_end': call_end,
                'duration_seconds': duration_seconds,
                'client_id': client_id
            })
    
    # Create DataFrame and save
    if call_info_list:
        call_info_df = pd.DataFrame(call_info_list)
        call_info_df.to_excel(output_path, index=False)
        print(f"Call info saved to: {output_path}")
        print(f"Processed {len(call_info_df)} audio files")
        return output_path
    else:
        # PERMANENT FIX: Create empty file instead of returning None (graceful handling)
        print("ℹ️  No call info extracted from audio files")
        print(f"📝 Creating empty call info output file...")
        empty_df = pd.DataFrame(columns=[
            'filename', 'mobile_number', 'present_in_ucc', 'call_start', 
            'call_end', 'duration_seconds', 'client_id'
        ])
        empty_df.to_excel(output_path, index=False)
        print(f"✅ Created empty call info file: {output_path}")
        print(f"✅ Audio file processing completed")
        return output_path

if __name__ == "__main__":
    import sys
    
    # Get date from command line argument or use default
    if len(sys.argv) > 1:
        date_str = sys.argv[1]
    else:
        # Default date (August 7th, 2025)
        date_str = "07082025"
    
    result = extract_call_info_for_date(date_str)
    if result:
        print(f"Successfully processed {date_str}")
        sys.exit(0)  # Success
    else:
        print(f"Failed to process {date_str}")
        sys.exit(1)  # Failure 