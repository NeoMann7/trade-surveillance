import os
import re
import glob
import pandas as pd
import wave
from datetime import datetime, timedelta

# Paths
CALL_RECORDS_DIR = os.path.join("July", "Call Records")
UCC_PATH = os.path.join("July", "UCC Database.xlsx")
OUTPUT_PATH = os.path.join("July", "call_info_output.xlsx")

# Load UCC database
ucc_df = pd.read_excel(UCC_PATH, dtype=str)
ucc_numbers = set(ucc_df['MOBILE'].astype(str).str.replace(r'\D', '', regex=True))

def extract_mobile(filename):
    # Look for patterns like 09..., 009..., 093..., 602-009..., 616-009...
    match = re.search(r'(?:^|[-_])0{1,2}(\d{10})', filename)
    if match:
        return match.group(1)
    # fallback: look for any 10+ digit number
    match = re.search(r'(\d{10,12})', filename)
    if match:
        return match.group(1)[-10:]
    return None

def extract_datetime(filename):
    # Last field is like 20250603094559, may be followed by (1), (2), etc.
    match = re.search(r'(\d{14})(?=\.wav$| \([\d]+\)\.wav$)', filename)
    if not match:
        return None, None, None  # Always return three values
    dt_str = match.group(1)
    dt = datetime.strptime(dt_str, "%Y%m%d%H%M%S")
    date = dt.strftime("%Y-%m-%d")
    time = dt.strftime("%H:%M:%S")
    return date, time, dt

def get_duration(filepath):
    try:
        with wave.open(filepath, 'rb') as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            duration = frames / float(rate)
            return int(duration)
    except Exception:
        return None

def process_files():
    results = []
    for folder in glob.glob(os.path.join(CALL_RECORDS_DIR, "Call_*")):
        for wavfile in glob.glob(os.path.join(folder, "*.wav")):
            fname = os.path.basename(wavfile)
            mobile = extract_mobile(fname)
            date, time, dt = extract_datetime(fname)
            duration = get_duration(wavfile)
            end_dt = dt + timedelta(seconds=duration) if dt and duration else None
            present_in_ucc = (
                (mobile in ucc_numbers) if mobile else False
            )
            results.append({
                'filename': fname,
                'mobile_number': mobile,
                'present_in_ucc': 'Yes' if present_in_ucc else 'No',
                'call_start': f"{date} {time}" if date and time else '',
                'call_end': end_dt.strftime("%Y-%m-%d %H:%M:%S") if end_dt else '',
                'duration_seconds': duration if duration is not None else '',
            })
    return results

def main():
    rows = process_files()
    df = pd.DataFrame(rows)
    df.to_excel(OUTPUT_PATH, index=False)
    print(f"Output written to {OUTPUT_PATH}")

if __name__ == "__main__":
    main() 