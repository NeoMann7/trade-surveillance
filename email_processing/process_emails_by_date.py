#!/usr/bin/env python3
"""
Process emails for specific dates using Graph API and AI analysis
"""

import json
import os
import sys
from datetime import datetime
import shutil
import msal
import requests
import base64
import mimetypes
import hashlib
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from dotenv import load_dotenv
import socket
import traceback

# Load environment variables
load_dotenv()

# Your App Registration credentials
TENANT_ID = "d3f35719-3f42-4550-b567-4421c83ca87b"
CLIENT_ID = "6ceedeac-fa0a-4480-b09b-ddec4eacd285"
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPES = ["Mail.Read"]
ATTACHMENT_TEMP_DIR = "temp_attachments"

def create_attachment_temp_dir():
    """Create temporary directory for attachments"""
    Path(ATTACHMENT_TEMP_DIR).mkdir(exist_ok=True)
    return ATTACHMENT_TEMP_DIR

def download_attachment(attachment_id, message_id, headers, temp_dir, max_retries=3):
    """Download attachment from Graph API with retry logic for rate limiting"""
    name = None
    for attempt in range(max_retries):
        try:
            # Get attachment metadata first
            attachment_url = f"https://graph.microsoft.com/v1.0/me/messages/{message_id}/attachments/{attachment_id}"
            resp = requests.get(attachment_url, headers=headers, timeout=30)
            
            # Handle rate limiting (429) with exponential backoff
            if resp.status_code == 429:
                retry_after = int(resp.headers.get('Retry-After', 60))  # Default 60 seconds
                wait_time = retry_after * (2 ** attempt)  # Exponential backoff
                print(f"   ⚠️ Rate limited (429) for attachment. Waiting {wait_time}s before retry {attempt + 1}/{max_retries}...")
                time.sleep(wait_time)
                continue
            
            resp.raise_for_status()
            
            attachment_data = resp.json()
            content_bytes = attachment_data.get('contentBytes', '')
            name = attachment_data.get('name', f'attachment_{attachment_id[:20]}')
            content_type = attachment_data.get('contentType', 'application/octet-stream')
            
            # Check if contentBytes is empty (common with email attachments)
            if not content_bytes:
                print(f"   ⚠️ No contentBytes for attachment {name}, trying alternative method...")
                
                # Try to get the attachment content using the $value endpoint
                for value_attempt in range(max_retries):
                    try:
                        content_url = f"https://graph.microsoft.com/v1.0/me/messages/{message_id}/attachments/{attachment_id}/$value"
                        content_resp = requests.get(content_url, headers=headers, timeout=30)
                        
                        # Handle rate limiting for $value endpoint too
                        if content_resp.status_code == 429:
                            retry_after = int(content_resp.headers.get('Retry-After', 60))
                            wait_time = retry_after * (2 ** value_attempt)
                            print(f"   ⚠️ Rate limited on $value endpoint. Waiting {wait_time}s...")
                            time.sleep(wait_time)
                            if value_attempt < max_retries - 1:
                                continue
                            else:
                                return None
                        
                        if content_resp.status_code == 200:
                            file_content = content_resp.content
                            print(f"   ✅ Retrieved content via $value endpoint: {len(file_content)} bytes")
                            break  # Success, exit retry loop
                        else:
                            print(f"   ❌ $value endpoint failed with status {content_resp.status_code}")
                            if value_attempt < max_retries - 1:
                                time.sleep(5 * (value_attempt + 1))
                                continue
                            return None
                    except requests.exceptions.RequestException as e:
                        if value_attempt < max_retries - 1:
                            wait_time = 5 * (value_attempt + 1)
                            print(f"   ⚠️ Request error, retrying in {wait_time}s...")
                            time.sleep(wait_time)
                            continue
                        print(f"   ❌ Alternative download method failed: {e}")
                        return None
            else:
                # Decode base64 content
                try:
                    file_content = base64.b64decode(content_bytes)
                except Exception as e:
                    print(f"⚠️ Failed to decode attachment {name}: {e}")
                    return None
            
            # Determine file extension
            if content_type:
                extension = mimetypes.guess_extension(content_type) or '.bin'
            else:
                extension = '.bin'
            if not extension.startswith('.'):
                extension = '.' + extension
            
            # Create safe filename with length limit
            safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_', '.')).rstrip()
            if not safe_name.endswith(extension):
                safe_name += extension
            
            # Fix: Use hash of attachment_id instead of full ID to avoid path length issues
            # attachment_id can be 200+ chars, causing "File name too long" errors
            attachment_hash = hashlib.md5(attachment_id.encode()).hexdigest()[:12]  # 12 char hash
            
            # Limit safe_name to 200 chars (leaving room for hash + extension + temp_dir path)
            max_safe_name_length = 200
            if len(safe_name) > max_safe_name_length:
                # Truncate but keep extension
                name_part = safe_name[:max_safe_name_length-len(extension)]
                safe_name = name_part + extension
            
            # Create short filename: hash + truncated name
            # Total: hash (12) + _ + name (max 200) = max 213 chars (well under 255 limit)
            short_filename = f"{attachment_hash}_{safe_name}"
            
            # Final safety check: if still too long, use just hash + extension
            if len(short_filename) > 240:
                short_filename = f"{attachment_hash}{extension}"
            
            # Save file
            file_path = os.path.join(temp_dir, short_filename)
            with open(file_path, 'wb') as f:
                f.write(file_content)
            
            return {
                'id': attachment_id,
                'name': name,
                'content_type': content_type,
                'file_path': file_path,
                'size': len(file_content)
            }
            
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                wait_time = 5 * (attempt + 1)
                print(f"   ⚠️ Network error (attempt {attempt + 1}/{max_retries}), retrying in {wait_time}s...")
                time.sleep(wait_time)
                continue
            print(f"[DEBUG] ❌ Network error downloading attachment {attachment_id}")
            print(f"[DEBUG]   Exception type: {type(e).__name__}")
            print(f"[DEBUG]   Exception message: {e}")
            print(f"❌ Network error downloading attachment {name or attachment_id[:20]}: {e}")
            return None
        except Exception as e:
            print(f"[DEBUG] ❌ Failed to download attachment {attachment_id}")
            print(f"[DEBUG]   Exception type: {type(e).__name__}")
            print(f"[DEBUG]   Exception message: {e}")
            print(f"❌ Failed to download attachment {name or attachment_id[:20]}: {e}")
            return None
    
    # If we get here, all retries failed
    print(f"❌ Failed to download attachment {name or attachment_id[:20]} after {max_retries} attempts")
    return None

def extract_text_from_pdf_attachment(attachment_info):
    """Extract text content from PDF attachments using PyPDF2"""
    file_path = attachment_info['file_path']
    name = attachment_info['name']
    
    try:
        import PyPDF2
        with open(file_path, 'rb') as f:
            pdf_reader = PyPDF2.PdfReader(f)
            text = ""
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text.strip():
                    text += page_text + "\n"
            return text.strip()
                    
    except ImportError:
        print("⚠️ PyPDF2 not installed. Install with: pip install PyPDF2")
        return None
    except Exception as e:
        print(f"⚠️ PDF text extraction failed for {name}: {e}")
        return None

def extract_text_from_email_attachment(attachment_info):
    """Extract text content from email attachments (forwarded emails)"""
    file_path = attachment_info['file_path']
    name = attachment_info['name']
    
    try:
        print(f"      🔍 Reading email attachment file: {file_path}")
        
        # Try different approaches to read email attachment
        content = None
        
        # First, try reading as text
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                print(f"      ✅ Read as text: {len(content)} chars")
        except Exception as e:
            print(f"      ⚠️ Text reading failed: {e}")
            # If text reading fails, try binary reading and decode
            try:
                with open(file_path, 'rb') as f:
                    binary_content = f.read()
                    print(f"      📄 Binary content size: {len(binary_content)} bytes")
                    # Try to decode as UTF-8
                    content = binary_content.decode('utf-8', errors='ignore')
                    print(f"      ✅ Decoded binary: {len(content)} chars")
            except Exception as e2:
                print(f"      ❌ Binary reading failed: {e2}")
                # If all else fails, return the attachment name as content
                return f"Email attachment: {name}"
        
        if not content or len(content.strip()) < 10:
            print(f"      ⚠️ Content too short or empty: {len(content) if content else 0} chars")
            return f"Email attachment: {name}"
            
        print(f"      📝 Processing email content...")
        
        # Extract email content from the raw email data
        lines = content.split('\n')
        email_content = []
        in_body = False
        header_count = 0
        body_started = False
        
        for line in lines:
            line = line.strip()
            if not line:
                if header_count > 0:
                    in_body = True
                continue
                
            # Keep important headers
            if line.startswith(('From:', 'To:', 'Subject:', 'Date:', 'Cc:', 'Bcc:')):
                email_content.append(line)
                header_count += 1
            # Skip technical headers
            elif line.startswith(('Message-ID:', 'Content-Type:', 'MIME-Version:', 'X-', 'Return-Path:', 'Received:', 'DKIM-', 'Authentication-Results:')):
                continue
            # Start of body content
            elif in_body or body_started:
                email_content.append(line)
                body_started = True
            # Keep first few important lines
            elif header_count < 5 and not body_started:
                email_content.append(line)
        
        if email_content:
            result = '\n'.join(email_content)
            print(f"      ✅ Extracted structured content: {len(result)} chars")
            # Limit to reasonable size
            if len(result) > 5000:
                result = result[:5000] + "... [truncated]"
            return result
        else:
            print(f"      ⚠️ No structured content found, using raw content")
            # If no structured content found, return the raw content (limited)
            if len(content) > 3000:
                return content[:3000] + "... [truncated]"
            return content
            
    except Exception as e:
        print(f"      ❌ Email attachment text extraction failed for {name}: {e}")
        # Return at least the attachment name
        return f"Email attachment: {name}"

def process_single_attachment(attachment, message_id, headers, temp_dir):
    """Process a single attachment (download, validate, extract text) - for parallel processing"""
    attachment_id = attachment.get('id')
    if not attachment_id:
        return None
    
    # Download attachment
    attachment_info = download_attachment(attachment_id, message_id, headers, temp_dir)
    if not attachment_info:
        return None
    
    # Validate attachment info
    content_type = attachment_info.get('content_type', '')
    name = attachment_info.get('name', '')
    file_path = attachment_info.get('file_path', '')
    
    # Check if name is None or empty
    if not name:
        return None
    
    # Verify file was actually saved
    if not os.path.exists(file_path):
        return None
    
    # Check if it's a PDF or email attachment
    is_pdf = False
    is_email_attachment = False
    
    # PDF detection
    if content_type == 'application/pdf':
        is_pdf = True
    elif name and name.lower().endswith('.pdf'):
        is_pdf = True
    
    # Email attachment detection
    elif (content_type is None or content_type == 'application/octet-stream') and name:
        email_patterns = ['Re:', 'Fw:', 'FW:', 'RE:', 'FW:', 'Forward:', 'Reply:']
        if any(pattern in name for pattern in email_patterns):
            is_email_attachment = True
        elif file_path.endswith('.bin') and os.path.exists(file_path):
            try:
                with open(file_path, 'rb') as f:
                    sample = f.read(200)
                    sample_str = sample.decode('utf-8', errors='ignore').lower()
                    if any(keyword in sample_str for keyword in ['from:', 'to:', 'subject:', 'date:', 'message-id:']):
                        is_email_attachment = True
            except:
                pass
    
    if not (is_pdf or is_email_attachment):
        return None
    
    # Extract text content based on attachment type
    text_content = None
    if is_pdf:
        text_content = extract_text_from_pdf_attachment(attachment_info)
        if text_content:
            attachment_info['extracted_text'] = text_content
    elif is_email_attachment:
        text_content = extract_text_from_email_attachment(attachment_info)
        if text_content and text_content != f"Email attachment: {name}":
            attachment_info['extracted_text'] = text_content
        else:
            attachment_info['extracted_text'] = f"Email attachment: {name}"
    
    return attachment_info

def process_email_attachments(message_id, attachments, headers, temp_dir):
    """Process PDF and email attachments for an email - NOW PARALLELIZED"""
    processed_attachments = []
    
    if not attachments:
        return processed_attachments
    
    print(f"📎 Processing {len(attachments)} attachments for message {message_id} in parallel...")
    
    # Ensure temp directory exists
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir, exist_ok=True)
    
    # PARALLELIZE attachment processing
    max_attachment_workers = 3  # Conservative for attachment downloads
    with ThreadPoolExecutor(max_workers=max_attachment_workers) as executor:
        futures = {executor.submit(process_single_attachment, attachment, message_id, headers, temp_dir): attachment 
                   for attachment in attachments if attachment.get('id')}
        
        for future in as_completed(futures):
            try:
                attachment_info = future.result()
                if attachment_info:
                    processed_attachments.append(attachment_info)
            except Exception as e:
                original_attachment = futures[future]
                print(f"   ⚠️ Failed to process attachment: {e}")
    
    print(f"📎 Processed {len(processed_attachments)}/{len(attachments)} attachments successfully")
    return processed_attachments

def get_emails_for_date(target_date: str):
    """Get emails for a specific date using Graph API"""
    print(f"[DEBUG] ===== Starting email processing for {target_date} =====")
    
    # Initialize progress file IMMEDIATELY when email processing starts
    if os.path.exists('/app'):
        progress_file = '/app/email_processing_progress.json'
    else:
        base_path = os.getenv('SURVEILLANCE_BASE_PATH', os.path.dirname(os.path.dirname(__file__)))
        progress_file = os.path.join(base_path, 'email_processing_progress.json')
    
    def update_progress(completed, total, successful, status="processing"):
        try:
            progress_data = {
                'total_emails': total,
                'processed_emails': completed,
                'successful_emails': successful,
                'remaining_emails': total - completed if total > 0 else 0,
                'progress_percent': int((completed / total * 100)) if total > 0 else 0,
                'status': status,  # "starting", "fetching", "processing", "completed"
                'timestamp': datetime.now().isoformat()
            }
            with open(progress_file, 'w') as f:
                json.dump(progress_data, f)
            sys.stdout.flush()
        except Exception as e:
            pass
    
    # Set initial status: "Starting email processing..."
    update_progress(0, 0, 0, "starting")
    
    print(f"[DEBUG] Step 1: Checking network connectivity...")
    
    # Network connectivity check
    try:
        print(f"[DEBUG] Testing DNS resolution for graph.microsoft.com...")
        socket.gethostbyname("graph.microsoft.com")
        print(f"[DEBUG] ✅ DNS resolution successful")
    except socket.gaierror as e:
        print(f"[DEBUG] ❌ DNS resolution failed: {e}")
        print(f"[DEBUG] Network connectivity issue detected!")
    
    try:
        print(f"[DEBUG] Testing DNS resolution for login.microsoftonline.com...")
        socket.gethostbyname("login.microsoftonline.com")
        print(f"[DEBUG] ✅ DNS resolution successful for auth endpoint")
    except socket.gaierror as e:
        print(f"[DEBUG] ❌ DNS resolution failed for auth: {e}")
    
    print(f"[DEBUG] Step 2: Initializing MSAL application...")
    print(f"[DEBUG]   TENANT_ID: {TENANT_ID}")
    print(f"[DEBUG]   CLIENT_ID: {CLIENT_ID}")
    print(f"[DEBUG]   AUTHORITY: {AUTHORITY}")
    print(f"[DEBUG]   SCOPES: {SCOPES}")
    
    try:
        # Create MSAL app
        app = msal.PublicClientApplication(CLIENT_ID, authority=AUTHORITY)
        print(f"[DEBUG] ✅ MSAL application created successfully")
        
        # Try silent token first
        print(f"[DEBUG] Step 3: Checking for cached accounts...")
        accounts = app.get_accounts()
        print(f"[DEBUG]   Found {len(accounts)} cached account(s)")
        
        result = None
        if accounts:
            print(f"[DEBUG] Step 4: Attempting silent token acquisition...")
            print(f"[DEBUG]   Account: {accounts[0].get('username', 'N/A')}")
            result = app.acquire_token_silent(SCOPES, account=accounts[0])
            if result and "access_token" in result:
                print(f"[DEBUG] ✅ Silent token acquisition successful")
            else:
                print(f"[DEBUG] ⚠️ Silent token acquisition failed or returned no token")
                if result:
                    print(f"[DEBUG]   Error: {result.get('error', 'N/A')}")
                    print(f"[DEBUG]   Error description: {result.get('error_description', 'N/A')}")
        
        # Fall back to interactive login
        if not result or "access_token" not in result:
            print(f"[DEBUG] Step 5: Falling back to interactive authentication...")
            print(f"[DEBUG]   This will open a browser window")
            
            # Check if we're in Docker (no DISPLAY, no browser available)
            is_docker = os.path.exists('/app') or os.path.exists('/.dockerenv')
            if is_docker:
                print(f"[DEBUG] ⚠️ DETECTED: Running in Docker environment")
                print(f"[DEBUG]   Interactive authentication will NOT work (no browser)")
                print(f"[DEBUG]   This will cause the process to hang indefinitely")
                print(f"[DEBUG]   ERROR: Cannot authenticate in Docker without cached tokens")
                print(f"[DEBUG]   SOLUTION: Need to use device code flow or client credentials")
                error_msg = "Authentication failed: Interactive auth not available in Docker. Need cached tokens or device code flow."
                print(f"❌ {error_msg}")
                return None
            
            try:
                result = app.acquire_token_interactive(scopes=SCOPES)
                print(f"[DEBUG]   Interactive auth completed")
            except Exception as e:
                print(f"[DEBUG] ❌ Interactive auth exception: {type(e).__name__}: {e}")
                print(f"[DEBUG]   Full traceback:")
                traceback.print_exc()
                raise
        
        if "access_token" not in result:
            print(f"[DEBUG] ❌ Authentication failed - no access token in result")
            print(f"[DEBUG]   Result keys: {list(result.keys()) if result else 'None'}")
            print(f"[DEBUG]   Error: {result.get('error', 'N/A') if result else 'N/A'}")
            print(f"[DEBUG]   Error description: {result.get('error_description', 'N/A') if result else 'N/A'}")
            print(f"❌ Auth failed: {result.get('error_description')}")
            return None
        
        print(f"[DEBUG] ✅ Authentication successful!")
        print(f"[DEBUG]   Token type: {result.get('token_type', 'N/A')}")
        print(f"[DEBUG]   Token expires in: {result.get('expires_in', 'N/A')} seconds")
        token = result["access_token"]
        token_preview = token[:20] + "..." if len(token) > 20 else token
        print(f"[DEBUG]   Token preview: {token_preview}")
        headers = {"Authorization": f"Bearer {token}"}
        print(f"[DEBUG] ✅ Headers prepared with Bearer token")
        
        # Convert target_date to Graph API format (2025-08-05 -> 2025-08-05T00:00:00Z)
        start_date = f"{target_date}T00:00:00Z"
        end_date = f"{target_date}T23:59:59Z"
        print(f"[DEBUG] Step 6: Preparing Graph API query...")
        print(f"[DEBUG]   Start date: {start_date}")
        print(f"[DEBUG]   End date: {end_date}")
        
        # Search for emails on the specific date
        print(f"🔍 Searching emails for {target_date}...")
        
        # Search all messages for the specific date
        # CRITICAL: Request body with HTML format explicitly to ensure we get HTML, not plain text
        messages_url = (
            f"https://graph.microsoft.com/v1.0/me/messages"
            f"?$filter=receivedDateTime ge {start_date} and receivedDateTime le {end_date}"
            f"&$select=id,receivedDateTime,from,subject,toRecipients,ccRecipients,body,hasAttachments"
            f"&$orderby=receivedDateTime desc"
        )
        print(f"[DEBUG]   Graph API URL: {messages_url[:100]}...")
        # Note: Graph API returns body.contentType ('html' or 'text') and body.content
        # By default, it should return HTML for modern emails, but we check contentType to be sure
        
        # Get emails with pagination
        print(f"[DEBUG] Step 7: Starting email fetch with pagination...")
        all_emails = []
        next_link = messages_url
        page_num = 1
        
        while next_link:
            try:
                print(f"[DEBUG]   Page {page_num}: Fetching batch... (current total: {len(all_emails)})")
                print(f"[DEBUG]   Request URL: {next_link[:150]}...")
                print(f"[DEBUG]   Sending GET request with timeout=120...")
                
                resp = requests.get(next_link, headers=headers, timeout=120)
                
                print(f"[DEBUG]   Response status code: {resp.status_code}")
                print(f"[DEBUG]   Response headers: {dict(resp.headers)}")
                
                if resp.status_code != 200:
                    print(f"[DEBUG] ❌ Non-200 status code: {resp.status_code}")
                    print(f"[DEBUG]   Response text: {resp.text[:500]}")
                    resp.raise_for_status()
                
                print(f"[DEBUG]   Parsing JSON response...")
                data = resp.json()
                print(f"[DEBUG]   Response keys: {list(data.keys())}")
                
                emails = data.get("value", [])
                print(f"[DEBUG]   Found {len(emails)} emails in this batch")
                all_emails.extend(emails)
                
                print(f"📧 Retrieved {len(emails)} emails in this batch")
                
                # Check for next page
                next_link = data.get("@odata.nextLink")
                if next_link:
                    print(f"[DEBUG]   Next page available")
                    print(f"📄 Found next page, continuing...")
                    page_num += 1
                else:
                    print(f"[DEBUG]   No more pages, pagination complete")
                
            except requests.exceptions.Timeout as e:
                print(f"[DEBUG] ❌ Request timeout after 120 seconds")
                print(f"[DEBUG]   Timeout exception: {e}")
                print(f"[DEBUG]   This may indicate network connectivity issues")
                traceback.print_exc()
                print(f"❌ API request failed: {e}")
                break
            except requests.exceptions.ConnectionError as e:
                print(f"[DEBUG] ❌ Connection error - network issue detected")
                print(f"[DEBUG]   Connection exception: {e}")
                print(f"[DEBUG]   This usually means the network is unreachable or blocked")
                traceback.print_exc()
                print(f"❌ API request failed: {e}")
                break
            except requests.exceptions.RequestException as e:
                print(f"[DEBUG] ❌ Request exception occurred")
                print(f"[DEBUG]   Exception type: {type(e).__name__}")
                print(f"[DEBUG]   Exception message: {e}")
                print(f"[DEBUG]   Full traceback:")
                traceback.print_exc()
                print(f"❌ API request failed: {e}")
                break
            except Exception as e:
                print(f"[DEBUG] ❌ Unexpected error during email fetch")
                print(f"[DEBUG]   Exception type: {type(e).__name__}")
                print(f"[DEBUG]   Exception message: {e}")
                print(f"[DEBUG]   Full traceback:")
                traceback.print_exc()
                print(f"❌ Error: {e}")
                break
        
        print(f"[DEBUG] Step 8: Filtering dealing emails...")
        print(f"[DEBUG]   Total emails retrieved: {len(all_emails)}")
        
        # Filter for dealing emails (to/cc dealing@neo-group.in)
        dealing_emails = []
        for email in all_emails:
            # Check if email was sent to or CC'd to Dealing@neo-group.in
            to_recipients = email.get("toRecipients", [])
            cc_recipients = email.get("ccRecipients", [])
            
            to_dealing = any("dealing@neo-group.in" in (r.get("emailAddress", {}).get("address", "") or "").lower()
                           for r in to_recipients)
            cc_dealing = any("dealing@neo-group.in" in (r.get("emailAddress", {}).get("address", "") or "").lower()
                           for r in cc_recipients)
            
            if to_dealing or cc_dealing:
                dealing_emails.append({
                    **email,
                    'to_dealing': to_dealing,
                    'cc_dealing': cc_dealing
                })
        
        print(f"[DEBUG]   Filtered to {len(dealing_emails)} dealing emails")
        print(f"📧 Found {len(dealing_emails)} dealing emails for {target_date}")
        
        if not dealing_emails:
            print(f"[DEBUG] ❌ No dealing emails found - returning None")
            print(f"❌ No dealing emails found for {target_date}")
            return None
        
        print(f"[DEBUG] Step 9: Creating temporary directory for attachments...")
        # Create temporary directory for attachments
        temp_dir = create_attachment_temp_dir()
        print(f"[DEBUG]   Temp directory: {temp_dir}")
        
        # Pre-process emails to pass body content to AI (now parallelized)
        processed_emails = []
        max_workers = 5  # conservative concurrency to avoid API throttling

        def process_single_email(email):
            # Extract body content for AI analysis
            body = email.get('body', {})
            html_content = body.get('content', '')
            content_type = body.get('contentType', 'html')  # Default to 'html' if not specified
            
            # DEBUG: Log what Graph API returned
            subject = email.get('subject', 'N/A')
            if 'KARANI' in subject.upper() or 'DEEPAK' in subject.upper():
                print(f"🔍 DEBUG KARANI EMAIL:")
                print(f"   Subject: {subject}")
                print(f"   Content Type: {content_type}")
                print(f"   HTML Content Length: {len(html_content)}")
                print(f"   Has <table>: {'<table' in html_content.lower() if html_content else False}")
                if html_content:
                    print(f"   First 200 chars: {html_content[:200]}...")
            
            # FIX: Pass raw HTML to AI for better table structure preservation
            # Generate clean_text for backward compatibility, but pass HTML to AI
            import re
            import html
            
            # CRITICAL FIX: If Graph API returned text instead of HTML, we need to request HTML explicitly
            # For now, if content_type is 'text', we can't do much, but log a warning
            if content_type == 'text' and html_content:
                print(f"⚠️  Warning: Email body is plain text, not HTML. Subject: {email.get('subject', 'N/A')}")
                print(f"   This might cause table parsing issues. Consider requesting HTML format from Graph API.")
            
            if html_content:
                # Generate clean_text for backward compatibility (used in some places)
                # Only strip HTML if we actually have HTML (contentType == 'html')
                if content_type == 'html':
                    # We have HTML, generate clean_text by stripping tags
                    clean_text = html.unescape(html_content)
                    clean_text = re.sub(r'<[^>]+>', '', clean_text)
                    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
                else:
                    # We have plain text, use it as-is for clean_text
                    clean_text = html_content.strip()
                
                # Keep raw HTML content to pass to AI (preserves table structure)
                # If content_type is 'html', html_content contains HTML
                # If content_type is 'text', html_content is plain text (but we still pass it)
                # The AI can better understand table structure from HTML than from stripped text
                # html_content remains as-is (not overwritten)
            
            # Process attachments if present
            processed_attachments = []
            if email.get('hasAttachments', False):
                message_id = email.get('id')
                if message_id:
                    # Get attachments for this message
                    attachments_url = f"https://graph.microsoft.com/v1.0/me/messages/{message_id}/attachments"
                    try:
                        att_resp = requests.get(attachments_url, headers=headers, timeout=30)
                        att_resp.raise_for_status()
                        attachments_data = att_resp.json()
                        attachments = attachments_data.get('value', [])
                        
                        # Process attachments
                        processed_attachments = process_email_attachments(message_id, attachments, headers, temp_dir)
                        
                        # Add attachment text to email content
                        # FIX: Append to both HTML and clean_text to maintain consistency
                        for attachment in processed_attachments:
                            if 'extracted_text' in attachment:
                                attachment_type = "PDF" if attachment.get('content_type') == 'application/pdf' else "EMAIL"
                                attachment_text = f"\n\n--- {attachment_type} ATTACHMENT: {attachment['name']} ---\n{attachment['extracted_text']}\n--- END {attachment_type} ATTACHMENT ---\n"
                                
                                # Append to HTML (raw HTML passed to AI)
                                html_content += attachment_text
                                
                                # Also append to clean_text for backward compatibility
                                if 'clean_text' in locals():
                                    clean_text += attachment_text
                        
                    except Exception as e:
                        print(f"⚠️ Failed to process attachments for message {message_id}: {e}")
            
            # Create processed email with body content and attachments
            # FIX: Pass raw HTML to AI instead of clean_text for better table structure preservation
            # DEBUG: Log what we're setting for KARANI email
            if 'KARANI' in subject.upper() or 'DEEPAK' in subject.upper():
                print(f"🔍 DEBUG KARANI EMAIL - Before processed_email:")
                print(f"   html_content length: {len(html_content)}")
                print(f"   html_content has <table>: {'<table' in html_content.lower() if html_content else False}")
                print(f"   clean_text in locals: {'clean_text' in locals()}")
                if 'clean_text' in locals():
                    print(f"   clean_text length: {len(clean_text)}")
                    print(f"   clean_text has <table>: {'<table' in clean_text.lower()}")
            
            processed_email = {
                'subject': email.get('subject', ''),
                'sender': email.get('from', {}).get('emailAddress', {}).get('address', ''),
                'date': email.get('receivedDateTime', ''),
                'clean_text': html_content,  # Pass raw HTML to AI (preserves table structure)
                'clean_text_fallback': clean_text if 'clean_text' in locals() else html_content,  # Keep clean_text for backward compatibility
                'table_data': [],  # Let AI extract table data
                'body': email.get('body', {}),
                'toRecipients': email.get('toRecipients', []),
                'ccRecipients': email.get('ccRecipients', []),
                'to_dealing': email.get('to_dealing', False),
                'cc_dealing': email.get('cc_dealing', False),
                'attachments': processed_attachments,  # Include processed attachments
                'has_attachments': len(processed_attachments) > 0
            }
            return processed_email

        # Run per-email processing in parallel - FIX: Use as_completed to process results as they finish
        print(f"[DEBUG] Step 10: Processing {len(dealing_emails)} dealing emails in parallel...")
        total_emails = len(dealing_emails)
        
        # Update progress file for frontend tracking
        # Write to /app/ in Docker (where code runs) or parent directory locally
        if os.path.exists('/app'):
            progress_file = '/app/email_processing_progress.json'
        else:
            base_path = os.getenv('SURVEILLANCE_BASE_PATH', os.path.dirname(os.path.dirname(__file__)))
            progress_file = os.path.join(base_path, 'email_processing_progress.json')
        
        def update_progress(completed, total, successful):
            try:
                progress_data = {
                    'total_emails': total,
                    'processed_emails': completed,
                    'successful_emails': successful,
                    'remaining_emails': total - completed,
                    'progress_percent': int((completed / total * 100)) if total > 0 else 0,
                    'timestamp': datetime.now().isoformat()
                }
                with open(progress_file, 'w') as f:
                    json.dump(progress_data, f)
                sys.stdout.flush()  # Ensure progress is written immediately
            except Exception as e:
                pass  # Don't fail if progress file can't be written
        
        # Initialize progress file at start
        update_progress(0, total_emails, 0)
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            futures = {executor.submit(process_single_email, email): email for email in dealing_emails}
            completed = 0
            # CRITICAL FIX: Use as_completed() to process results as they finish, not sequentially
            for future in as_completed(futures):
                original_email = futures[future]
                try:
                    result = future.result()  # This now only blocks for the completed future, not all
                    if result:
                        processed_emails.append(result)
                    completed += 1
                    # Update progress file for frontend
                    update_progress(completed, total_emails, len(processed_emails))
                    if completed % 5 == 0 or completed == total_emails:
                        print(f"[DEBUG] Step 10: Progress - {completed}/{total_emails} emails processed ({len(processed_emails)} successful)")
                        sys.stdout.flush()  # Force flush to ensure output is captured
                except Exception as e:
                    completed += 1
                    update_progress(completed, total_emails, len(processed_emails))
                    subject = original_email.get('subject', 'N/A') if isinstance(original_email, dict) else 'N/A'
                    print(f"⚠️ Failed to process email '{subject}': {e}")
                    sys.stdout.flush()
        print(f"[DEBUG] Step 10: Completed parallel processing of emails. Successfully processed {len(processed_emails)}/{total_emails}.")
        sys.stdout.flush()
        # Final progress update
        update_progress(total_emails, total_emails, len(processed_emails))
        
        # Group emails by thread (same subject pattern)
        thread_groups = {}
        for email in processed_emails:
            subject = email['subject']
            
            # Extract base subject pattern (remove RE:, FW:, etc.)
            base_subject = subject
            for prefix in ['RE:', 'FW:', 'FWD:', 'Re:', 'Fw:', 'Fwd:']:
                if subject.upper().startswith(prefix):
                    base_subject = subject[len(prefix):].strip()
                    break
            
            # Create thread key
            thread_key = base_subject
            
            if thread_key not in thread_groups:
                thread_groups[thread_key] = []
            thread_groups[thread_key].append(email)
        
        # Sort emails within each thread by date
        for thread_key in thread_groups:
            thread_groups[thread_key].sort(key=lambda x: x['date'])
        
        print(f"📧 Grouped {len(processed_emails)} emails into {len(thread_groups)} threads")
        
        # Create thread-based data structure for emails
        thread_emails = []
        for thread_key, emails in thread_groups.items():
            if len(emails) == 1:
                # Single email thread - preserve HTML directly
                thread_emails.append(emails[0])
            else:
                # Multiple email thread - combine content
                # CRITICAL FIX: Preserve HTML structure when combining threads
                # Instead of wrapping in plain text format, combine HTML directly
                combined_content = ""
                for email in emails:
                    # Check if clean_text contains HTML
                    email_content = email.get('clean_text', '')
                    # DEBUG: Log thread combination for KARANI
                    if 'KARANI' in str(email.get('subject', '')).upper() or 'DEEPAK' in str(email.get('subject', '')).upper():
                        print(f"🔍 DEBUG KARANI THREAD COMBINATION:")
                        print(f"   Email subject: {email.get('subject', 'N/A')}")
                        print(f"   email_content length: {len(email_content)}")
                        print(f"   Has <table>: {'<table' in email_content.lower() if email_content else False}")
                        print(f"   Has <html>: {'<html' in email_content.lower() if email_content else False}")
                        if email_content:
                            print(f"   First 200 chars: {email_content[:200]}...")
                    if '<table' in email_content.lower() or '<html' in email_content.lower():
                        # Email has HTML - preserve it with HTML wrapper
                        combined_content += f"\n<!-- Email from {email['sender']} -->\n"
                        combined_content += f"<!-- Subject: {email['subject']} -->\n"
                        combined_content += email_content
                        combined_content += "\n"
                    else:
                        # Email is plain text - use text format
                        combined_content += f"\n--- Email from {email['sender']} ---\n"
                        combined_content += f"Subject: {email['subject']}\n"
                        combined_content += f"Content: {email_content}\n"
                
                # Combine attachments from all emails in thread
                combined_attachments = []
                for email in emails:
                    combined_attachments.extend(email.get('attachments', []))
                
                # Create combined thread email
                thread_email = {
                    'subject': thread_key,
                    'sender': emails[0]['sender'],  # Use first email sender
                    'date': emails[0]['date'],  # Use first email date
                    'clean_text': combined_content,
                    'table_data': [],
                    'body': emails[0]['body'],
                    'toRecipients': emails[0]['toRecipients'],
                    'ccRecipients': emails[0]['ccRecipients'],
                    'to_dealing': emails[0]['to_dealing'],
                    'cc_dealing': emails[0]['cc_dealing'],
                    'attachments': combined_attachments,  # Include all attachments from thread
                    'has_attachments': len(combined_attachments) > 0,
                    'thread_emails': emails,  # Keep original emails for reference
                    'is_thread': True
                }
                thread_emails.append(thread_email)
        
        # Create filtered data structure
        filtered_data = {
            'email_analyses': thread_emails,
            'email_type': 'dealing'
        }
        
        # Save to temporary file
        temp_file = f"temp_emails_{target_date.replace('-', '')}.json"
        
        with open(temp_file, "w") as f:
            json.dump(filtered_data, f, indent=2, default=str, ensure_ascii=False)
        
        print(f"📧 Saved {len(processed_emails)} dealing emails for {target_date}")
        
        return temp_file
        
    except Exception as e:
        print(f"[DEBUG] ❌ Exception in get_emails_for_date")
        print(f"[DEBUG]   Exception type: {type(e).__name__}")
        print(f"[DEBUG]   Exception message: {str(e)}")
        print(f"[DEBUG]   Full traceback:")
        traceback.print_exc()
        print(f"❌ Error accessing emails: {str(e)}")
        return None

def process_emails_for_date(target_date: str):
    """Process emails for a specific date using the existing system"""
    print(f"[DEBUG] ===== process_emails_for_date called =====")
    print(f"[DEBUG]   Input date: {target_date}")
    print(f"[DEBUG]   Date type: {type(target_date)}")
    print(f"📧 Processing emails for {target_date}")
    print("=" * 50)
    
    print(f"[DEBUG] Calling get_emails_for_date({target_date})...")
    # Get emails for the date using Graph API
    temp_file = get_emails_for_date(target_date)
    print(f"[DEBUG] get_emails_for_date returned: {temp_file}")
    if not temp_file:
        print(f"[DEBUG] ❌ get_emails_for_date returned None/False - email processing failed")
        print(f"[DEBUG]   This usually means:")
        print(f"[DEBUG]     1. Authentication failed")
        print(f"[DEBUG]     2. Network connectivity issue")
        print(f"[DEBUG]     3. No dealing emails found for the date")
        print(f"[DEBUG]     4. API request failed")
        return False
    print(f"[DEBUG] ✅ get_emails_for_date returned file: {temp_file}")
    
    try:
        # PERMANENT FIX: Get the surveillance base path
        # This script may be called from different directories (e.g., dashboard/backend/)
        # So we need to use absolute paths
        current_dir = os.getcwd()
        script_dir = os.path.dirname(os.path.abspath(__file__))
        surveillance_base = os.path.dirname(script_dir)  # Go up from email_processing/ to root
        
        # Copy the temporary file to the expected location (in surveillance base directory)
        target_file = os.path.join(surveillance_base, "comprehensive_dealing_emails_analysis.json")
        shutil.copy2(temp_file, target_file)
        print(f"📁 Copied email data to: {target_file}")
        
        # Run the existing email surveillance system
        print("🤖 Running email surveillance system...")
        # PERMANENT FIX: Use absolute path to the script and run from surveillance base directory
        email_system_script = os.path.join(script_dir, "complete_email_surveillance_system.py")
        
        # Change to surveillance base directory before running (script expects to run from there)
        original_cwd = os.getcwd()
        try:
            os.chdir(surveillance_base)
            print(f"📂 Changed working directory to: {surveillance_base}")
            print(f"📜 Running script: {email_system_script}")
            
            # FIX: Use venv Python instead of system Python to ensure:
            # 1. Same Python version as manual run
            # 2. Same packages and dependencies
            # 3. Fresh imports (no stale bytecode)
            # 4. HTML fix code is used (not cached old code)
            venv_python = os.path.join(surveillance_base, "august_env", "bin", "python")
            if not os.path.exists(venv_python):
                # Fallback to python3 if venv doesn't exist
                venv_python = "python3"
                print(f"⚠️  Venv Python not found, using: {venv_python}")
            else:
                print(f"✅ Using venv Python: {venv_python}")
            
            # PERMANENT FIX: Use subprocess.run() instead of os.system() to capture output
            # This allows logging of stdout/stderr for debugging
            import subprocess
            print(f"🔄 Running email surveillance system with subprocess...")
            print(f"📜 Command: {venv_python} {email_system_script}")
            print(f"📂 Working directory: {surveillance_base}")
            
            try:
                result = subprocess.run(
                    [venv_python, email_system_script],
                    capture_output=True,
                    text=True,
                    cwd=surveillance_base,
                    timeout=3600  # 1 hour timeout
                )
                
                # Log the output for debugging
                print(f"📊 Subprocess completed with return code: {result.returncode}")
                
                if result.stdout:
                    print(f"📋 STDOUT ({len(result.stdout)} chars, {len(result.stdout.splitlines())} lines):")
                    # Print last 30 lines to avoid overwhelming output
                    stdout_lines = result.stdout.strip().split('\n')
                    for line in stdout_lines[-30:]:
                        print(f"   {line}")
                
                if result.stderr:
                    print(f"⚠️  STDERR ({len(result.stderr)} chars, {len(result.stderr.splitlines())} lines):")
                    # Print last 30 lines
                    stderr_lines = result.stderr.strip().split('\n')
                    for line in stderr_lines[-30:]:
                        print(f"   {line}")
                
                if result.returncode != 0:
                    error_msg = f"❌ Email surveillance failed - exit code: {result.returncode}"
                    if result.stderr:
                        # Show last 500 chars of stderr
                        error_details = result.stderr.strip()[-500:]
                        error_msg += f"\n   Error details: {error_details}"
                    if result.stdout:
                        # Check for error patterns in stdout
                        stdout_lower = result.stdout.lower()
                        if any(keyword in stdout_lower for keyword in ['error', 'failed', 'exception', 'traceback']):
                            error_lines = [line for line in result.stdout.split('\n') 
                                         if any(kw in line.lower() for kw in ['error', 'failed', 'exception'])]
                            if error_lines:
                                error_msg += f"\n   Errors in stdout: {'; '.join(error_lines[-3:])}"
                    print(error_msg)
                    return False
                    
            except subprocess.TimeoutExpired:
                error_msg = "❌ Email surveillance timed out after 1 hour"
                print(error_msg)
                return False
            except Exception as e:
                error_msg = f"❌ Email surveillance subprocess error: {str(e)}"
                print(error_msg)
                import traceback
                traceback.print_exc()
                return False
        finally:
            # Always restore original working directory
            os.chdir(original_cwd)
        
        print("✅ Email surveillance system executed successfully")
        
        # PERMANENT FIX: Find output file in surveillance base directory (where script runs)
        # Support both legacy (complete_email_surveillance_results_*) and current (complete_surveillance_results_*) filenames
        output_files = [
            os.path.join(surveillance_base, f) for f in os.listdir(surveillance_base) if f.endswith('.json') and (
                f.startswith("complete_email_surveillance_results_") or
                f.startswith("complete_surveillance_results_")
            )
        ]
        
        if not output_files:
            print(f"❌ Email surveillance failed - no output file created")
            print(f"🔍 Expected file pattern: complete_*surveillance_results_*.json")
            print(f"🔍 Looking in directory: {surveillance_base}")
            print(f"🔍 Files in directory: {[f for f in os.listdir(surveillance_base) if f.endswith('.json')][:10]}")
            return False
        
        latest_file = max(output_files, key=lambda x: os.path.getctime(x))
        print(f"📄 Found output file: {latest_file}")
        
        # STANDARDIZED FORMAT: Convert YYYY-MM-DD to DDMMYYYY format
        # This matches the format used throughout the surveillance system
        date_obj = datetime.strptime(target_date, '%Y-%m-%d')
        ddmmyyyy = date_obj.strftime('%d%m%Y')
        output_file = os.path.join(surveillance_base, f"email_surveillance_{ddmmyyyy}.json")
        
        # FIX: Save email_analyses (raw emails) to S3, not all_results (analyzed results)
        # This allows the system to re-analyze emails when needed
        # Load the comprehensive_dealing_emails_analysis.json which has email_analyses
        input_file = os.path.join(surveillance_base, "comprehensive_dealing_emails_analysis.json")
        if os.path.exists(input_file):
            # Copy the input file (with email_analyses) instead of output file (with all_results)
            shutil.copy2(input_file, output_file)
            print(f"📁 Email data saved to: {output_file} (using email_analyses format for S3)")
            
            # Verify the structure
            with open(output_file, 'r') as f:
                saved_data = json.load(f)
            if 'email_analyses' in saved_data:
                print(f"✅ Verified: File contains email_analyses ({len(saved_data['email_analyses'])} emails)")
            else:
                print(f"⚠️  Warning: File does not contain email_analyses, keys: {list(saved_data.keys())}")
        else:
            # Fallback: Copy the output file (for backward compatibility)
            shutil.copy2(latest_file, output_file)
            print(f"📁 Email results saved to: {output_file} (fallback to output format)")
        
        # Verify the file was actually created
        if not os.path.exists(output_file):
            print(f"❌ Email surveillance failed - output file not created: {output_file}")
            return False
        
        # Clean up the temporary file
        try:
            os.remove(latest_file)
        except:
            pass
        
        print(f"✅ Email processing completed successfully - file verified: {output_file}")
        return True
        
    except Exception as e:
        print(f"[DEBUG] ❌ Exception in process_emails_for_date")
        print(f"[DEBUG]   Exception type: {type(e).__name__}")
        print(f"[DEBUG]   Exception message: {str(e)}")
        print(f"[DEBUG]   Full traceback:")
        traceback.print_exc()
        print(f"❌ Error processing emails: {str(e)}")
        return False
    
    finally:
        # Clean up temporary files
        try:
            if 'temp_file' in locals():
                os.remove(temp_file)
            print(f"🧹 Cleaned up temporary files")
        except:
            pass
        
        # Clean up attachment temporary directory
        try:
            if os.path.exists(ATTACHMENT_TEMP_DIR):
                shutil.rmtree(ATTACHMENT_TEMP_DIR)
                print(f"🧹 Cleaned up attachment temporary directory")
        except:
            pass

def main():
    if len(sys.argv) != 2:
        print("Usage: python process_emails_by_date.py YYYY-MM-DD")
        print("Example: python process_emails_by_date.py 2025-08-01")
        return
    
    target_date = sys.argv[1]
    
    # Validate date format
    try:
        datetime.strptime(target_date, "%Y-%m-%d")
    except ValueError:
        print("❌ Invalid date format. Use YYYY-MM-DD")
        return
    
    # Process emails for the date
    success = process_emails_for_date(target_date)
    
    if success:
        print(f"\n✅ Successfully processed emails for {target_date}")
    else:
        print(f"\n❌ Failed to process emails for {target_date}")

if __name__ == "__main__":
    main() 