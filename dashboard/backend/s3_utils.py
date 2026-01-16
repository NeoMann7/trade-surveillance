#!/usr/bin/env python3
"""
S3 utility functions for reading surveillance data from AWS S3
"""

import os
import json
import tempfile
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
import pandas as pd
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# S3 Configuration from environment variables
S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME', 'icmemo-documents-prod')
S3_BASE_PREFIX = os.getenv('S3_BASE_PREFIX', 'trade_surveillance')
AWS_REGION = os.getenv('AWS_REGION', 'ap-south-1')
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')

# Initialize S3 client
_s3_client = None

def get_s3_client():
    """Get or create S3 client"""
    global _s3_client
    if _s3_client is None:
        try:
            if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY:
                _s3_client = boto3.client(
                    's3',
                    region_name=AWS_REGION,
                    aws_access_key_id=AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=AWS_SECRET_ACCESS_KEY
                )
            else:
                # Try to use default credentials (IAM role, ~/.aws/credentials, etc.)
                _s3_client = boto3.client('s3', region_name=AWS_REGION)
            logger.info(f"S3 client initialized for bucket: {S3_BUCKET_NAME}")
        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {e}")
            raise
    return _s3_client

def get_s3_key(local_path, base_path=None):
    """
    Convert local file path to S3 key
    Example: 
    - local: /Users/.../trade_surveillance_prod/August/Daily_Reports/...
    - S3 key: trade_surveillance/August/Daily_Reports/...
    """
    if base_path:
        # Remove base_path prefix
        relative_path = os.path.relpath(local_path, base_path)
    else:
        # Extract path after 'trade_surveillance_prod' or similar
        parts = local_path.split(os.sep)
        try:
            idx = next(i for i, part in enumerate(parts) if 'trade_surveillance' in part.lower() or part in ['August', 'September', 'October', 'November', 'December'])
            relative_path = os.path.join(*parts[idx:])
        except StopIteration:
            # Fallback: use last few parts
            relative_path = os.path.join(*parts[-3:])
    
    # Normalize path separators for S3 (use forward slashes)
    s3_key = relative_path.replace(os.sep, '/')
    
    # Prepend base prefix if not already present
    if not s3_key.startswith(S3_BASE_PREFIX):
        s3_key = f"{S3_BASE_PREFIX}/{s3_key}"
    
    return s3_key

def s3_file_exists(s3_key):
    """Check if file exists in S3"""
    try:
        s3_client = get_s3_client()
        s3_client.head_object(Bucket=S3_BUCKET_NAME, Key=s3_key)
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            return False
        logger.error(f"Error checking S3 file existence for {s3_key}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error checking S3 file: {e}")
        return False

def download_file_from_s3(s3_key, local_path=None):
    """
    Download file from S3 to local temporary file or specified path
    Returns path to downloaded file
    """
    try:
        s3_client = get_s3_client()
        
        if local_path is None:
            # Create temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(s3_key)[1])
            local_path = temp_file.name
            temp_file.close()
        
        s3_client.download_file(S3_BUCKET_NAME, s3_key, local_path)
        logger.debug(f"Downloaded {s3_key} to {local_path}")
        return local_path
    except ClientError as e:
        logger.error(f"Error downloading {s3_key} from S3: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error downloading from S3: {e}")
        raise

def read_excel_from_s3(s3_key):
    """
    Read Excel file from S3 and return pandas DataFrame
    Downloads to temp file, reads, then deletes temp file
    """
    temp_file = None
    try:
        temp_file = download_file_from_s3(s3_key)
        df = pd.read_excel(temp_file)
        return df
    except Exception as e:
        logger.error(f"Error reading Excel from S3 {s3_key}: {e}")
        raise
    finally:
        if temp_file and os.path.exists(temp_file):
            try:
                os.unlink(temp_file)
            except Exception as e:
                logger.warning(f"Failed to delete temp file {temp_file}: {e}")

def read_csv_from_s3(s3_key):
    """
    Read CSV file from S3 and return pandas DataFrame
    Downloads to temp file, reads, then deletes temp file
    """
    temp_file = None
    try:
        temp_file = download_file_from_s3(s3_key)
        df = pd.read_csv(temp_file)
        return df
    except Exception as e:
        logger.error(f"Error reading CSV from S3 {s3_key}: {e}")
        raise
    finally:
        if temp_file and os.path.exists(temp_file):
            try:
                os.unlink(temp_file)
            except Exception as e:
                logger.warning(f"Failed to delete temp file {temp_file}: {e}")

def read_json_from_s3(s3_key):
    """
    Read JSON file from S3 and return parsed JSON object
    Downloads to temp file, reads, then deletes temp file
    """
    temp_file = None
    try:
        temp_file = download_file_from_s3(s3_key)
        with open(temp_file, 'r') as f:
            data = json.load(f)
        return data
    except Exception as e:
        logger.error(f"Error reading JSON from S3 {s3_key}: {e}")
        raise
    finally:
        if temp_file and os.path.exists(temp_file):
            try:
                os.unlink(temp_file)
            except Exception as e:
                logger.warning(f"Failed to delete temp file {temp_file}: {e}")

def read_text_from_s3(s3_key):
    """
    Read text file from S3 and return content as string
    Downloads to temp file, reads, then deletes temp file
    """
    temp_file = None
    try:
        temp_file = download_file_from_s3(s3_key)
        with open(temp_file, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except Exception as e:
        logger.error(f"Error reading text from S3 {s3_key}: {e}")
        raise
    finally:
        if temp_file and os.path.exists(temp_file):
            try:
                os.unlink(temp_file)
            except Exception as e:
                logger.warning(f"Failed to delete temp file {temp_file}: {e}")

def list_s3_objects(prefix, max_keys=1000):
    """
    List all objects in S3 with given prefix
    Returns list of object keys
    """
    try:
        s3_client = get_s3_client()
        objects = []
        paginator = s3_client.get_paginator('list_objects_v2')
        
        for page in paginator.paginate(Bucket=S3_BUCKET_NAME, Prefix=prefix, MaxKeys=max_keys):
            if 'Contents' in page:
                for obj in page['Contents']:
                    objects.append(obj['Key'])
        
        return objects
    except Exception as e:
        logger.error(f"Error listing S3 objects with prefix {prefix}: {e}")
        return []

def list_s3_directories(prefix):
    """
    List all "directories" (common prefixes) in S3 with given prefix
    Returns list of directory names (without trailing slash)
    """
    try:
        s3_client = get_s3_client()
        directories = []
        paginator = s3_client.get_paginator('list_objects_v2')
        
        for page in paginator.paginate(Bucket=S3_BUCKET_NAME, Prefix=prefix, Delimiter='/'):
            if 'CommonPrefixes' in page:
                for prefix_obj in page['CommonPrefixes']:
                    # Remove trailing slash and base prefix
                    dir_name = prefix_obj['Prefix'].rstrip('/')
                    if dir_name.startswith(S3_BASE_PREFIX + '/'):
                        dir_name = dir_name[len(S3_BASE_PREFIX) + 1:]
                    directories.append(dir_name)
        
        return directories
    except Exception as e:
        logger.error(f"Error listing S3 directories with prefix {prefix}: {e}")
        return []

def upload_file_to_s3(local_path, s3_key):
    """
    Upload local file to S3
    """
    try:
        s3_client = get_s3_client()
        s3_client.upload_file(local_path, S3_BUCKET_NAME, s3_key)
        logger.info(f"Uploaded {local_path} to s3://{S3_BUCKET_NAME}/{s3_key}")
        return True
    except Exception as e:
        logger.error(f"Error uploading {local_path} to S3: {e}")
        raise

def generate_presigned_post_url(s3_key, expiration=3600, content_type=None, max_size_mb=100):
    """
    Generate a pre-signed POST URL for direct S3 upload from browser
    
    Args:
        s3_key: S3 object key where file will be uploaded
        expiration: URL expiration time in seconds (default 1 hour)
        content_type: Optional content type restriction
        max_size_mb: Maximum file size in MB
    
    Returns:
        dict with 'url' and 'fields' for POST request
    """
    try:
        s3_client = get_s3_client()
        
        # Prepare conditions for POST policy
        conditions = []
        fields = {}
        
        if content_type:
            # For exact content type match, use 'eq' condition
            conditions.append(['eq', '$Content-Type', content_type])
            fields['Content-Type'] = content_type
        
        # Add file size limit
        conditions.append(['content-length-range', 0, max_size_mb * 1024 * 1024])
        
        # Generate pre-signed POST URL
        presigned_post = s3_client.generate_presigned_post(
            Bucket=S3_BUCKET_NAME,
            Key=s3_key,
            Fields=fields,
            Conditions=conditions,
            ExpiresIn=expiration
        )
        
        logger.info(f"Generated pre-signed POST URL for s3://{S3_BUCKET_NAME}/{s3_key}")
        return presigned_post
    except Exception as e:
        logger.error(f"Error generating pre-signed POST URL for {s3_key}: {e}")
        raise



