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
from pathlib import Path
from dotenv import load_dotenv

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

def download_attachment(attachment_id, message_id, headers, temp_dir):
    """Download attachment from Graph API"""
    try:
        # Get attachment metadata first
        attachment_url = f"https://graph.microsoft.com/v1.0/me/messages/{message_id}/attachments/{attachment_id}"
        resp = requests.get(attachment_url, headers=headers, timeout=30)
        resp.raise_for_status()
        
        attachment_data = resp.json()
        content_bytes = attachment_data.get('contentBytes', '')
        name = attachment_data.get('name', f'attachment_{attachment_id}')
        content_type = attachment_data.get('contentType', 'application/octet-stream')
        
        # Check if contentBytes is empty (common with email attachments)
        if not content_bytes:
            print(f"   ⚠️ No contentBytes for attachment {name}, trying alternative method...")
            
            # Try to get the attachment content using the $value endpoint
            try:
                content_url = f"https://graph.microsoft.com/v1.0/me/messages/{message_id}/attachments/{attachment_id}/$value"
                content_resp = requests.get(content_url, headers=headers, timeout=30)
                if content_resp.status_code == 200:
                    file_content = content_resp.content
                    print(f"   ✅ Retrieved content via $value endpoint: {len(file_content)} bytes")
                else:
                    print(f"   ❌ $value endpoint failed with status {content_resp.status_code}")
                    return None
            except Exception as e:
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
        
        # Limit filename length to avoid filesystem errors (max 255 chars total)
        # Keep attachment_id (first 50 chars) + safe_name (max 200 chars)
        max_safe_name_length = 200
        if len(safe_name) > max_safe_name_length:
            # Truncate but keep extension
            name_part = safe_name[:max_safe_name_length-len(extension)]
            safe_name = name_part + extension
        
        # Save file
        file_path = os.path.join(temp_dir, f"{attachment_id}_{safe_name}")
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
        print(f"❌ Network error downloading attachment {attachment_id}: {e}")
        return None
    except Exception as e:
        print(f"❌ Failed to download attachment {attachment_id}: {e}")
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

def process_email_attachments(message_id, attachments, headers, temp_dir):
    """Process PDF and email attachments for an email"""
    processed_attachments = []
    
    if not attachments:
        return processed_attachments
    
    print(f"📎 Processing {len(attachments)} attachments for message {message_id}")
    
    # Ensure temp directory exists
    if not os.path.exists(temp_dir):
        print(f"   📁 Creating temp directory: {temp_dir}")
        os.makedirs(temp_dir, exist_ok=True)
    
    for attachment in attachments:
        attachment_id = attachment.get('id')
        if not attachment_id:
            print(f"   ⚠️ Skipping attachment with no ID")
            continue
            
        # Download attachment
        print(f"   📥 Downloading attachment: {attachment.get('name', 'Unknown')}")
        attachment_info = download_attachment(attachment_id, message_id, headers, temp_dir)
        if not attachment_info:
            print(f"   ❌ Failed to download attachment {attachment_id}")
            continue
        
        # Validate attachment info
        content_type = attachment_info.get('content_type', '')
        name = attachment_info.get('name', '')
        file_path = attachment_info.get('file_path', '')
        
        # Check if name is None or empty
        if not name:
            print(f"   ⚠️ Skipping attachment with no name")
            continue
        
        # Verify file was actually saved
        if not os.path.exists(file_path):
            print(f"   ❌ Downloaded file does not exist: {file_path}")
            continue
            
        print(f"   ✅ Downloaded: {name} -> {file_path} ({attachment_info.get('size', 0)} bytes)")
            
        # Check if it's a PDF or email attachment
        is_pdf = False
        is_email_attachment = False
        
        # PDF detection
        if content_type == 'application/pdf':
            is_pdf = True
        elif name and name.lower().endswith('.pdf'):
            is_pdf = True
        
        # Email attachment detection - improved logic
        elif (content_type is None or content_type == 'application/octet-stream') and name:
            # Check for email-like patterns in the name
            email_patterns = ['Re:', 'Fw:', 'FW:', 'RE:', 'FW:', 'Forward:', 'Reply:']
            if any(pattern in name for pattern in email_patterns):
                is_email_attachment = True
            # Also check if it's a .bin file with email-like content
            elif file_path.endswith('.bin') and os.path.exists(file_path):
                # Try to read a small portion to detect if it's email content
                try:
                    with open(file_path, 'rb') as f:
                        sample = f.read(200)
                        sample_str = sample.decode('utf-8', errors='ignore').lower()
                        if any(keyword in sample_str for keyword in ['from:', 'to:', 'subject:', 'date:', 'message-id:']):
                            is_email_attachment = True
                except:
                    pass
        
        if not (is_pdf or is_email_attachment):
            print(f"   ⚠️ Skipping non-PDF/non-email attachment: {name} ({content_type})")
            continue
        
        # Extract text content based on attachment type
        text_content = None
        if is_pdf:
            print(f"   🔍 Extracting text from PDF: {name}")
            text_content = extract_text_from_pdf_attachment(attachment_info)
            if text_content:
                attachment_info['extracted_text'] = text_content
                print(f"   ✅ Extracted text from PDF {name} ({len(text_content)} chars)")
            else:
                print(f"   ⚠️ No text extracted from PDF {name}")
        elif is_email_attachment:
            print(f"   🔍 Extracting text from email attachment: {name}")
            text_content = extract_text_from_email_attachment(attachment_info)
            if text_content and text_content != f"Email attachment: {name}":
                attachment_info['extracted_text'] = text_content
                print(f"   ✅ Extracted text from email attachment {name} ({len(text_content)} chars)")
            else:
                print(f"   ⚠️ No text extracted from email attachment {name}")
                # Still add the attachment info even if extraction failed
                attachment_info['extracted_text'] = f"Email attachment: {name}"
        
        processed_attachments.append(attachment_info)
    
    return processed_attachments

def get_emails_for_date(target_date: str):
    """Get emails for a specific date using Graph API"""
    try:
        # Create MSAL app
        app = msal.PublicClientApplication(CLIENT_ID, authority=AUTHORITY)
        
        # Try silent token first
        accounts = app.get_accounts()
        result = None
        if accounts:
            print("🔄 Using cached token...")
            result = app.acquire_token_silent(SCOPES, account=accounts[0])
        
        # Fall back to interactive login
        if not result or "access_token" not in result:
            print("🔐 Opening browser for authentication...")
            result = app.acquire_token_interactive(scopes=SCOPES)
        
        if "access_token" not in result:
            print(f"❌ Auth failed: {result.get('error_description')}")
            return None
        
        print("✅ Authentication successful!")
        token = result["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Convert target_date to Graph API format (2025-08-05 -> 2025-08-05T00:00:00Z)
        start_date = f"{target_date}T00:00:00Z"
        end_date = f"{target_date}T23:59:59Z"
        
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
        # Note: Graph API returns body.contentType ('html' or 'text') and body.content
        # By default, it should return HTML for modern emails, but we check contentType to be sure
        
        # Get emails with pagination
        all_emails = []
        next_link = messages_url
        
        while next_link:
            try:
                print(f"📧 Fetching batch... (current total: {len(all_emails)})")
                resp = requests.get(next_link, headers=headers, timeout=120)
                resp.raise_for_status()
                
                data = resp.json()
                emails = data.get("value", [])
                all_emails.extend(emails)
                
                print(f"📧 Retrieved {len(emails)} emails in this batch")
                
                # Check for next page
                next_link = data.get("@odata.nextLink")
                if next_link:
                    print(f"📄 Found next page, continuing...")
                
            except requests.exceptions.RequestException as e:
                print(f"❌ API request failed: {e}")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                break
        
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
        
        print(f"📧 Found {len(dealing_emails)} dealing emails for {target_date}")
        
        if not dealing_emails:
            print(f"❌ No dealing emails found for {target_date}")
            return None
        
        # Create temporary directory for attachments
        temp_dir = create_attachment_temp_dir()
        
        # Pre-process emails to pass body content to AI
        processed_emails = []
        for email in dealing_emails:
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
            processed_emails.append(processed_email)
        
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
        print(f"❌ Error accessing emails: {str(e)}")
        return None

def process_emails_for_date(target_date: str):
    """Process emails for a specific date using the existing system"""
    print(f"📧 Processing emails for {target_date}")
    print("=" * 50)
    
    # Get emails for the date using Graph API
    temp_file = get_emails_for_date(target_date)
    if not temp_file:
        return False
    
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
            
            # Run the complete system using venv Python
            result = os.system(f"{venv_python} {email_system_script}")
            
            if result != 0:
                print("❌ Email surveillance failed - system command returned non-zero exit code")
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
        
        # Copy to standardized filename
        shutil.copy2(latest_file, output_file)
        print(f"📁 Email results saved to: {output_file}")
        
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