#!/usr/bin/env python3
"""
Script to upload surveillance data to S3
Uploads August, September, October, November, December folders to S3
"""

import os
import boto3
from pathlib import Path
from dotenv import load_dotenv
import sys

# Load environment variables
load_dotenv()

# S3 Configuration
S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME', 'icmemo-documents-prod')
S3_BASE_PREFIX = os.getenv('S3_BASE_PREFIX', 'trade_surveillance')
AWS_REGION = os.getenv('AWS_REGION', 'ap-south-1')
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')

# Base directory
BASE_DIR = Path(__file__).parent

# Months to upload
MONTHS = ['August', 'September', 'October', 'November', 'December']

def get_s3_client():
    """Initialize S3 client"""
    if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY:
        return boto3.client(
            's3',
            region_name=AWS_REGION,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY
        )
    else:
        return boto3.client('s3', region_name=AWS_REGION)

def upload_file_to_s3(s3_client, local_path, s3_key):
    """Upload a single file to S3"""
    try:
        s3_client.upload_file(str(local_path), S3_BUCKET_NAME, s3_key)
        return True
    except Exception as e:
        print(f"❌ Error uploading {local_path}: {e}")
        return False

def upload_directory_to_s3(s3_client, local_dir, s3_prefix, month_name):
    """Recursively upload directory to S3"""
    local_path = Path(local_dir)
    if not local_path.exists():
        print(f"⚠️  Directory not found: {local_dir}")
        return 0, 0
    
    uploaded = 0
    failed = 0
    
    # Walk through all files in directory
    for root, dirs, files in os.walk(local_path):
        for file in files:
            local_file = Path(root) / file
            # Calculate relative path from month directory
            relative_path = local_file.relative_to(local_path)
            # Construct S3 key
            s3_key = f"{S3_BASE_PREFIX}/{month_name}/{relative_path}".replace('\\', '/')
            
            # Upload file
            if upload_file_to_s3(s3_client, local_file, s3_key):
                uploaded += 1
                if uploaded % 100 == 0:
                    print(f"  ✅ Uploaded {uploaded} files...")
            else:
                failed += 1
    
    return uploaded, failed

def main():
    """Main upload function"""
    print("🚀 Starting S3 upload process...")
    print(f"📦 Bucket: {S3_BUCKET_NAME}")
    print(f"📁 Prefix: {S3_BASE_PREFIX}")
    print(f"🌍 Region: {AWS_REGION}")
    print()
    
    # Check credentials
    if not AWS_ACCESS_KEY_ID or not AWS_SECRET_ACCESS_KEY:
        print("⚠️  Warning: AWS credentials not found in environment variables")
        print("   Trying to use default credentials (IAM role, ~/.aws/credentials, etc.)")
        print()
    
    # Initialize S3 client
    try:
        s3_client = get_s3_client()
        # Test connection
        s3_client.head_bucket(Bucket=S3_BUCKET_NAME)
        print("✅ Successfully connected to S3")
        print()
    except Exception as e:
        print(f"❌ Failed to connect to S3: {e}")
        sys.exit(1)
    
    total_uploaded = 0
    total_failed = 0
    
    # Upload each month
    for month in MONTHS:
        month_dir = BASE_DIR / month
        if not month_dir.exists():
            print(f"⚠️  Skipping {month} - directory not found")
            continue
        
        print(f"📂 Uploading {month}...")
        uploaded, failed = upload_directory_to_s3(s3_client, month_dir, S3_BASE_PREFIX, month)
        total_uploaded += uploaded
        total_failed += failed
        print(f"   ✅ {uploaded} files uploaded, ❌ {failed} failed")
        print()
    
    # Summary
    print("=" * 60)
    print("📊 Upload Summary:")
    print(f"   ✅ Total uploaded: {total_uploaded}")
    print(f"   ❌ Total failed: {total_failed}")
    print("=" * 60)
    
    if total_failed == 0:
        print("🎉 All files uploaded successfully!")
    else:
        print(f"⚠️  {total_failed} files failed to upload. Please check the errors above.")

if __name__ == '__main__':
    main()



