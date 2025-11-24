#!/usr/bin/env python3
"""
OMS Email Fetcher
Fetches OMS emails from Microsoft Graph API with filtering for "New Order Alert - OMS!" emails.
"""

import json
import os
import sys
from datetime import datetime
import msal
import requests
import base64
import mimetypes
from pathlib import Path
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Your App Registration credentials
TENANT_ID = "d3f35719-3f42-4550-b567-4421c83ca87b"
CLIENT_ID = "6ceedeac-fa0a-4480-b09b-ddec4eacd285"
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPES = ["Mail.Read"]

class OMSEmailFetcher:
    """Fetches OMS emails from Microsoft Graph API."""
    
    def __init__(self):
        """Initialize the OMS email fetcher."""
        self.app = msal.PublicClientApplication(CLIENT_ID, authority=AUTHORITY)
        self.token = None
        self.headers = None
    
    def authenticate(self) -> bool:
        """
        Authenticate with Microsoft Graph API.
        
        Returns:
            True if authentication successful, False otherwise
        """
        try:
            # Try silent token first
            accounts = self.app.get_accounts()
            result = None
            if accounts:
                logger.info("🔄 Using cached token...")
                result = self.app.acquire_token_silent(SCOPES, account=accounts[0])
            
            # Fall back to interactive login
            if not result or "access_token" not in result:
                logger.info("🔐 Opening browser for authentication...")
                result = self.app.acquire_token_interactive(scopes=SCOPES)
            
            if "access_token" not in result:
                logger.error(f"❌ Auth failed: {result.get('error_description')}")
                return False
            
            logger.info("✅ Authentication successful!")
            self.token = result["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
            return True
            
        except Exception as e:
            logger.error(f"❌ Authentication error: {e}")
            return False
    
    def fetch_oms_emails_for_date(self, target_date: str) -> list:
        """
        Fetch OMS emails for a specific date.
        
        Args:
            target_date: Date in YYYY-MM-DD format
        
        Returns:
            List of OMS emails or empty list if failed
        """
        
        if not self.headers:
            logger.error("❌ Not authenticated. Call authenticate() first.")
            return []
        
        try:
            # Convert target_date to Graph API format
            start_date = f"{target_date}T00:00:00Z"
            end_date = f"{target_date}T23:59:59Z"
            
            logger.info(f"🔍 Searching for OMS emails on {target_date}...")
            
            # Search for emails with OMS subject pattern
            messages_url = (
                f"https://graph.microsoft.com/v1.0/me/messages"
                f"?$filter=receivedDateTime ge {start_date} and receivedDateTime le {end_date} "
                f"and contains(subject, 'New Order Alert - OMS!')"
                f"&$select=id,receivedDateTime,from,subject,toRecipients,ccRecipients,body,hasAttachments"
                f"&$orderby=receivedDateTime desc"
            )
            
            # Get emails with pagination
            all_emails = []
            next_link = messages_url
            
            while next_link:
                try:
                    logger.info(f"📧 Fetching OMS email batch... (current total: {len(all_emails)})")
                    resp = requests.get(next_link, headers=self.headers, timeout=120)
                    resp.raise_for_status()
                    
                    data = resp.json()
                    emails = data.get("value", [])
                    all_emails.extend(emails)
                    
                    logger.info(f"📧 Retrieved {len(emails)} OMS emails in this batch")
                    
                    # Check for next page
                    next_link = data.get("@odata.nextLink")
                    if next_link:
                        logger.info(f"📄 Found next page, continuing...")
                    
                except requests.exceptions.RequestException as e:
                    logger.error(f"❌ API request failed: {e}")
                    break
                except Exception as e:
                    logger.error(f"❌ Error: {e}")
                    break
            
            logger.info(f"📧 Found {len(all_emails)} OMS emails for {target_date}")
            return all_emails
            
        except Exception as e:
            logger.error(f"❌ Error fetching OMS emails: {e}")
            return []
    
    def process_oms_email_content(self, email: dict) -> dict:
        """
        Process OMS email content and extract relevant information.
        
        Args:
            email: Raw email data from Graph API
        
        Returns:
            Processed email data
        """
        
        try:
            # Extract body content
            body = email.get('body', {})
            html_content = body.get('content', '')
            
            # Strip HTML tags and entities to get clean text
            import re
            import html
            if html_content:
                # First decode HTML entities
                clean_text = html.unescape(html_content)
                # Remove HTML tags but keep the content
                clean_text = re.sub(r'<[^>]+>', '', clean_text)
                # Clean up extra whitespace
                clean_text = re.sub(r'\s+', ' ', clean_text).strip()
                html_content = clean_text
            
            # Create processed email structure
            processed_email = {
                'subject': email.get('subject', ''),
                'sender': email.get('from', {}).get('emailAddress', {}).get('address', ''),
                'date': email.get('receivedDateTime', ''),
                'clean_text': html_content,
                'body': email.get('body', {}),
                'toRecipients': email.get('toRecipients', []),
                'ccRecipients': email.get('ccRecipients', []),
                'hasAttachments': email.get('hasAttachments', False),
                'message_id': email.get('id', ''),
                'attachment_info': ''  # OMS emails typically don't have `attachments
            }
            
            return processed_email
            
        except Exception as e:
            logger.error(f"❌ Error processing email content: {e}")
            return {}
    
    def save_oms_emails_to_file(self, oms_emails: list, target_date: str) -> str:
        """
        Save OMS emails to a JSON file.
        
        Args:
            oms_emails: List of processed OMS emails
            target_date: Date in YYYY-MM-DD format
        
        Returns:
            Path to saved file or None if failed
        """
        
        try:
            # Process emails
            processed_emails = []
            for email in oms_emails:
                processed_email = self.process_oms_email_content(email)
                if processed_email:
                    processed_emails.append(processed_email)
            
            # Create data structure
            data = {
                'email_analyses': processed_emails,
                'email_type': 'oms_order_alert',
                'fetch_date': target_date,
                'total_emails': len(processed_emails),
                'fetch_timestamp': datetime.now().isoformat()
            }
            
            # Save to file
            date_str = target_date.replace('-', '')
            output_file = f"oms_emails_{date_str}.json"
            
            with open(output_file, "w", encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str, ensure_ascii=False)
            
            logger.info(f"📁 Saved {len(processed_emails)} OMS emails to {output_file}")
            return output_file
            
        except Exception as e:
            logger.error(f"❌ Error saving OMS emails: {e}")
            return None
    
    def create_empty_oms_file(self, target_date: str) -> str:
        """
        Create an empty but valid OMS emails file when no emails are found.
        
        Args:
            target_date: Date in YYYY-MM-DD format
        
        Returns:
            Path to empty file
        """
        
        try:
            # Create empty data structure
            data = {
                'email_analyses': [],
                'email_type': 'oms_order_alert',
                'fetch_date': target_date,
                'total_emails': 0,
                'fetch_timestamp': datetime.now().isoformat(),
                'status': 'no_emails_found'
            }
            
            # Save to file
            date_str = target_date.replace('-', '')
            output_file = f"oms_emails_{date_str}.json"
            
            with open(output_file, "w", encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str, ensure_ascii=False)
            
            logger.info(f"📁 Created empty OMS emails file: {output_file}")
            return output_file
            
        except Exception as e:
            logger.error(f"❌ Error creating empty OMS file: {e}")
            return None
    
    def fetch_and_save_oms_emails(self, target_date: str) -> str:
        """
        Complete process: fetch and save OMS emails for a specific date.
        
        Args:
            target_date: Date in YYYY-MM-DD format
        
        Returns:
            Path to saved file or None if failed
        """
        
        print(f"🚀 OMS Email Fetcher for {target_date}")
        print("=" * 50)
        
        # Step 1: Authenticate
        print("🔐 Step 1: Authenticating with Microsoft Graph API...")
        if not self.authenticate():
            return None
        
        # Step 2: Fetch OMS emails
        print("📧 Step 2: Fetching OMS emails...")
        oms_emails = self.fetch_oms_emails_for_date(target_date)
        
        if not oms_emails:
            logger.warning(f"⚠️ No OMS emails found for {target_date}")
            # Create an empty but valid JSON file to indicate successful processing with no results
            return self.create_empty_oms_file(target_date)
        
        # Step 3: Save to file
        print("💾 Step 3: Saving OMS emails to file...")
        output_file = self.save_oms_emails_to_file(oms_emails, target_date)
        
        if output_file:
            print(f"\n✅ OMS email fetching completed successfully!")
            print(f"📊 Summary:")
            print(f"   📧 OMS emails found: {len(oms_emails)}")
            print(f"   📁 Output file: {output_file}")
            if len(oms_emails) == 0:
                print(f"   ℹ️  No OMS emails found for this date (this is normal)")
        else:
            print(f"\n❌ OMS email fetching failed!")
        
        return output_file

def main():
    """Main function for OMS email fetching."""
    
    if len(sys.argv) != 2:
        print("Usage: python fetch_oms_emails.py YYYY-MM-DD")
        print("Example: python fetch_oms_emails.py 2025-09-02")
        sys.exit(1)
    
    target_date = sys.argv[1]
    
    # Validate date format
    try:
        datetime.strptime(target_date, "%Y-%m-%d")
    except ValueError:
        print("❌ Invalid date format. Use YYYY-MM-DD")
        sys.exit(1)
    
    # Initialize fetcher and run
    fetcher = OMSEmailFetcher()
    output_file = fetcher.fetch_and_save_oms_emails(target_date)
    
    if output_file:
        print(f"\n✅ Successfully processed OMS emails for {target_date}")
        print(f"📁 Results saved to: {output_file}")
        sys.exit(0)
    else:
        print(f"\n❌ Failed to process OMS emails for {target_date}")
        sys.exit(1)

if __name__ == "__main__":
    main()
