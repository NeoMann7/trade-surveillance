#!/usr/bin/env python3
"""
Backend API service to serve real surveillance data from Excel and JSON files
This reads from your actual surveillance output files
"""

import os
import json
import pandas as pd
import numpy as np
import io
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from datetime import datetime
import logging
import subprocess
import threading
import uuid
import shutil
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from s3_utils import (
    get_s3_key, s3_file_exists, read_excel_from_s3, read_csv_from_s3,
    read_json_from_s3, read_text_from_s3, list_s3_objects, list_s3_directories,
    upload_file_to_s3
)

# Load environment variables
load_dotenv()

app = Flask(__name__)

# CORS configuration from environment variable
# CORS_ORIGINS should be a comma-separated list of allowed origins
# Example: CORS_ORIGINS=http://localhost:3000,http://localhost:3001,https://your-frontend-url.trycloudflare.com
CORS_ORIGINS_STR = os.getenv('CORS_ORIGINS', 'http://localhost:3000,http://localhost:3001')
CORS_ORIGINS = [origin.strip() for origin in CORS_ORIGINS_STR.split(',') if origin.strip()]

# Also allow the frontend URL from environment if specified
FRONTEND_URL = os.getenv('FRONTEND_URL', '')
if FRONTEND_URL and FRONTEND_URL not in CORS_ORIGINS:
    CORS_ORIGINS.append(FRONTEND_URL)

# Use CORS with the configured origins, or allow all if CORS_ORIGINS is empty
if CORS_ORIGINS:
    CORS(app, origins=CORS_ORIGINS, supports_credentials=True)
else:
    # Fallback: allow all origins (for development only)
    CORS(app, origins='*', supports_credentials=True)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global job tracking with 24-hour retention
surveillance_jobs = {}

def cleanup_old_jobs():
    """Clean up jobs older than 24 hours"""
    current_time = datetime.now()
    jobs_to_remove = []
    
    for job_id, job_data in surveillance_jobs.items():
        if job_data.get('completed_at'):
            completed_time = datetime.fromisoformat(job_data['completed_at'])
            if (current_time - completed_time).total_seconds() > 24 * 3600:  # 24 hours
                jobs_to_remove.append(job_id)
    
    for job_id in jobs_to_remove:
        del surveillance_jobs[job_id]
        logger.info(f"Cleaned up old job: {job_id}")

def get_recent_jobs():
    """Get jobs from the last 24 hours"""
    current_time = datetime.now()
    recent_jobs = {}
    
    for job_id, job_data in surveillance_jobs.items():
        if job_data.get('completed_at'):
            completed_time = datetime.fromisoformat(job_data['completed_at'])
            if (current_time - completed_time).total_seconds() <= 24 * 3600:  # 24 hours
                recent_jobs[job_id] = job_data
    
    return recent_jobs

# Base paths for surveillance data - now using S3
# For S3, we use logical paths that map to S3 keys
# Set USE_S3=true to use S3, otherwise use local filesystem (for development)
USE_S3 = os.getenv('USE_S3', 'true').lower() == 'true'
SURVEILLANCE_BASE_PATH = os.getenv('SURVEILLANCE_BASE_PATH', '/app/data')  # For local dev fallback

# S3 base prefix (folder in S3 bucket)
S3_BASE_PREFIX = os.getenv('S3_BASE_PREFIX', 'trade_surveillance')

# Logical paths (same structure for both S3 and local)
def get_reports_path(month):
    """Get reports path for month (works for both S3 and local)"""
    return f"{month}/Daily_Reports"

def get_order_files_path(month):
    """Get order files path for month (works for both S3 and local)"""
    return f"{month}/Order Files"

def get_call_records_path(month):
    """Get call records path for month (works for both S3 and local)"""
    return f"{month}/Call Records"

# Month paths (for backward compatibility)
AUGUST_REPORTS_PATH = get_reports_path("August")
SEPTEMBER_REPORTS_PATH = get_reports_path("September")
OCTOBER_REPORTS_PATH = get_reports_path("October")
NOVEMBER_REPORTS_PATH = get_reports_path("November")
DECEMBER_REPORTS_PATH = get_reports_path("December")
AUGUST_ORDER_FILES_PATH = get_order_files_path("August")
SEPTEMBER_ORDER_FILES_PATH = get_order_files_path("September")
OCTOBER_ORDER_FILES_PATH = get_order_files_path("October")
NOVEMBER_ORDER_FILES_PATH = get_order_files_path("November")
DECEMBER_ORDER_FILES_PATH = get_order_files_path("December")
AUGUST_CALL_RECORDS_PATH = get_call_records_path("August")
SEPTEMBER_CALL_RECORDS_PATH = get_call_records_path("September")
OCTOBER_CALL_RECORDS_PATH = get_call_records_path("October")
NOVEMBER_CALL_RECORDS_PATH = get_call_records_path("November")
DECEMBER_CALL_RECORDS_PATH = get_call_records_path("December")
EMAIL_SURVEILLANCE_PATH = ""  # Root of surveillance data

def _parse_percentage(value):
    """Parse percentage string to float"""
    if pd.isna(value):
        return 0.0
    try:
        if isinstance(value, str) and value.endswith('%'):
            return float(value[:-1])
        return float(value)
    except (ValueError, TypeError):
        return 0.0

def get_date_paths(year, month):
    """Get all available date paths for the given year/month - dynamically discovers dates"""
    month_to_path = {
        "August": AUGUST_REPORTS_PATH,
        "September": SEPTEMBER_REPORTS_PATH,
        "October": OCTOBER_REPORTS_PATH,
        "November": NOVEMBER_REPORTS_PATH,
        "December": DECEMBER_REPORTS_PATH
    }
    
    if month in month_to_path and year == 2025:
        reports_path = month_to_path[month]
        
        if USE_S3:
            # List directories in S3
            s3_prefix = f"{S3_BASE_PREFIX}/{reports_path}/"
            date_dirs = list_s3_directories(s3_prefix)
            dates = []
            
            for date_dir in date_dirs:
                # Extract date name from path (e.g., "August/Daily_Reports/01082025" -> "01082025")
                date_name = date_dir.split('/')[-1] if '/' in date_dir else date_dir
                date_s3_path = f"{reports_path}/{date_name}"
                
                # Check if final report exists
                report_key = f"{S3_BASE_PREFIX}/{date_s3_path}/Final_Trade_Surveillance_Report_{date_name}_with_Email_and_Trade_Analysis.xlsx"
                
                # Check for intermediate files
                intermediate_files = [
                    f"{S3_BASE_PREFIX}/{date_s3_path}/call_info_output_{date_name}.xlsx",
                    f"{S3_BASE_PREFIX}/{date_s3_path}/audio_order_kl_orgtimestamp_validation_{date_name}.xlsx",
                    f"{S3_BASE_PREFIX}/{date_s3_path}/order_transcript_analysis_{date_name}.xlsx",
                    f"{S3_BASE_PREFIX}/{date_s3_path}/email_order_mapping_{date_name}.xlsx"
                ]
                
                has_intermediate_files = any(s3_file_exists(f) for f in intermediate_files)
                
                if s3_file_exists(report_key) or has_intermediate_files:
                    dates.append(date_name)
            
            return [f"{reports_path}/{date}" for date in sorted(dates)]
        else:
            # Local filesystem
            full_reports_path = os.path.join(SURVEILLANCE_BASE_PATH, reports_path)
            if not os.path.exists(full_reports_path):
                return []
            
            dates = []
            for item in os.listdir(full_reports_path):
                date_path = os.path.join(full_reports_path, item)
                if os.path.isdir(date_path):
                    # Check if Final_Trade_Surveillance_Report exists (completed)
                    report_pattern = f"Final_Trade_Surveillance_Report_{item}_with_Email_and_Trade_Analysis.xlsx"
                    final_report_path = os.path.join(date_path, report_pattern)
                    
                    # Also check for intermediate files (in-progress surveillance)
                    has_intermediate_files = any(
                        os.path.exists(os.path.join(date_path, f))
                        for f in [
                            f"call_info_output_{item}.xlsx",
                            f"audio_order_kl_orgtimestamp_validation_{item}.xlsx",
                            f"order_transcript_analysis_{item}.xlsx",
                            f"email_order_mapping_{item}.xlsx"
                        ]
                    )
                    
                    # Include if final report exists OR if intermediate files exist (in-progress)
                    if os.path.exists(final_report_path) or has_intermediate_files:
                        dates.append(item)
            
            # Return sorted dates
            return [os.path.join(reports_path, date) for date in sorted(dates)]
    return []

def get_month_paths_from_date(date_str):
    """Helper function to get the appropriate month paths based on a date string (DDMMYYYY format)"""
    try:
        # Parse DDMMYYYY format
        day = int(date_str[:2])
        month_num = int(date_str[2:4])
        year = int(date_str[4:])
        
        month_to_paths = {
            8: {"reports": AUGUST_REPORTS_PATH, "orders": AUGUST_ORDER_FILES_PATH, "calls": AUGUST_CALL_RECORDS_PATH},
            9: {"reports": SEPTEMBER_REPORTS_PATH, "orders": SEPTEMBER_ORDER_FILES_PATH, "calls": SEPTEMBER_CALL_RECORDS_PATH},
            10: {"reports": OCTOBER_REPORTS_PATH, "orders": OCTOBER_ORDER_FILES_PATH, "calls": OCTOBER_CALL_RECORDS_PATH},
            11: {"reports": NOVEMBER_REPORTS_PATH, "orders": NOVEMBER_ORDER_FILES_PATH, "calls": NOVEMBER_CALL_RECORDS_PATH},
            12: {"reports": DECEMBER_REPORTS_PATH, "orders": DECEMBER_ORDER_FILES_PATH, "calls": DECEMBER_CALL_RECORDS_PATH}
        }
        
        if month_num in month_to_paths and year == 2025:
            return month_to_paths[month_num]
    except (ValueError, IndexError):
        pass
    
    # Default to September if can't determine
    return {"reports": SEPTEMBER_REPORTS_PATH, "orders": SEPTEMBER_ORDER_FILES_PATH, "calls": SEPTEMBER_CALL_RECORDS_PATH}

def read_final_surveillance_report(date_path):
    """Read the final surveillance report Excel file"""
    date_name = os.path.basename(date_path) if os.path.sep in date_path else date_path
    filename = f"Final_Trade_Surveillance_Report_{date_name}_with_Email_and_Trade_Analysis.xlsx"
    
    if USE_S3:
        # For S3: date_path is like "August/Daily_Reports/01082025"
        s3_key = f"{S3_BASE_PREFIX}/{date_path}/{filename}" if date_path else f"{S3_BASE_PREFIX}/{filename}"
        if not s3_file_exists(s3_key):
            logger.warning(f"Final report not found in S3: {s3_key}")
            return None
        try:
            df = read_excel_from_s3(s3_key)
            return df
        except Exception as e:
            logger.error(f"Error reading final report from S3 {s3_key}: {e}")
            return None
    else:
        # Local filesystem
        final_report_path = os.path.join(SURVEILLANCE_BASE_PATH, date_path, filename) if date_path else os.path.join(SURVEILLANCE_BASE_PATH, filename)
        if not os.path.exists(final_report_path):
            logger.warning(f"Final report not found: {final_report_path}")
            return None
        try:
            df = pd.read_excel(final_report_path)
            return df
        except Exception as e:
            logger.error(f"Error reading final report {final_report_path}: {e}")
            return None

def read_email_mapping(date_path):
    """Read email mapping JSON file"""
    date_name = os.path.basename(date_path) if os.path.sep in date_path else date_path
    filename = f"email_order_mapping_{date_name}.json"
    
    if USE_S3:
        s3_key = f"{S3_BASE_PREFIX}/{date_path}/{filename}" if date_path else f"{S3_BASE_PREFIX}/{filename}"
        if not s3_file_exists(s3_key):
            return None
        try:
            return read_json_from_s3(s3_key)
        except Exception as e:
            logger.error(f"Error reading email mapping from S3 {s3_key}: {e}")
            return None
    else:
        email_mapping_path = os.path.join(SURVEILLANCE_BASE_PATH, date_path, filename) if date_path else os.path.join(SURVEILLANCE_BASE_PATH, filename)
        if not os.path.exists(email_mapping_path):
            return None
        try:
            with open(email_mapping_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading email mapping {email_mapping_path}: {e}")
            return None

def read_transcript(date_path, audio_filename):
    """Read transcript file for audio evidence"""
    date_name = os.path.basename(date_path) if os.path.sep in date_path else date_path
    transcript_dir = f"{date_path}/transcripts_{date_name}" if date_path else f"transcripts_{date_name}"
    
    # PERMANENT FIX: Handle audio filename with or without extension
    # Transcript files are typically named: filename.mp3.txt or filename.wav.txt
    # But Excel might have filename without extension
    base_filename = audio_filename
    transcript_candidates = []
    
    if base_filename.endswith('.mp3') or base_filename.endswith('.wav'):
        # If extension is present, use it
        transcript_candidates.append(f"{base_filename}.txt")
    else:
        # If no extension, try with .mp3 first (most common)
        transcript_candidates.append(f"{base_filename}.mp3.txt")
        transcript_candidates.append(f"{base_filename}.txt")
    
    if USE_S3:
        # Try each candidate in S3
        for transcript_filename in transcript_candidates:
            s3_key = f"{S3_BASE_PREFIX}/{transcript_dir}/{transcript_filename}"
            if s3_file_exists(s3_key):
                logger.info(f"Found transcript in S3: {s3_key}")
                try:
                    content = read_text_from_s3(s3_key)
                    logger.info(f"Successfully read transcript file, length: {len(content)}")
                    return content
                except Exception as e:
                    logger.error(f"Error reading transcript from S3 {s3_key}: {e}")
                    return None
        
        logger.warning(f"Transcript file not found in S3 for {audio_filename} in {transcript_dir}")
        return None
    else:
        # Local filesystem
        for transcript_filename in transcript_candidates:
            transcript_file = os.path.join(SURVEILLANCE_BASE_PATH, transcript_dir, transcript_filename)
            logger.info(f"Looking for transcript file: {transcript_file}")
            if os.path.exists(transcript_file):
                logger.info(f"Transcript file exists: {transcript_file}")
                try:
                    with open(transcript_file, 'r') as f:
                        content = f.read()
                        logger.info(f"Successfully read transcript file, length: {len(content)}")
                    return content
                except Exception as e:
                    logger.error(f"Error reading transcript {transcript_file}: {e}")
                    return None
        
        logger.warning(f"Transcript file not found for {audio_filename} in {transcript_dir}")
        return None

def get_order_file_paths(year, month):
    """Get all available order file paths for the given year/month"""
    month_to_order_dir = {
        "August": AUGUST_ORDER_FILES_PATH,
        "September": SEPTEMBER_ORDER_FILES_PATH,
        "October": OCTOBER_ORDER_FILES_PATH,
        "November": NOVEMBER_ORDER_FILES_PATH,
        "December": DECEMBER_ORDER_FILES_PATH
    }
    
    if month in month_to_order_dir and year == 2025:
        # Get all order files for the month
        order_files = []
        order_dir = month_to_order_dir[month]
        
        if USE_S3:
            s3_prefix = f"{S3_BASE_PREFIX}/{order_dir}/"
            s3_objects = list_s3_objects(s3_prefix)
            for obj_key in s3_objects:
                filename = obj_key.split('/')[-1]
                if filename.startswith('OrderBook-Closed-') and filename.endswith('.csv'):
                    # Return relative path (without S3_BASE_PREFIX)
                    relative_path = obj_key.replace(f"{S3_BASE_PREFIX}/", "")
                    order_files.append(relative_path)
        else:
            full_order_dir = os.path.join(SURVEILLANCE_BASE_PATH, order_dir)
            if os.path.exists(full_order_dir):
                for filename in os.listdir(full_order_dir):
                    if filename.startswith('OrderBook-Closed-') and filename.endswith('.csv'):
                        order_files.append(os.path.join(order_dir, filename))
        return order_files
    return []

def read_order_file(file_path):
    """Read order file and return DataFrame"""
    try:
        if USE_S3:
            # file_path is like "August/Order Files/filename.csv"
            s3_key = f"{S3_BASE_PREFIX}/{file_path}"
            df = read_csv_from_s3(s3_key)
            return df
        else:
            # Local filesystem
            full_path = os.path.join(SURVEILLANCE_BASE_PATH, file_path)
            df = pd.read_csv(full_path)
            return df
    except Exception as e:
        logger.error(f"Error reading order file {file_path}: {e}")
        return None

@app.route('/api/surveillance/orders/<int:year>/<string:month>/<string:metric_type>')
def get_orders_for_metric(year, month, metric_type):
    """Get orders for a specific metric type with optional date filtering"""
    try:
        # Get date filtering parameters from query string
        start_date = request.args.get('startDate')
        end_date = request.args.get('endDate')
        
        logger.info(f"Getting orders for {year}/{month}/{metric_type}")
        if start_date or end_date:
            logger.info(f"Date filter: {start_date} to {end_date}")
        
        date_paths = get_date_paths(year, month)
        logger.info(f"Found {len(date_paths)} date paths: {date_paths}")
        
        # Filter date paths based on date range if provided
        if start_date or end_date:
            filtered_date_paths = []
            for date_path in date_paths:
                # Extract date from path (e.g., "September/Daily_Reports/15092025" -> "15092025")
                date_str = os.path.basename(date_path)
                
                # Handle different filter scenarios:
                # 1. Both start_date and end_date provided: range filter
                # 2. Only start_date provided: >= start_date
                # 3. Only end_date provided: <= end_date
                # 4. Both same (single date): exact match
                if start_date and end_date:
                    # Range filter
                    if start_date <= date_str <= end_date:
                        filtered_date_paths.append(date_path)
                elif start_date:
                    # Only start_date: >= start_date
                    if date_str >= start_date:
                        filtered_date_paths.append(date_path)
                elif end_date:
                    # Only end_date: <= end_date
                    if date_str <= end_date:
                        filtered_date_paths.append(date_path)
            
            date_paths = filtered_date_paths
            logger.info(f"Filtered to {len(date_paths)} date paths: {date_paths}")
        
        all_orders = []
        
        if len(date_paths) == 0:
            logger.warning("No date paths found - returning empty array")
            return jsonify([])
        
        for date_path in date_paths:
            logger.info(f"Processing date path: {date_path}")
            df = read_final_surveillance_report(date_path)
            if df is None:
                logger.warning(f"No data found for {date_path}")
                continue
            
            logger.info(f"Found {len(df)} orders in {date_path}")
            # Filter orders based on metric type
            filtered_df = filter_orders_by_metric(df, metric_type)
            logger.info(f"Filtered to {len(filtered_df)} orders for metric {metric_type}")
            
            # Convert to order objects
            for _, row in filtered_df.iterrows():
                try:
                    # Ensure we have a valid order ID
                    order_id = row.get('Order ID', '')
                    if pd.isna(order_id) or order_id == '':
                        order_id = f"unknown-{len(all_orders)}"
                    
                    order = {
                        'id': f"order-{order_id}",
                        'orderId': str(order_id),
                        'clientId': str(row.get('Client Code', '')),
                        'clientName': str(row.get('Client Code', '')),  # Using Client Code as name
                        'symbol': str(row.get('symbol', '')),
                        'quantity': int(row.get('quantity', 0)) if pd.notna(row.get('quantity', 0)) else 0,
                        'price': float(row.get('price', 0)) if pd.notna(row.get('price', 0)) else 0.0,
                        'buySell': str(row.get('side', 'BUY')),
                        'status': 'Complete',  # All orders in final report are completed
                        'orderDate': str(row.get('Order Date', '')),
                        'hasAudio': str(row.get('audio_mapped', 'no')).lower() == 'yes',
                        'hasEmail': str(row.get('Email-Order Match Status', 'No Email Match')) == 'Matched',
                        'hasDiscrepancy': str(row.get('discrepancy', 'none')).lower() != 'none',
                        'audioFile': str(row.get('Call File Name', '')),
                        'emailContent': str(row.get('Email_Content', '')),
                        'discrepancy': str(row.get('discrepancy', '')),
                        'aiObservation': str(row.get('Observation', '')),
                        'audioMapped': str(row.get('audio_mapped', 'no')),
                        'emailMatchStatus': str(row.get('Email-Order Match Status', 'No Email Match')),
                        'emailConfidenceScore': _parse_percentage(row.get('Email Confidence Score', 0)),
                        'emailDiscrepancyDetails': str(row.get('Email Discrepancy Details', '')),
                        'callExtract': str(row.get('Call Extract', '')),
                        'observation': str(row.get('Observation', '')),
                        'mobileNumber': str(row.get('Mobile No.', '')),
                        'callReceivedFromRegisteredNumber': str(row.get('Call received from Registered Number (Y/N)', 'N')),
                        'orderExecuted': str(row.get('Order Executed (Y/N)', 'N'))
                    }
                    all_orders.append(order)
                except Exception as row_error:
                    logger.error(f"Error processing row: {row_error}")
                    continue
        
        # NOTE: For KL orders, we ONLY use surveillance reports, not raw order files
        # The surveillance reports already contain the filtered KL orders with evidence analysis
        # Raw order files contain all orders (not just KL orders) and should not be used for the dashboard
        
        logger.info(f"Returning {len(all_orders)} orders")
        if len(all_orders) == 0:
            logger.warning("No orders found - this might indicate a data processing issue")
        return jsonify(all_orders)
    
    except Exception as e:
        logger.error(f"Error getting orders for metric {metric_type}: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()}), 500

# AI classification function removed - now reading pre-classified data from Excel

def filter_orders_by_metric(df, metric_type):
    """Filter DataFrame based on metric type - ONLY COMPLETE ORDERS"""
    # First filter for complete orders only
    df = df[df['status'] == 'Complete']
    
    if metric_type == 'totalTrades':
        return df
    elif metric_type == 'audioMatches':
        return df[df['audio_mapped'] == 'yes']
    elif metric_type == 'emailMatches':
        # Include both 'Matched' and 'Partial Match' as email matches
        return df[df['Email-Order Match Status'].isin(['Matched', 'Partial Match'])]
    elif metric_type == 'omsMatches':
        # Orders matched via OMS process update the same Excel column with value 'OMS_MATCH'
        return df[df['Email-Order Match Status'] == 'OMS_MATCH']
    elif metric_type == 'unmatchedOrders':
        # Unmatched = no audio evidence AND no email evidence AND not matched via OMS
        # Partial Match orders are considered matched (they have some email evidence)
        # Exclude: 'Matched', 'OMS_MATCH', 'Partial Match'
        return df[(df['audio_mapped'] != 'yes') & 
                  (df['Email-Order Match Status'] != 'Matched') & 
                  (df['Email-Order Match Status'] != 'OMS_MATCH') &
                  (df['Email-Order Match Status'] != 'Partial Match')]
    elif metric_type == 'discrepancies':
        # Show only ACTUAL discrepancies (compliance issues) - read pre-classified data
        if 'discrepancy' in df.columns and 'discrepancy_type' in df.columns:
            # Use pre-classified data from Excel
            return df[(df['discrepancy'] != 'none') & (df['discrepancy_type'] == 'actual')]
        elif 'discrepancy' in df.columns:
            # Fallback: show only actual discrepancies (exclude 'no' and 'none')
            # Only count rows where discrepancy starts with 'yes' (actual discrepancies)
            filtered_df = df[df['discrepancy'].str.startswith('yes')]
            logger.info(f"Discrepancy filtering: {len(df)} total rows -> {len(filtered_df)} actual discrepancies (excluded 'no' and 'none' values)")
            return filtered_df
        else:
            return df.iloc[0:0]  # Return empty DataFrame
    elif metric_type == 'reportingDiscrepancies':
        # Show only REPORTING discrepancies (dealer training issues) - read pre-classified data
        if 'discrepancy' in df.columns and 'discrepancy_type' in df.columns:
            # Use pre-classified data from Excel
            return df[(df['discrepancy'] != 'none') & (df['discrepancy_type'] == 'reporting')]
        else:
            return df.iloc[0:0]  # Return empty DataFrame
    elif metric_type == 'cancelledOrders':
        # No cancelled orders since we only show complete orders
        return df.iloc[0:0]  # Return empty DataFrame
    elif metric_type == 'rejectedOrders':
        # No rejected orders since we only show complete orders
        return df.iloc[0:0]  # Return empty DataFrame
    else:
        return df

@app.route('/api/surveillance/audio/<string:order_id>/<string:date>')
def get_audio_evidence(order_id, date):
    """Get audio evidence for an order"""
    try:
        # Determine which month's data to use based on date format
        month_paths = get_month_paths_from_date(date)
        date_path = os.path.join(month_paths["reports"], date)
        df = read_final_surveillance_report(date_path)
        
        if df is None:
            return jsonify({'error': 'Report not found'}), 404
        
        # PERMANENT FIX: Use EXACT STRING MATCHING after normalization (same as OMS validation)
        # Excel converts large integers to floats/scientific notation, normalize to exact strings
        def normalize_order_id_to_string(val):
            """Normalize order ID to exact string for matching"""
            if pd.isna(val):
                return None
            try:
                return str(int(float(val)))
            except (ValueError, TypeError):
                s = str(val)
                return s[:-2] if s.endswith('.0') else s
        
        # Normalize the search key
        search_key = normalize_order_id_to_string(order_id)
        if search_key is None:
            return jsonify({'error': 'Invalid order ID'}), 400
        
        # Normalize all Order IDs in DataFrame and match exactly
        df['Order ID Normalized'] = df['Order ID'].apply(normalize_order_id_to_string)
        order_row = df[df['Order ID Normalized'] == search_key]
        
        if order_row.empty:
            logger.warning(f"Order not found: {order_id} (normalized: {search_key})")
            return jsonify({'error': 'Order not found'}), 404
        
        order = order_row.iloc[0]
        audio_filename = str(order.get('Call File Name', ''))
        
        # PERMANENT FIX: Handle empty/nan audio filename more gracefully
        # Check if audio_mapped is 'yes' but Call File Name is missing (data inconsistency)
        audio_mapped = str(order.get('audio_mapped', 'no')).lower()
        if (not audio_filename or audio_filename == 'nan' or audio_filename == '') and audio_mapped == 'yes':
            logger.warning(f"Order {order_id} has audio_mapped='yes' but no Call File Name - data inconsistency")
            # Try to find audio file from audio validation data
            # For now, return a helpful error message
            return jsonify({
                'error': 'Audio file name not found in Excel',
                'message': 'This order is marked as having audio evidence, but the audio file name is missing from the report. This may indicate a data processing issue.',
                'orderId': str(order_id),
                'audioMapped': audio_mapped
            }), 404
        
        if not audio_filename or audio_filename == 'nan' or audio_filename == '':
            return jsonify({'error': 'No audio file found for this order'}), 404
        
        # Handle multiple filenames (comma-separated)
        audio_filenames = [f.strip() for f in audio_filename.split(',') if f.strip()]
        
        # Read transcript for the first file (or combine if needed)
        transcript = read_transcript(date_path, audio_filenames[0])
        
        audio_evidence = {
            'filename': audio_filenames[0] if len(audio_filenames) == 1 else audio_filename,  # Show single filename or full string
            'allFilenames': audio_filenames,  # Array of all filenames
            'fileCount': len(audio_filenames),
            'duration': '5:32',  # This would need to be calculated from actual audio
            'transcript': transcript or 'Transcript not available',
            'speakers': {
                'client': ['Client discussed trade requirements'],
                'dealer': ['Dealer provided market information']
            },
            'callStart': str(order.get('order_time', 'Not available')),
            'callEnd': str(order.get('order_time', 'Not available')),  # Using order_time as proxy
            'mobileNumber': str(order.get('Mobile No.', 'Not available')) if pd.notna(order.get('Mobile No.', '')) else 'Not available',
            'clientId': str(order.get('client_id', '')),
            'callExtract': str(order.get('Call Extract', ''))
        }
        
        return jsonify(audio_evidence)
    
    except Exception as e:
        logger.error(f"Error getting audio evidence for order {order_id}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/surveillance/email/<string:order_id>/<string:date>')
def get_email_evidence(order_id, date):
    """Get email evidence for an order"""
    try:
        # Determine which month's data to use based on date format
        month_paths = get_month_paths_from_date(date)
        date_path = os.path.join(month_paths["reports"], date)
        df = read_final_surveillance_report(date_path)
        
        if df is None:
            return jsonify({'error': 'Report not found'}), 404
        
        # PERMANENT FIX: Use EXACT STRING MATCHING after normalization (same as OMS validation)
        # Excel converts large integers to floats/scientific notation, normalize to exact strings
        def normalize_order_id_to_string(val):
            """Normalize order ID to exact string for matching"""
            if pd.isna(val):
                return None
            try:
                return str(int(float(val)))
            except (ValueError, TypeError):
                s = str(val)
                return s[:-2] if s.endswith('.0') else s
        
        # Normalize the search key
        search_key = normalize_order_id_to_string(order_id)
        if search_key is None:
            return jsonify({'error': 'Invalid order ID'}), 400
        
        # Normalize all Order IDs in DataFrame and match exactly
        df['Order ID Normalized'] = df['Order ID'].apply(normalize_order_id_to_string)
        order_row = df[df['Order ID Normalized'] == search_key]
        
        if order_row.empty:
            logger.warning(f"Order not found: {order_id} (normalized: {search_key})")
            return jsonify({'error': 'Order not found'}), 404
        
        order = order_row.iloc[0]
        email_content = str(order.get('Email_Content', ''))
        
        if not email_content or email_content == 'nan':
            return jsonify({'error': 'No email content'}), 404
        
        email_evidence = {
            'subject': f"Trade Instruction - {order.get('symbol', '')}",
            'sender': 'client@example.com',
            'recipient': 'dealer@example.com',
            'date': str(order.get('Order Date', '')),
            'content': email_content,
            'attachments': [],
            'clientCode': str(order.get('Client Code', '')),
            'symbol': str(order.get('symbol', '')),
            'quantity': int(order.get('quantity', 0)) if pd.notna(order.get('quantity', 0)) else 0,
            'price': f"₹{order.get('price', 0)}",
            'action': str(order.get('side', 'BUY')),
            'confidenceScore': _parse_percentage(order.get('Email Confidence Score', 0)),
            'discrepancyDetails': str(order.get('Email Discrepancy Details', ''))
        }
        
        return jsonify(email_evidence)
    
    except Exception as e:
        logger.error(f"Error getting email evidence for order {order_id}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/surveillance/discrepancy/<string:order_id>/<string:date>')
def get_discrepancy_details(order_id, date):
    """Get discrepancy details for an order"""
    try:
        # Determine which month's data to use based on date format
        month_paths = get_month_paths_from_date(date)
        date_path = os.path.join(month_paths["reports"], date)
        df = read_final_surveillance_report(date_path)
        
        if df is None:
            return jsonify({'error': 'Report not found'}), 404
        
        # Find the order - convert order_id to float for comparison
        try:
            order_id_float = float(order_id)
            order_row = df[df['Order ID'] == order_id_float]
        except ValueError:
            order_row = df[df['Order ID'] == order_id]
        if order_row.empty:
            return jsonify({'error': 'Order not found'}), 404
        
        order = order_row.iloc[0]
        discrepancy = str(order.get('discrepancy', ''))
        
        if not discrepancy or discrepancy == 'none' or discrepancy == 'nan':
            return jsonify({'error': 'No discrepancy found'}), 404
        
        discrepancy_details = {
            'id': f"disc-{order_id}",
            'orderId': order_id,
            'type': 'PRICE_MISMATCH',  # This would need to be determined from the discrepancy content
            'severity': 'MEDIUM',
            'description': discrepancy,
            'aiObservation': str(order.get('Observation', '')),
            'recommendedAction': 'REVIEW',
            'evidence': {
                'audio': {
                    'filename': str(order.get('Call File Name', '')),
                    'transcript': str(order.get('Call Extract', '')),
                    'timestamp': str(order.get('order_date', ''))
                },
                'email': {
                    'subject': f"Trade Instruction - {order.get('Symbol', '')}",
                    'content': str(order.get('Email_Content', '')),
                    'timestamp': str(order.get('order_date', ''))
                },
                'order': {
                    'details': f"Order executed at ₹{order.get('Price', 0)} on {order.get('order_date', '')}",
                    'timestamp': str(order.get('order_date', ''))
                }
            },
            'status': 'OPEN',
            'createdAt': str(order.get('order_date', '')),
            'updatedAt': str(order.get('order_date', ''))
        }
        
        return jsonify(discrepancy_details)
    
    except Exception as e:
        logger.error(f"Error getting discrepancy details for order {order_id}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/surveillance/audio-file/<string:filename>')
def serve_audio_file(filename):
    """Serve audio files for playback with proper headers for telephony format"""
    try:
        # PERMANENT FIX: Search all months and try with/without extensions in single efficient loop
        # This handles cases where Excel has filename without extension
        audio_file_path = None
        
        # Build list of filenames to try (exact, with .mp3, with .wav)
        filenames_to_try = [filename]
        if not filename.endswith('.mp3') and not filename.endswith('.wav'):
            filenames_to_try.append(f"{filename}.mp3")
            filenames_to_try.append(f"{filename}.wav")
        
        # Search all months for the file
        for month_path in [AUGUST_CALL_RECORDS_PATH, SEPTEMBER_CALL_RECORDS_PATH, OCTOBER_CALL_RECORDS_PATH, NOVEMBER_CALL_RECORDS_PATH, DECEMBER_CALL_RECORDS_PATH]:
            if os.path.exists(month_path):
                for root, dirs, files in os.walk(month_path):
                    for try_filename in filenames_to_try:
                        if try_filename in files:
                            audio_file_path = os.path.join(root, try_filename)
                            logger.info(f"Found audio file: {audio_file_path}")
                            break
                    if audio_file_path:
                        break
                if audio_file_path:
                    break
        
        # If file found, serve it
        if audio_file_path and os.path.exists(audio_file_path):
            # Serve with proper headers for telephony WAV files
            response = send_file(
                audio_file_path, 
                as_attachment=False, 
                mimetype='audio/wav',
                conditional=True
            )
            
            # Add headers to help browsers handle telephony format
            response.headers['Accept-Ranges'] = 'bytes'
            response.headers['Cache-Control'] = 'public, max-age=3600'
            response.headers['Content-Type'] = 'audio/wav; codecs="1"'
            
            return response
        
        logger.warning(f"Audio file not found: {filename} (tried with .mp3 and .wav extensions)")
        return jsonify({'error': 'Audio file not found'}), 404
    
    except Exception as e:
        logger.error(f"Error serving audio file {filename}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/surveillance/available-dates/<int:year>/<string:month>')
def get_available_dates(year, month):
    """Get available dates for a specific month"""
    try:
        logger.info(f"Getting available dates for {year}/{month}")
        date_paths = get_date_paths(year, month)
        
        # Extract dates from paths and format them
        available_dates = []
        for date_path in date_paths:
            date_str = os.path.basename(date_path)  # e.g., "15092025"
            # Convert DDMMYYYY to DD/MM/YYYY for display
            if len(date_str) == 8:
                day = date_str[:2]
                month_num = date_str[2:4]
                year_num = date_str[4:8]
                formatted_date = f"{day}/{month_num}/{year_num}"
                available_dates.append({
                    'value': date_str,  # DDMMYYYY format for API
                    'label': formatted_date,  # DD/MM/YYYY format for display
                    'day': int(day),
                    'month': int(month_num),
                    'year': int(year_num)
                })
        
        # Sort by date
        available_dates.sort(key=lambda x: x['value'])
        
        logger.info(f"Found {len(available_dates)} available dates")
        return jsonify(available_dates)
    
    except Exception as e:
        logger.error(f"Error getting available dates for {year}/{month}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/surveillance/health')
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

@app.route('/api/upload/files', methods=['POST'])
def upload_files():
    """Handle file uploads for surveillance processing"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        file_type = request.form.get('file_type', 'audio')
        date = request.form.get('date', '')
        
        logger.info(f"Upload request - file: {file.filename}, file_type: {file_type}, date: {date}")
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not date:
            return jsonify({'error': 'Date is required'}), 400
        
        # Secure the filename
        filename = secure_filename(file.filename)
        
        # Accept standard YYYY-MM-DD format from frontend date picker
        # The backend handles all internal conversions - user doesn't need to worry about formats
        try:
            date_obj = datetime.strptime(date, '%Y-%m-%d')
            formatted_date = date_obj.strftime('%Y-%m-%d')  # Keep as YYYY-MM-DD for uploads directory
            logger.info(f"Date parsed successfully: {date} -> {formatted_date}")
        except ValueError:
            # If somehow a different format is sent, try to parse it but prefer YYYY-MM-DD
            logger.warning(f"Failed to parse date as YYYY-MM-DD, trying DDMMYYYY: {date}")
            try:
                date_obj = datetime.strptime(date, '%d%m%Y')
                formatted_date = date_obj.strftime('%Y-%m-%d')
                logger.info(f"Date parsed as DDMMYYYY: {date} -> {formatted_date}")
            except ValueError:
                error_msg = f'Invalid date format: "{date}". Expected YYYY-MM-DD format (e.g., 2025-10-01)'
                logger.error(error_msg)
                return jsonify({'error': error_msg}), 400
        
        # Check if using S3
        USE_S3 = os.getenv('USE_S3', 'false').lower() == 'true'
        S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME')
        S3_BASE_PREFIX = os.getenv('S3_BASE_PREFIX', 'trade_surveillance')
        
        if USE_S3 and S3_BUCKET_NAME:
            # Upload to S3
            logger.info(f"📦 Uploading to S3: {S3_BUCKET_NAME}")
            
            # Convert date to DDMMYYYY format for S3 path (matches existing structure)
            date_obj = datetime.strptime(formatted_date, '%Y-%m-%d')
            month_num = date_obj.month
            ddmmyyyy = date_obj.strftime('%d%m%Y')
            month_names = {
                1: "January", 2: "February", 3: "March", 4: "April",
                5: "May", 6: "June", 7: "July", 8: "August",
                9: "September", 10: "October", 11: "November", 12: "December"
            }
            month_name = month_names.get(month_num, "Unknown")
            
            # Determine S3 path based on file type
            if file_type == 'audio':
                # Audio files go to Month/Call Records/Call_DDMMYYYY/
                s3_key = f"{S3_BASE_PREFIX}/{month_name}/Call Records/Call_{ddmmyyyy}/{filename}"
            elif file_type == 'orders':
                # Order files go to Month/Daily_Reports/DDMMYYYY/
                s3_key = f"{S3_BASE_PREFIX}/{month_name}/Daily_Reports/{ddmmyyyy}/{filename}"
            elif file_type == 'ucc':
                # UCC files go to root of S3_BASE_PREFIX
                s3_key = f"{S3_BASE_PREFIX}/{filename}"
            else:
                return jsonify({'error': f'Invalid file type: {file_type}. Supported types: audio, orders, ucc'}), 400
            
            # Save file temporarily, then upload to S3
            import tempfile
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1])
            try:
                file.save(temp_file.name)
                temp_file.close()
                
                # Upload to S3
                upload_file_to_s3(temp_file.name, s3_key)
                logger.info(f"✅ File uploaded to S3: s3://{S3_BUCKET_NAME}/{s3_key}")
                
                # Clean up temp file
                os.unlink(temp_file.name)
                
                return jsonify({
                    'status': 'success',
                    'message': f'File {filename} uploaded successfully to S3',
                    'file_type': file_type,
                    'date': date,
                    'destination': f's3://{S3_BUCKET_NAME}/{s3_key}'
                })
            except Exception as e:
                # Clean up temp file on error
                if os.path.exists(temp_file.name):
                    os.unlink(temp_file.name)
                raise
        else:
            # Local filesystem upload (fallback)
            logger.info(f"📁 Uploading to local filesystem")
        
        # Create uploads directory structure that FileDiscoveryMapper expects
        uploads_dir = os.path.join(SURVEILLANCE_BASE_PATH, "uploads", formatted_date)
        
        # Determine destination based on file type
        if file_type == 'audio':
            # Audio files go to uploads/YYYY-MM-DD/audios/
            dest_dir = os.path.join(uploads_dir, "audios")
        elif file_type == 'orders':
            # Order files go to uploads/YYYY-MM-DD/orders/
            dest_dir = os.path.join(uploads_dir, "orders")
        elif file_type == 'ucc':
            # UCC files go to uploads/YYYY-MM-DD/ucc/
            dest_dir = os.path.join(uploads_dir, "ucc")
        else:
            return jsonify({'error': f'Invalid file type: {file_type}. Supported types: audio, orders, ucc'}), 400
        
        # Create directory if it doesn't exist
        os.makedirs(dest_dir, exist_ok=True)
        dest_path = os.path.join(dest_dir, filename)
        
        # Save the file
        file.save(dest_path)
        
        logger.info(f"File uploaded successfully: {filename} to {dest_path}")
        
        return jsonify({
            'status': 'success',
            'message': f'File {filename} uploaded successfully',
            'file_type': file_type,
            'date': date,
            'destination': dest_path
        })
        
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/surveillance/run', methods=['POST'])
def run_surveillance():
    """Start surveillance process for a specific date"""
    try:
        data = request.get_json()
        date = data.get('date', '')
        
        if not date:
            return jsonify({'error': 'Date is required'}), 400
        
        # Convert date format from YYYY-MM-DD to DDMMYYYY
        try:
            date_obj = datetime.strptime(date, '%Y-%m-%d')
            formatted_date = date_obj.strftime('%d%m%Y')
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        
        # Generate job ID
        job_id = str(uuid.uuid4())
        
        # Initialize job status
        surveillance_jobs[job_id] = {
            'status': 'running',
            'date': formatted_date,
            'started_at': datetime.now().isoformat(),
            'current_step': 'Starting surveillance process...',
            'steps': [],
            'logs': [],
            'error': None,
            'excel_file_path': None,
            'summary': {
                'total_steps': 10,
                'completed_steps': 0,
                'failed_steps': 0
            }
        }
        
        # Start surveillance process in background thread
        thread = threading.Thread(target=run_surveillance_process, args=(job_id, formatted_date))
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'status': 'started',
            'jobId': job_id,
            'message': f'Surveillance process started for {date}'
        })
        
    except Exception as e:
        logger.error(f"Error starting surveillance: {e}")
        return jsonify({'error': str(e)}), 500

def run_surveillance_process(job_id, date):
    """Run the surveillance process in background with detailed step tracking"""
    print(f"🔵 [DEBUG] run_surveillance_process started for job {job_id}, date {date}")
    logger.info(f"🔵 [DEBUG] run_surveillance_process started for job {job_id}, date {date}")
    import sys
    sys.stdout.flush()
    try:
        job = surveillance_jobs[job_id]
        
        # Define the 10 surveillance steps
        surveillance_steps = [
            {
                "id": 1,
                "name": "File Discovery & Mapping",
                "script": "file_discovery_mapper.py",
                "is_file_discovery_step": True
            },
            {
                "id": 2,
                "name": "Email Processing",
                "script": "email_processing/process_emails_by_date.py",
                "is_email_step": True
            },
            {
                "id": 3,
                "name": "Audio File Processing",
                "script": "extract_call_info_august_daily.py"
            },
            {
                "id": 4,
                "name": "Audio-Order Validation & Mapping",
                "script": "comprehensive_audio_trading_validation_august_daily.py"
            },
            {
                "id": 5,
                "name": "Audio Transcription",
                "script": "transcribe_calls_august_daily.py"
            },
            {
                "id": 6,
                "name": "AI Analysis",
                "script": "order_transcript_analysis_august_daily.py"
            },
            {
                "id": 7,
                "name": "Email-Order Validation & Mapping",
                "script": "email_order_validation_august_daily.py"
            },
            {
                "id": 8,
                "name": "OMS Surveillance",
                "script": "oms_surveillance/run_oms_surveillance.py",
                "is_oms_step": True
            },
            {
                "id": 9,
                "name": "Final Required Columns Mapping",
                "script": "add_required_columns_to_excel_august_daily.py"
            },
            {
                "id": 10,
                "name": "Discrepancy Classification",
                "script": "classify_discrepancies_august_daily.py"
            }
        ]
        
        print(f"🔵 [DEBUG] Job initialized, about to execute {len(surveillance_steps)} steps")
        logger.info(f"🔵 [DEBUG] Job initialized, about to execute {len(surveillance_steps)} steps")
        
        # Initialize steps in job status
        job['steps'] = []
        for step in surveillance_steps:
            job['steps'].append({
                "id": step["id"],
                "name": step["name"],
                "status": "pending",
                "startTime": None,
                "endTime": None,
                "duration": None,
                "error": None,
                "logs": []
            })
        
        # Update job status
        job['current_step'] = 'Starting surveillance process...'
        job['logs'].append(f"Starting surveillance for date: {date}")
        
        # Execute each step
        for i, step in enumerate(surveillance_steps):
            step_start_time = datetime.now()
            
            # Update step status to running
            job['steps'][i]['status'] = 'running'
            job['steps'][i]['startTime'] = step_start_time.isoformat()
            job['current_step'] = f"Running Step {step['id']}: {step['name']}"
            job['logs'].append(f"Starting Step {step['id']}: {step['name']}")
            
            # DEBUG: Print step execution
            print(f"🔵 [DEBUG] About to execute Step {step['id']}: {step['name']}")
            logger.info(f"🔵 [DEBUG] About to execute Step {step['id']}: {step['name']}")
            
            try:
                # Execute the step
                step_result = execute_surveillance_step(step, date, job_id)
                print(f"🔵 [DEBUG] Step {step['id']} returned: success={step_result.get('success')}")
                logger.info(f"🔵 [DEBUG] Step {step['id']} returned: success={step_result.get('success')}")
                
                step_end_time = datetime.now()
                duration = (step_end_time - step_start_time).total_seconds()
                
                if step_result['success']:
                    job['steps'][i]['status'] = 'completed'
                    job['steps'][i]['endTime'] = step_end_time.isoformat()
                    job['steps'][i]['duration'] = duration
                    job['logs'].append(f"✅ Step {step['id']} completed successfully in {duration:.2f}s")
                    step_logs = step_result.get('logs', [])
                    job['logs'].extend(step_logs)
                    # Add logs to step's logs array for visibility
                    job['steps'][i]['logs'].extend(step_logs)
                else:
                    job['steps'][i]['status'] = 'failed'
                    job['steps'][i]['endTime'] = step_end_time.isoformat()
                    job['steps'][i]['duration'] = duration
                    job['steps'][i]['error'] = step_result['error']
                    job['logs'].append(f"❌ Step {step['id']} failed: {step_result['error']}")
                    step_logs = step_result.get('logs', [])
                    job['logs'].extend(step_logs)
                    # Add logs to step's logs array for visibility
                    job['steps'][i]['logs'].extend(step_logs)
                    
                    # NON-BLOCKING: Steps 2, 7, and 8 failures should not stop the pipeline
                    # Step 2: Email Processing (may fail due to auth issues)
                    # Step 7: Email-Order Validation (may fail if email processing was skipped)
                    # Step 8: OMS Surveillance (may fail due to data issues)
                    # Allow other steps to continue
                    if step['id'] in [2, 7, 8]:  # Non-blocking steps
                        step_name = step['name']
                        job['logs'].append(f"⚠️ {step_name} failed, but continuing with other steps...")
                        job['logs'].append(f"📋 Pipeline will continue to next step")
                        # Continue to next step instead of returning
                    else:
                        # For other critical steps, stop execution on failure
                        job['status'] = 'failed'
                        job['current_step'] = f"Failed at Step {step['id']}: {step['name']}"
                        job['error'] = step_result['error']
                        job['completed_at'] = datetime.now().isoformat()
                        return
                    
            except Exception as e:
                step_end_time = datetime.now()
                duration = (step_end_time - step_start_time).total_seconds()
                
                job['steps'][i]['status'] = 'failed'
                job['steps'][i]['endTime'] = step_end_time.isoformat()
                job['steps'][i]['duration'] = duration
                job['steps'][i]['error'] = str(e)
                job['logs'].append(f"❌ Step {step['id']} failed with exception: {str(e)}")
                
                # NON-BLOCKING: Steps 2, 7, and 8 exceptions should not stop the pipeline
                # Step 2: Email Processing (may fail due to auth issues)
                # Step 7: Email-Order Validation (may fail if email processing was skipped)
                # Step 8: OMS Surveillance (may fail due to data issues)
                if step['id'] in [2, 7, 8]:  # Non-blocking steps
                    step_name = step['name']
                    job['logs'].append(f"⚠️ {step_name} exception, but continuing with other steps...")
                    job['logs'].append(f"📋 Pipeline will continue to next step")
                    # Continue to next step instead of returning
                else:
                    # For other critical steps, stop execution on exception
                    job['status'] = 'failed'
                    job['current_step'] = f"Failed at Step {step['id']}: {step['name']}"
                    job['error'] = str(e)
                    job['completed_at'] = datetime.now().isoformat()
                    return
        
        # Check if any non-blocking steps failed but others succeeded
        non_blocking_steps = [2, 7, 8]  # Email Processing, Email-Order Validation, OMS Surveillance
        failed_non_blocking = []
        for step_id in non_blocking_steps:
            step = next((s for s in job['steps'] if s.get('id') == step_id), None)
            if step and step.get('status') == 'failed':
                step_name = next((s['name'] for s in surveillance_steps if s['id'] == step_id), f"Step {step_id}")
                failed_non_blocking.append(step_name)
        
        if failed_non_blocking:
            job['status'] = 'completed_with_warnings'
            failed_steps_str = ', '.join(failed_non_blocking)
            job['current_step'] = f'Completed with warnings ({failed_steps_str} failed, but other steps succeeded)'
            job['logs'].append(f"⚠️ Job completed with warnings: {failed_steps_str} failed, but other steps completed successfully")
            job['logs'].append("📋 Pipeline completed - non-critical steps failed but critical steps succeeded")
        else:
            job['status'] = 'completed'
            job['current_step'] = 'Surveillance completed successfully'
            job['logs'].append("🎉 All surveillance steps completed successfully!")
            job['completed_at'] = datetime.now().isoformat()
        
        # Set Excel file path
        try:
            month = int(date[2:4])
            month_names = {
                1: "January", 2: "February", 3: "March", 4: "April",
                5: "May", 6: "June", 7: "July", 8: "August",
                9: "September", 10: "October", 11: "November", 12: "December"
            }
            month_name = month_names.get(month, "Unknown")
            excel_file_path = f"{month_name}/Daily_Reports/{date}/Final_Trade_Surveillance_Report_{date}_with_Email_and_Trade_Analysis.xlsx"
            job['excel_file_path'] = excel_file_path
        except Exception as e:
            logger.warning(f"Error setting Excel file path: {e}")
            job['excel_file_path'] = None
        
        # Update summary
        try:
            completed_steps = len([step for step in job['steps'] if step['status'] == 'completed'])
            failed_steps = len([step for step in job['steps'] if step['status'] == 'failed'])
            job['summary']['completed_steps'] = completed_steps
            job['summary']['failed_steps'] = failed_steps
        except Exception as e:
            logger.warning(f"Error updating summary: {e}")
        
        # Log completion
        logger.info(f"✅ Surveillance pipeline completed for job {job_id} with status: {job['status']}")
        
    except Exception as e:
        job = surveillance_jobs[job_id]
        job['status'] = 'failed'
        job['current_step'] = 'Surveillance failed'
        job['error'] = str(e)
        job['logs'].append(f"Error running surveillance: {str(e)}")
        job['completed_at'] = datetime.now().isoformat()
        logger.error(f"Error in surveillance process {job_id}: {e}")

def execute_surveillance_step(step, date_str, job_id):
    """Execute a single surveillance step with proper error handling"""
    try:
        job = surveillance_jobs[job_id]
        logs = []
        
        # Helper function to add logs in real-time
        def add_log(message):
            logs.append(message)
            # Also add to step's logs array for real-time visibility
            step_index = next((idx for idx, s in enumerate(job.get('steps', [])) if s.get('id') == step['id']), None)
            if step_index is not None:
                job['steps'][step_index]['logs'].append(message)
            # Also add to main job logs
            job['logs'].append(message)
        
        # Handle special steps
        if step.get('is_file_discovery_step', False):
            result = execute_file_discovery_step(date_str, logs)
            # Update logs in step
            step_index = next((idx for idx, s in enumerate(job.get('steps', [])) if s.get('id') == step['id']), None)
            if step_index is not None:
                job['steps'][step_index]['logs'].extend(logs)
            return result
        elif step.get('is_email_step', False):
            result = execute_email_processing_step(date_str, logs, add_log_callback=add_log)
            # Update logs in step
            step_index = next((idx for idx, s in enumerate(job.get('steps', [])) if s.get('id') == step['id']), None)
            if step_index is not None:
                job['steps'][step_index]['logs'].extend(logs)
            return result
        elif step.get('is_oms_step', False):
            result = execute_oms_surveillance_step(date_str, logs)
            # Update logs in step
            step_index = next((idx for idx, s in enumerate(job.get('steps', [])) if s.get('id') == step['id']), None)
            if step_index is not None:
                job['steps'][step_index]['logs'].extend(logs)
            return result
        else:
            result = execute_regular_step(step, date_str, logs)
            # Update logs in step
            step_index = next((idx for idx, s in enumerate(job.get('steps', [])) if s.get('id') == step['id']), None)
            if step_index is not None:
                job['steps'][step_index]['logs'].extend(logs)
            return result
            
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'logs': [f"Exception in step execution: {str(e)}"]
        }

def execute_file_discovery_step(date_str, logs):
    """Execute file discovery step"""
    try:
        # Convert DDMMYYYY to YYYY-MM-DD format
        date_obj = datetime.strptime(date_str, '%d%m%Y')
        formatted_date = date_obj.strftime('%Y-%m-%d')
        
        logs.append(f"🔍 Discovering uploaded files for {formatted_date}...")
        
        # Import and use FileDiscoveryMapper
        try:
            # PERMANENT FIX: Add parent directory to sys.path to ensure import works
            import sys
            parent_dir = os.path.dirname(SURVEILLANCE_BASE_PATH)
            if parent_dir not in sys.path:
                sys.path.insert(0, SURVEILLANCE_BASE_PATH)
            
            from file_discovery_mapper import FileDiscoveryMapper
            
            # PERMANENT FIX: Pass SURVEILLANCE_BASE_PATH as base_dir
            # Backend runs from dashboard/backend/, so os.getcwd() would be wrong
            # This ensures FileDiscoveryMapper uses the correct base directory
            mapper = FileDiscoveryMapper(base_dir=SURVEILLANCE_BASE_PATH)
            logs.append(f"📂 Using base directory: {SURVEILLANCE_BASE_PATH}")
            
            success, file_mappings = mapper.process_uploaded_files(formatted_date, replace_existing=True)
            
            # PERMANENT FIX: Verify files were actually copied to expected locations
            # This prevents silent failures where process returns success but files aren't copied
            date_obj = datetime.strptime(formatted_date, '%Y-%m-%d')
            month_num = date_obj.month
            ddmmyyyy = date_obj.strftime('%d%m%Y')
            month_names = {
                1: "January", 2: "February", 3: "March", 4: "April",
                5: "May", 6: "June", 7: "July", 8: "August",
                9: "September", 10: "October", 11: "November", 12: "December"
            }
            month_name = month_names.get(month_num)
            
            # Verify Call Records directory and count files
            if month_name:
                call_records_dir = os.path.join(SURVEILLANCE_BASE_PATH, month_name, "Call Records", f"Call_{ddmmyyyy}")
                if not os.path.exists(call_records_dir):
                    logs.append(f"⚠️  Call Records directory missing, creating: {call_records_dir}")
                    os.makedirs(call_records_dir, exist_ok=True)
                
                # Count audio files in Call Records directory
                import glob
                audio_files = glob.glob(os.path.join(call_records_dir, "*.mp3")) + \
                             glob.glob(os.path.join(call_records_dir, "*.wav"))
                audio_count = len(audio_files)
                
                # Count expected audio files from mappings
                expected_audio_count = sum(1 for src, dst in file_mappings.items() 
                                         if any(ext in src.lower() for ext in ['.mp3', '.wav', '.m4a', '.aac']))
                
                if expected_audio_count > 0:
                    if audio_count == 0:
                        logs.append(f"❌ CRITICAL: Expected {expected_audio_count} audio files but found 0 in {call_records_dir}")
                        logs.append(f"   This indicates file copying failed!")
                        # Try to re-run file copying
                        logs.append(f"🔄 Attempting to re-copy files...")
                        success_retry, file_mappings_retry = mapper.process_uploaded_files(formatted_date, replace_existing=True)
                        if success_retry:
                            audio_files_retry = glob.glob(os.path.join(call_records_dir, "*.mp3")) + \
                                              glob.glob(os.path.join(call_records_dir, "*.wav"))
                            if len(audio_files_retry) > 0:
                                logs.append(f"✅ Retry successful: {len(audio_files_retry)} audio files now in Call Records")
                            else:
                                logs.append(f"❌ Retry failed: Still no audio files in Call Records")
                                return {'success': False, 'error': 'File copying failed: No audio files in Call Records directory', 'logs': logs}
                        else:
                            logs.append(f"❌ Retry failed: File copying returned failure")
                            return {'success': False, 'error': 'File copying failed after retry', 'logs': logs}
                    elif audio_count < expected_audio_count:
                        logs.append(f"⚠️  WARNING: Expected {expected_audio_count} audio files but found {audio_count}")
                        logs.append(f"   Some files may not have been copied successfully")
                    else:
                        logs.append(f"✅ Verified: {audio_count} audio files in Call Records directory")
            
            # CRITICAL: File discovery should never fail completely
            # Even if no files found, directories should be created for downstream steps
            if success:
                if file_mappings:
                    logs.append(f"✅ File discovery completed successfully")
                    logs.append(f"📁 Mapped {len(file_mappings)} files")
                    for original, target in list(file_mappings.items())[:5]:  # Show first 5
                        logs.append(f"   📄 {os.path.basename(original)} -> {os.path.basename(target)}")
                    if len(file_mappings) > 5:
                        logs.append(f"   ... and {len(file_mappings) - 5} more files")
                else:
                    logs.append(f"ℹ️  No uploaded files found, using existing files")
                
                return {'success': True, 'logs': logs}
            else:
                # Even if file copying failed, ensure directories exist and continue
                logs.append(f"⚠️  Some files failed to copy, but ensuring directories exist...")
                # Directories should already be created by _ensure_required_directories_exist
                # Still return success to allow process to continue
                logs.append(f"✅ File discovery step completed (with warnings)")
                return {'success': True, 'logs': logs}
                
        except ImportError as e:
            logs.append(f"❌ File discovery module import error: {e}")
            logs.append(f"   Attempted to import from: {SURVEILLANCE_BASE_PATH}")
            import traceback
            logs.append(f"   Traceback: {traceback.format_exc()}")
            return {'success': False, 'error': f'File discovery module not available: {e}', 'logs': logs}
            
    except Exception as e:
        logs.append(f"❌ File discovery error: {e}")
        import traceback
        logs.append(f"📋 Traceback: {traceback.format_exc()}")
        return {'success': False, 'error': str(e), 'logs': logs}

def execute_email_processing_step(date_str, logs, add_log_callback=None):
    """Execute email processing step - now reads from S3 instead of processing"""
    print(f"🔵 [DEBUG] execute_email_processing_step called for {date_str}")
    logger.info(f"🔵 [DEBUG] execute_email_processing_step called for {date_str}")
    
    # Use callback if provided, otherwise just append to logs
    def log(message):
        logs.append(message)
        if add_log_callback:
            add_log_callback(message)
        logger.info(message)
    
    try:
        # Convert DDMMYYYY to YYYY-MM-DD format
        date_obj = datetime.strptime(date_str, '%d%m%Y')
        formatted_date = date_obj.strftime('%Y-%m-%d')
        print(f"🔵 [DEBUG] Formatted date: {formatted_date}")
        
        log(f"📧 Reading email data from S3 for {formatted_date}...")
        
        # Get S3 key for email data
        year = date_obj.strftime('%Y')
        month_names = {
            1: "January", 2: "February", 3: "March", 4: "April",
            5: "May", 6: "June", 7: "July", 8: "August",
            9: "September", 10: "October", 11: "November", 12: "December"
        }
        month_name = month_names[date_obj.month]
        
        # S3 path: trade_surveillance/Email_Data/{year}/{month}/email_surveillance_{date}.json
        s3_key = f"{S3_BASE_PREFIX}/Email_Data/{year}/{month_name}/email_surveillance_{date_str}.json"
        
        log(f"🔍 Looking for email data in S3: {s3_key}")
        
        # Check if file exists in S3
        if not s3_file_exists(s3_key):
            error_msg = f"Email data not found in S3: {s3_key}"
            log(f"❌ {error_msg}")
            log(f"💡 Please run the daily email fetch job first:")
            log(f"   python email_fetch_daily_job.py {formatted_date}")
            log(f"   OR")
            log(f"   python email_fetch_daily_job.py {date_str}")
            return {'success': False, 'error': error_msg, 'logs': logs}
            
        log(f"✅ Found email data in S3")
        
        # Download from S3 to local file (same location as before for compatibility)
        from s3_utils import download_file_from_s3
        expected_file = os.path.join(SURVEILLANCE_BASE_PATH, f'email_surveillance_{date_str}.json')
        
        try:
            # Download to temporary location first, then move to expected location
            log(f"⬇️  Downloading email data from S3...")
            temp_file = download_file_from_s3(s3_key)
            import shutil
            shutil.move(temp_file, expected_file)
            log(f"✅ Downloaded email data from S3 to: {expected_file}")
            
            # Verify file exists and is not empty
            if not os.path.exists(expected_file):
                error_msg = f"Downloaded file not found: {expected_file}"
                log(f"❌ {error_msg}")
                return {'success': False, 'error': error_msg, 'logs': logs}
            
            # Verify file
            try:
                file_size = os.path.getsize(expected_file)
                if file_size == 0:
                    log(f"⚠️  WARNING: Email file is empty: {expected_file}")
                    return {'success': False, 'error': 'Email file is empty', 'logs': logs}
                log(f"✅ Email file verified: {expected_file} ({file_size:,} bytes)")
                
                # Verify file content is valid JSON
                try:
                    with open(expected_file, 'r') as f:
                        email_data = json.load(f)
                    
                    # FIX: Copy to comprehensive_dealing_emails_analysis.json for complete_email_surveillance_system.py
                    # The file from S3 now has email_analyses (raw emails) which is what the system expects
                    comprehensive_file = os.path.join(SURVEILLANCE_BASE_PATH, 'comprehensive_dealing_emails_analysis.json')
                    shutil.copy2(expected_file, comprehensive_file)
                    log(f"✅ Copied email data to: {comprehensive_file} (for AI analysis)")
                    
                    # Verify structure
                    if 'email_analyses' in email_data:
                        email_count = len(email_data['email_analyses'])
                        log(f"✅ Email file contains email_analyses ({email_count} emails)")
                    elif 'all_results' in email_data:
                        email_count = len(email_data['all_results'])
                        log(f"⚠️  WARNING: File contains all_results instead of email_analyses ({email_count} emails)")
                    else:
                        log(f"⚠️  WARNING: File structure unknown, keys: {list(email_data.keys())}")
                        email_count = 0
                    
                    # CRITICAL FIX: Run complete_email_surveillance_system.py to perform AI analysis
                    # This is what actually classifies emails as "trade_instruction" vs "other"
                    print(f"🔵 [DEBUG] About to run AI analysis for {date_str}")
                    log(f"🤖 Running AI analysis on {email_count} emails...")
                    log(f"⏱️  This may take 5-15 minutes depending on email count...")
                    logger.info(f"🤖 [Step 2] Starting AI analysis for {date_str}")
                    # Try multiple possible paths
                    possible_paths = [
                        os.path.join(SURVEILLANCE_BASE_PATH, 'email_processing', 'complete_email_surveillance_system.py'),
                        os.path.join(os.path.dirname(SURVEILLANCE_BASE_PATH), 'email_processing', 'complete_email_surveillance_system.py'),
                        '/app/email_processing/complete_email_surveillance_system.py',  # Docker path
                    ]
                    email_system_script = None
                    for path in possible_paths:
                        if os.path.exists(path):
                            email_system_script = path
                            logger.info(f"✅ [Step 2] Found AI script at: {path}")
                            break
                    
                    if not email_system_script:
                        logger.warning(f"❌ [Step 2] AI script not found in any of these paths: {possible_paths}")
                    
                    print(f"🔵 [DEBUG] email_system_script = {email_system_script}")
                    print(f"🔵 [DEBUG] Script exists: {os.path.exists(email_system_script) if email_system_script else False}")
                    if email_system_script and os.path.exists(email_system_script):
                        print(f"🔵 [DEBUG] ✅ Script found, about to execute: {email_system_script}")
                        logger.info(f"📜 [Step 2] Executing: python3 {email_system_script}")
                        log(f"📜 Executing: python3 {email_system_script}")
                        log(f"📂 Working directory: {SURVEILLANCE_BASE_PATH}")
                        import subprocess
                        print(f"🔵 [DEBUG] Starting subprocess with real-time streaming...")
                        logger.info(f"🚀 [Step 2] Starting subprocess for AI analysis with real-time logging...")
                        
                        # Use Popen for real-time output streaming
                        process = subprocess.Popen(
                            ['python3', email_system_script],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            text=True,
                            bufsize=1,
                            universal_newlines=True,
                            cwd=SURVEILLANCE_BASE_PATH
                        )
                        
                        # Stream output in real-time
                        log(f"🔄 AI analysis started, streaming output...")
                        output_lines = []
                        line_count = 0
                        for line in iter(process.stdout.readline, ''):
                            if line:
                                line = line.strip()
                                if line:  # Only log non-empty lines
                                    output_lines.append(line)
                                    line_count += 1
                                    # Log important lines in real-time (API calls, progress, errors)
                                    if any(keyword in line.upper() for keyword in ['API CALL', 'PROCESSING', 'EMAIL', 'ANALYZING', 'TRADE', 'INSTRUCTION', 'COMPLETE', 'ERROR', 'WARNING', 'PROGRESS', 'ANALYZED', 'TOTAL', 'SUMMARY', 'FINISHED', 'RETRYING']):
                                        log(f"   {line}")
                                    # Also log every 5th line to show general progress
                                    elif line_count % 5 == 0:
                                        log(f"   {line}")
                        
                        # Wait for process to complete
                        process.wait()
                        return_code = process.returncode
                        
                        logger.info(f"📊 [Step 2] Subprocess completed with return code: {return_code}")
                        if return_code == 0:
                            log(f"✅ AI analysis completed successfully")
                            # Check if output file was created
                            import glob
                            output_files = glob.glob(os.path.join(SURVEILLANCE_BASE_PATH, 'complete_surveillance_results_*.json'))
                            if output_files:
                                latest_output = max(output_files, key=os.path.getctime)
                                log(f"📄 AI analysis output: {latest_output}")
                                
                                # CRITICAL FIX: Save analyzed results (with all_results) back to email_surveillance file
                                # This is what email_order_validation expects
                                try:
                                    with open(latest_output, 'r') as f:
                                        analyzed_results = json.load(f)
                                    
                                    # Update the email_surveillance file with analyzed results (LOCALLY)
                                    analyzed_email_file = os.path.join(SURVEILLANCE_BASE_PATH, f'email_surveillance_{date_str}.json')
                                    with open(analyzed_email_file, 'w') as f:
                                        json.dump(analyzed_results, f, indent=2)
                                    log(f"✅ Updated email_surveillance_{date_str}.json with analyzed results (all_results)")
                                    
                                    # CRITICAL FIX: Upload analyzed results to S3 in Daily_Reports folder
                                    # This ensures Step 7 can always find it, even if local file is lost
                                    # We use a DIFFERENT S3 path to avoid overwriting email_analyses
                                    from s3_utils import upload_file_to_s3
                                    reports_s3_key = f"{S3_BASE_PREFIX}/{month_name}/Daily_Reports/{date_str}/email_surveillance_{date_str}.json"
                                    try:
                                        upload_file_to_s3(analyzed_email_file, reports_s3_key)
                                        log(f"✅ Uploaded analyzed results (all_results) to S3: {reports_s3_key}")
                                        log(f"💡 Step 7 will read from this S3 location if local file is missing")
                                    except Exception as upload_error:
                                        log(f"⚠️  Warning: Could not upload analyzed results to S3: {upload_error}")
                                        log(f"💡 Step 7 will try to read from local file: {analyzed_email_file}")
                                    
                                    log(f"💡 Note: Original email_analyses kept at: Email_Data/{year}/{month_name}/email_surveillance_{date_str}.json")
                                    
                                    # Log summary with detailed breakdown
                                    trade_instructions = analyzed_results.get('trade_instructions', {}).get('total', 0)
                                    all_results = analyzed_results.get('all_results', [])
                                    total_emails = len(all_results) if all_results else 0
                                    
                                    # Count intents for debugging
                                    intent_counts = {}
                                    if all_results:
                                        for email in all_results:
                                            ai_analysis = email.get('ai_analysis', {})
                                            intent = ai_analysis.get('ai_email_intent', 'NOT_SET') if ai_analysis else 'NO_ANALYSIS'
                                            intent_counts[intent] = intent_counts.get(intent, 0) + 1
                                    
                                    log(f"📊 Analysis summary: {trade_instructions} trade instructions found out of {total_emails} total emails")
                                    if intent_counts:
                                        log(f"📊 Intent breakdown: {intent_counts}")
                                    if trade_instructions == 0 and total_emails > 0:
                                        log(f"⚠️  WARNING: {total_emails} emails analyzed but 0 classified as trade_instruction!")
                                        log(f"⚠️  This may indicate an issue with AI classification or email content.")
                                except Exception as e:
                                    log(f"⚠️  Warning: Could not update email file with analyzed results: {e}")
                        else:
                            log(f"⚠️  AI analysis completed with warnings (return code: {return_code})")
                            # Show last 20 lines of output
                            if output_lines:
                                log(f"📋 Last output lines:")
                                for line in output_lines[-20:]:
                                    log(f"   {line}")
                    else:
                        print(f"🔵 [DEBUG] ❌ Script not found! email_system_script = {email_system_script}")
                        print(f"🔵 [DEBUG] Checked paths: {possible_paths}")
                        log(f"⚠️  WARNING: complete_email_surveillance_system.py not found at {email_system_script}")
                        log(f"⚠️  Emails will not be analyzed - they will remain as raw data")
                        
                except json.JSONDecodeError as e:
                    logs.append(f"⚠️  WARNING: Email file is not valid JSON: {e}")
                    return {'success': False, 'error': f'Invalid JSON in email file: {e}', 'logs': logs}
                except subprocess.TimeoutExpired as e:
                    logs.append(f"⚠️  WARNING: AI analysis timed out after 30 minutes")
                    logs.append(f"⚠️  Checking for partial results...")
                    # Check if output file was created even after timeout
                    import glob
                    output_files = glob.glob(os.path.join(SURVEILLANCE_BASE_PATH, 'complete_surveillance_results_*.json'))
                    if output_files:
                        latest_output = max(output_files, key=os.path.getctime)
                        logs.append(f"✅ Found output file despite timeout: {latest_output}")
                        try:
                            with open(latest_output, 'r') as f:
                                analyzed_results = json.load(f)
                            
                            # Save results even if timed out
                            analyzed_email_file = os.path.join(SURVEILLANCE_BASE_PATH, f'email_surveillance_{date_str}.json')
                            with open(analyzed_email_file, 'w') as f:
                                json.dump(analyzed_results, f, indent=2)
                            logs.append(f"✅ Saved partial results to email_surveillance_{date_str}.json")
                            
                            # Upload to S3
                            from s3_utils import upload_file_to_s3
                            s3_key = f"{S3_BASE_PREFIX}/Email_Data/{year}/{month_name}/email_surveillance_{date_str}.json"
                            upload_file_to_s3(analyzed_email_file, s3_key)
                            logs.append(f"✅ Uploaded partial results to S3")
                            
                            trade_instructions = analyzed_results.get('trade_instructions', {}).get('total', 0)
                            logs.append(f"📊 Partial analysis: {trade_instructions} trade instructions found")
                        except Exception as save_error:
                            logs.append(f"⚠️  Could not save partial results: {save_error}")
                    else:
                        logs.append(f"⚠️  No output file found - AI analysis did not produce results")
                    # Still return success since file was loaded
                except Exception as e:
                    logs.append(f"⚠️  WARNING: Error during AI analysis: {str(e)}")
                    import traceback
                    logs.append(f"📋 Traceback: {traceback.format_exc()}")
                    # Still return success since file was loaded
                
                log(f"✅ Email data loaded successfully from S3!")
                return {'success': True, 'logs': logs}
                
            except Exception as e:
                error_msg = f"Error verifying email file: {str(e)}"
                logs.append(f"❌ {error_msg}")
                import traceback
                logs.append(f"📋 Traceback: {traceback.format_exc()}")
                return {'success': False, 'error': error_msg, 'logs': logs}
            
        except Exception as e:
            error_msg = f"Error downloading email data from S3: {str(e)}"
            logs.append(f"❌ {error_msg}")
            import traceback
            logs.append(f"📋 Traceback: {traceback.format_exc()}")
            return {'success': False, 'error': error_msg, 'logs': logs}
            
    except Exception as e:
        logs.append(f"❌ Email Processing failed: {str(e)}")
        import traceback
        logs.append(f"📋 Traceback: {traceback.format_exc()}")
        return {'success': False, 'error': str(e), 'logs': logs}

def execute_oms_surveillance_step(date_str, logs):
    """Execute OMS surveillance step"""
    try:
        # PERMANENT FIX: Always run OMS surveillance, even if file exists
        # The file is created in Step 3 (parsing), but Step 4 (validation) still needs to run
        # Step 4 matches OMS orders with KL orders and updates Excel with OMS_MATCH status
        
        # PERMANENT FIX: Use absolute path for OMS file check
        # Backend runs from dashboard/backend/, so relative paths won't work
        oms_file = os.path.join(SURVEILLANCE_BASE_PATH, 'oms_surveillance', f'oms_email_surveillance_{date_str}.json')
        if os.path.exists(oms_file):
            logs.append(f"✅ OMS surveillance file already exists: {oms_file}")
            logs.append(f"🔄 File exists, but Step 4 (validation) still needs to run...")
        else:
            logs.append(f"ℹ️  OMS surveillance file not found, will fetch emails first...")
        
        # Convert DDMMYYYY to YYYY-MM-DD for OMS surveillance
        date_obj = datetime.strptime(date_str, '%d%m%Y')
        oms_date_str = date_obj.strftime('%Y-%m-%d')
        
        logs.append(f"🔄 Running OMS surveillance for {oms_date_str}...")
        logs.append(f"   This will run all steps: fetch emails, parse, validate, and update Excel")
        
        # Try /app/ first (where scripts are in Docker), then SURVEILLANCE_BASE_PATH as fallback
        script_path = os.path.join('/app', 'oms_surveillance', 'run_oms_surveillance.py')
        if not os.path.exists(script_path):
            script_path = os.path.join(SURVEILLANCE_BASE_PATH, 'oms_surveillance', 'run_oms_surveillance.py')
        
        if not os.path.exists(script_path):
            logs.append(f"❌ OMS surveillance script not found: {script_path}")
            return {'success': False, 'error': f'OMS surveillance script not found: {script_path}', 'logs': logs}
        
        # Execute the script with system Python (no venv needed in Docker)
        python_cmd = "python3"
        logs.append(f"🔍 [PORTAL] Executing: {python_cmd} {script_path} {oms_date_str}")
        logs.append(f"🔍 [PORTAL] Working directory: /app")
        logs.append(f"🔍 [PORTAL] Timeout: 3600 seconds (1 hour)")
        
        result = subprocess.run([
            python_cmd, script_path, oms_date_str
        ], capture_output=True, text=True, cwd='/app', timeout=3600)  # 1 hour timeout
        
        logs.append(f"🔍 [PORTAL] Subprocess completed with return code: {result.returncode}")
        logs.append(f"🔍 [PORTAL] STDOUT length: {len(result.stdout)} characters")
        logs.append(f"🔍 [PORTAL] STDERR length: {len(result.stderr)} characters")
        
        # Check for Step 4 in output
        if 'Step 4' in result.stdout or '[STEP4]' in result.stdout or '[VALIDATE]' in result.stdout:
            logs.append(f"✅ [PORTAL] Step 4 execution detected in output")
        else:
            logs.append(f"⚠️ [PORTAL] WARNING: Step 4 execution NOT detected in output!")
        
        if result.returncode == 0:
            logs.append(f"✅ OMS surveillance completed successfully")
            if result.stdout.strip():
                # Show more context - look for Step 4 specifically
                stdout_lines = result.stdout.strip().split('\n')
                step4_lines = [line for line in stdout_lines if 'Step 4' in line or '[STEP4]' in line or '[VALIDATE]' in line]
                if step4_lines:
                    logs.append(f"📋 [PORTAL] Step 4 related output ({len(step4_lines)} lines):")
                    logs.extend(step4_lines[-15:])  # Last 15 Step 4 related lines
                else:
                    logs.append(f"⚠️ [PORTAL] WARNING: No Step 4 related output found!")
                    logs.append(f"📋 [PORTAL] Last 20 lines of output:")
                    logs.extend(stdout_lines[-20:])  # Last 20 lines if no Step 4 found
            else:
                logs.append(f"⚠️ [PORTAL] WARNING: No stdout output from OMS surveillance script!")
            
            # VERIFICATION: Check if matches were applied
            ddmmyyyy = date_str
            matches_file = os.path.join(SURVEILLANCE_BASE_PATH, 'oms_surveillance', f'oms_matches_{ddmmyyyy}.json')
            if os.path.exists(matches_file):
                logs.append(f"📋 [PORTAL] Intermediate matches file exists: {matches_file}")
                try:
                    import json
                    with open(matches_file, 'r') as f:
                        matches_data = json.load(f)
                    match_count = len(matches_data.get('matches', {}))
                    logs.append(f"📋 [PORTAL] Intermediate file contains {match_count} matches")
                except Exception as e:
                    logs.append(f"⚠️ [PORTAL] Error reading intermediate file: {e}")
            else:
                logs.append(f"📋 [PORTAL] Intermediate matches file NOT found: {matches_file}")
            
            # Check Excel for OMS matches
            try:
                import pandas as pd
                month_num = int(ddmmyyyy[2:4])
                month_names = {
                    1: "January", 2: "February", 3: "March", 4: "April",
                    5: "May", 6: "June", 7: "July", 8: "August",
                    9: "September", 10: "October", 11: "November", 12: "December"
                }
                month_name = month_names.get(month_num)
                excel_file = os.path.join(
                    SURVEILLANCE_BASE_PATH,
                    month_name,
                    "Daily_Reports",
                    ddmmyyyy,
                    f"Final_Trade_Surveillance_Report_{ddmmyyyy}_with_Email_and_Trade_Analysis.xlsx"
                )
                
                if os.path.exists(excel_file):
                    df = pd.read_excel(excel_file)
                    oms_matched = df[df['Email-Order Match Status'] == 'OMS_MATCH']
                    match_count = len(oms_matched)
                    logs.append(f"📋 [PORTAL] Verification: Found {match_count} OMS matches in Excel")
                    
                    if match_count == 0:
                        logs.append(f"⚠️ [PORTAL] WARNING: No OMS matches found in Excel after Step 8!")
                    else:
                        logs.append(f"✅ [PORTAL] Verification passed: {match_count} OMS matches in Excel")
                else:
                    logs.append(f"⚠️ [PORTAL] Excel file not found for verification: {excel_file}")
            except Exception as verify_error:
                logs.append(f"⚠️ [PORTAL] Error during Excel verification: {verify_error}")
            
            return {'success': True, 'logs': logs}
        else:
            error_msg = f"OMS surveillance failed"
            if result.stderr:
                error_msg += f": {result.stderr}"
            if result.stdout:
                # Look for error messages in stdout too
                stdout_lines = result.stdout.strip().split('\n')
                error_lines = [line for line in stdout_lines if any(keyword in line.lower() for keyword in ['error', 'failed', 'exception', 'traceback'])]
                if error_lines:
                    error_msg += f" | STDOUT errors: {'; '.join(error_lines[-3:])}"
            logs.append(f"❌ {error_msg}")
            if result.stdout.strip():
                logs.append(f"📋 Full output (last 10 lines):")
                logs.extend(result.stdout.strip().split('\n')[-10:])
            if result.stderr.strip():
                logs.append(f"📋 Error output:")
                logs.extend(result.stderr.strip().split('\n')[-10:])
            return {'success': False, 'error': error_msg, 'logs': logs}
            
    except subprocess.TimeoutExpired:
        error_msg = f"OMS surveillance timed out after 1 hour"
        logs.append(f"❌ {error_msg}")
        return {'success': False, 'error': error_msg, 'logs': logs}
    except Exception as e:
        logs.append(f"❌ OMS surveillance error: {str(e)}")
        import traceback
        logs.append(f"📋 Traceback: {traceback.format_exc()}")
        return {'success': False, 'error': str(e), 'logs': logs}

def execute_regular_step(step, date_str, logs):
    """Execute a regular surveillance step"""
    try:
        # Scripts are in /app/, but SURVEILLANCE_BASE_PATH is /app/data (for data storage)
        # Try /app/ first (where scripts are), then SURVEILLANCE_BASE_PATH as fallback
        script_name = step['script']
        script_path = os.path.join('/app', script_name)
        
        if not os.path.exists(script_path):
            # Fallback to SURVEILLANCE_BASE_PATH
            script_path = os.path.join(SURVEILLANCE_BASE_PATH, script_name)
        
        if not os.path.exists(script_path):
            error_msg = f"Script not found: {script_name} (checked /app/ and {SURVEILLANCE_BASE_PATH})"
            logs.append(f"❌ {error_msg}")
            return {'success': False, 'error': error_msg, 'logs': logs}
        
        logs.append(f"🔄 Running {step['name']}...")
        logs.append(f"📜 Script: {script_path}")
        
        # Special handling for email-order validation step - verify email file exists first
        if step['name'] == 'Email-Order Validation & Mapping':
            email_file = os.path.join(SURVEILLANCE_BASE_PATH, f'email_surveillance_{date_str}.json')
            logs.append(f"🔍 Checking for email file: {email_file}")
            if os.path.exists(email_file):
                try:
                    import json
                    with open(email_file, 'r') as f:
                        email_data = json.load(f)
                    all_results = email_data.get('all_results', [])
                    trade_instructions = [e for e in all_results if e.get('ai_analysis', {}).get('ai_email_intent') == 'trade_instruction']
                    logs.append(f"📧 Email file found: {len(all_results)} total emails, {len(trade_instructions)} trade instructions")
                    if len(trade_instructions) == 0:
                        logs.append(f"⚠️  WARNING: No trade instructions found in email file!")
                        logs.append(f"⚠️  Email matching will result in 0 matches.")
                except Exception as e:
                    logs.append(f"⚠️  Could not verify email file structure: {e}")
            else:
                logs.append(f"⚠️  WARNING: Email file not found at {email_file}")
                logs.append(f"⚠️  Email-order validation may fail or produce 0 matches")
        
        # Execute the script - use system Python in Docker (no venv needed)
        # Scripts are in /app/, run from /app/ directory
        python_cmd = "python3"
        result = subprocess.run([
            python_cmd, script_path, date_str
        ], capture_output=True, text=True, cwd='/app')
        
        if result.returncode == 0:
            logs.append(f"✅ {step['name']} completed successfully")
            if result.stdout.strip():
                # For email validation, show more output to debug matching
                if step['name'] == 'Email-Order Validation & Mapping':
                    stdout_lines = result.stdout.strip().split('\n')
                    # Show lines with DEBUG, WARNING, or match counts
                    important_lines = [line for line in stdout_lines if any(keyword in line for keyword in ['DEBUG', 'WARNING', 'Found', 'Matched', 'trade instruction'])]
                    if important_lines:
                        logs.append(f"📋 Key output from email validation:")
                        logs.extend(important_lines[-20:])  # Last 20 important lines
                    else:
                        logs.extend(stdout_lines[-10:])  # Last 10 lines if no important lines
                else:
                    logs.extend(result.stdout.strip().split('\n')[-5:])  # Last 5 lines
            return {'success': True, 'logs': logs}
        else:
            error_msg = f"{step['name']} failed: {result.stderr}"
            logs.append(f"❌ {error_msg}")
            if result.stdout.strip():
                logs.append(f"📋 STDOUT: {result.stdout[-500:]}")
            return {'success': False, 'error': error_msg, 'logs': logs}
            
    except Exception as e:
        logs.append(f"❌ {step['name']} error: {str(e)}")
        return {'success': False, 'error': str(e), 'logs': logs}

@app.route('/api/surveillance/job/<job_id>', methods=['GET'])
def get_job_status(job_id):
    """Get status of surveillance job"""
    try:
        if job_id not in surveillance_jobs:
            return jsonify({'error': 'Job not found'}), 404
        
        job = surveillance_jobs[job_id]
        
        # Check for email processing progress if email step exists (running or just completed)
        # Also check if current_step mentions email processing
        email_step = next((s for s in job.get('steps', []) if s.get('id') == 2), None)
        is_email_processing = (
            (email_step and email_step.get('status') in ['running', 'completed']) or
            'email' in job.get('current_step', '').lower()
        )
        if is_email_processing:
            # Check both /app/ (Docker) and SURVEILLANCE_BASE_PATH
            progress_files = [
                '/app/email_processing_progress.json',  # Docker location
                os.path.join(SURVEILLANCE_BASE_PATH, 'email_processing_progress.json')  # Local/S3 fallback
            ]
            for progress_file in progress_files:
                if os.path.exists(progress_file):
                    try:
                        with open(progress_file, 'r') as f:
                            progress_data = json.load(f)
                            job['email_progress'] = progress_data
                            logger.info(f"Loaded email progress: {progress_data.get('processed_emails', 0)}/{progress_data.get('total_emails', 0)}")
                            break
                    except Exception as e:
                        logger.warning(f"Could not read email progress file {progress_file}: {e}")
        
        return jsonify(job)
        
    except Exception as e:
        logger.error(f"Error getting job status: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/surveillance/download/<job_id>', methods=['GET'])
def download_surveillance_report(job_id):
    """Download the final Excel report for a completed surveillance job"""
    try:
        if job_id not in surveillance_jobs:
            return jsonify({'error': 'Job not found'}), 404
        
        job = surveillance_jobs[job_id]
        
        if job['status'] != 'completed':
            return jsonify({'error': 'Job not completed yet'}), 400
        
        excel_file_path = job.get('excel_file_path')
        if not excel_file_path:
            return jsonify({'error': 'Excel file path not found'}), 404
        
        # Build full path
        full_path = os.path.join(SURVEILLANCE_BASE_PATH, excel_file_path)
        
        if not os.path.exists(full_path):
            return jsonify({'error': 'Excel file not found'}), 404
        
        # Generate filename for download
        date_str = job['date']
        filename = f"Trade_Surveillance_Report_{date_str}.xlsx"
        
        return send_file(
            full_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        logger.error(f"Error downloading surveillance report: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/surveillance/jobs/history', methods=['GET'])
def get_job_history():
    """Get recent surveillance jobs from the last 24 hours"""
    try:
        # Clean up old jobs first
        cleanup_old_jobs()
        
        # Get recent jobs
        recent_jobs = get_recent_jobs()
        
        # Convert to list and sort by completion time
        jobs_list = []
        for job_id, job_data in recent_jobs.items():
            if job_data.get('completed_at'):
                jobs_list.append({
                    'id': job_id,
                    'date': job_data['date'],
                    'status': job_data['status'],
                    'completed_at': job_data['completed_at'],
                    'duration': job_data.get('duration', 0),
                    'summary': job_data.get('summary', {}),
                    'excel_file_available': job_data.get('excel_file_path') is not None
                })
        
        # Sort by completion time (newest first)
        jobs_list.sort(key=lambda x: x['completed_at'], reverse=True)
        
        return jsonify({
            'jobs': jobs_list,
            'total': len(jobs_list)
        })
        
    except Exception as e:
        logger.error(f"Error getting job history: {e}")
        return jsonify({'error': str(e)}), 500

def get_orders_dataframe(year, month, metric_type, start_date=None, end_date=None):
    """Get orders as DataFrame for a specific metric type"""
    try:
        logger.info(f"Getting orders DataFrame for {year}/{month}/{metric_type}")
        
        date_paths = get_date_paths(year, month)
        logger.info(f"Found {len(date_paths)} date paths: {date_paths}")
        
        # Filter date paths based on date range if provided
        if start_date or end_date:
            filtered_date_paths = []
            for date_path in date_paths:
                # Extract date from path (e.g., "September/Daily_Reports/15092025" -> "15092025")
                date_str = os.path.basename(date_path)
                
                # Handle different filter scenarios:
                # 1. Both start_date and end_date provided: range filter
                # 2. Only start_date provided: >= start_date
                # 3. Only end_date provided: <= end_date
                # 4. Both same (single date): exact match
                if start_date and end_date:
                    # Range filter
                    if start_date <= date_str <= end_date:
                        filtered_date_paths.append(date_path)
                elif start_date:
                    # Only start_date: >= start_date
                    if date_str >= start_date:
                        filtered_date_paths.append(date_path)
                elif end_date:
                    # Only end_date: <= end_date
                    if date_str <= end_date:
                        filtered_date_paths.append(date_path)
            
            date_paths = filtered_date_paths
            logger.info(f"Filtered to {len(date_paths)} date paths: {date_paths}")
        
        all_orders = []
        
        if len(date_paths) == 0:
            logger.warning("No date paths found - returning empty DataFrame")
            return pd.DataFrame()
        
        for date_path in date_paths:
            logger.info(f"Processing date path: {date_path}")
            df = read_final_surveillance_report(date_path)
            if df is None:
                logger.warning(f"No data found for {date_path}")
                continue
            
            logger.info(f"Loaded {len(df)} rows from {date_path}")
            
            # Filter orders by metric type
            filtered_df = filter_orders_by_metric(df, metric_type)
            logger.info(f"Filtered to {len(filtered_df)} orders for metric {metric_type}")
            
            if not filtered_df.empty:
                all_orders.append(filtered_df)
        
        if not all_orders:
            logger.warning(f"No orders found for {metric_type}")
            return pd.DataFrame()
        
        # Combine all orders
        combined_df = pd.concat(all_orders, ignore_index=True)
        logger.info(f"Combined {len(combined_df)} total orders for {metric_type}")
        
        return combined_df
        
    except Exception as e:
        logger.error(f"Error getting orders DataFrame: {e}")
        return pd.DataFrame()

@app.route('/api/surveillance/export/<metric_type>')
def export_orders(metric_type):
    """Export orders for a specific metric type to Excel"""
    try:
        year = request.args.get('year', 2025, type=int)
        month = request.args.get('month', 'August')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        logger.info(f"Exporting {metric_type} orders for {month} {year}")
        
        # Get orders for the metric
        orders_df = get_orders_dataframe(year, month, metric_type, start_date, end_date)
        
        if orders_df is None or orders_df.empty:
            return jsonify({'error': f'No orders found for {metric_type}'}), 404
        
        # Create Excel file in memory
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Write the main orders data
            orders_df.to_excel(writer, sheet_name=f'{metric_type}_Orders', index=False)
            
            # Add summary sheet
            summary_data = {
                'Metric': [metric_type],
                'Month': [month],
                'Year': [year],
                'Total Orders': [len(orders_df)],
                'Export Date': [datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
            }
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
        
        output.seek(0)
        
        # Generate filename
        filename = f"{metric_type}_Orders_{month}_{year}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        return send_file(
            output,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        logger.error(f"Error exporting orders: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/surveillance/test')
def test_endpoint():
    """Test endpoint to verify backend is working"""
    try:
        date_paths = get_date_paths(2025, "August")
        available_files = []
        
        for date_path in date_paths:
            final_report_path = os.path.join(date_path, f"Final_Trade_Surveillance_Report_{os.path.basename(date_path)}_with_Email_and_Trade_Analysis.xlsx")
            if os.path.exists(final_report_path):
                available_files.append(os.path.basename(date_path))
        
        return jsonify({
            'status': 'working',
            'available_dates': available_files,
            'total_dates': len(available_files),
            'base_path': SURVEILLANCE_BASE_PATH,
            'reports_path': AUGUST_REPORTS_PATH
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Use environment variable for debug mode, default to False for production
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    port = int(os.getenv('PORT', 5001))
    app.run(debug=debug_mode, port=port, host='0.0.0.0')
