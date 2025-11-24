import re
from datetime import datetime

filename = 'in-09374237422-423602-1754790849.88-20250818072409.wav'

print("=== TIMESTAMP EXTRACTION DEBUG ===")
print(f"Filename: {filename}")

# Current method (Unix timestamp)
timestamp_match = re.search(r'-(\d{10})\.\d+-\d{14}', filename)
if timestamp_match:
    unix_timestamp = int(timestamp_match.group(1))
    unix_date = datetime.fromtimestamp(unix_timestamp)
    print(f"Unix timestamp: {unix_timestamp}")
    print(f"Unix date: {unix_date}")

# Alternative method (date suffix)
date_suffix_match = re.search(r'-(\d{14})\.wav$', filename)
if date_suffix_match:
    date_suffix = date_suffix_match.group(1)
    suffix_date = datetime.strptime(date_suffix, '%Y%m%d%H%M%S')
    print(f"Date suffix: {date_suffix}")
    print(f"Suffix date: {suffix_date}")

print("\n=== CONCLUSION ===")
print("The script should use the date suffix (20250818072409) instead of the Unix timestamp")
print("This would give us August 18th instead of August 10th")
