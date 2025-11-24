#!/usr/bin/env python3
"""
Quick check for emails on October 1st, 2025 using Graph API
"""

import msal
import requests
from datetime import datetime

# App Registration credentials
TENANT_ID = "d3f35719-3f42-4550-b567-4421c83ca87b"
CLIENT_ID = "6ceedeac-fa0a-4480-b09b-ddec4eacd285"
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPES = ["Mail.Read"]

def check_emails_for_date(target_date: str):
    """Check if there are emails for a specific date"""
    try:
        print(f"📧 Checking emails for {target_date}...")
        print("=" * 60)
        
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
        
        # Convert target_date to Graph API format (2025-10-01 -> 2025-10-01T00:00:00Z)
        start_date = f"{target_date}T00:00:00Z"
        end_date = f"{target_date}T23:59:59Z"
        
        # Search for emails on the specific date
        print(f"🔍 Searching emails from {start_date} to {end_date}...")
        
        messages_url = (
            f"https://graph.microsoft.com/v1.0/me/messages"
            f"?$filter=receivedDateTime ge {start_date} and receivedDateTime le {end_date}"
            f"&$select=id,receivedDateTime,from,subject,toRecipients,ccRecipients,hasAttachments"
            f"&$orderby=receivedDateTime desc"
        )
        
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
        
        print(f"\n📊 RESULTS FOR {target_date}")
        print("=" * 60)
        print(f"Total emails found: {len(all_emails)}")
        
        # Filter for dealing emails (to/cc dealing@neo-group.in)
        dealing_emails = []
        for email in all_emails:
            to_recipients = email.get("toRecipients", [])
            cc_recipients = email.get("ccRecipients", [])
            
            to_dealing = any("dealing@neo-group.in" in (r.get("emailAddress", {}).get("address", "") or "").lower()
                           for r in to_recipients)
            cc_dealing = any("dealing@neo-group.in" in (r.get("emailAddress", {}).get("address", "") or "").lower()
                           for r in cc_recipients)
            
            if to_dealing or cc_dealing:
                dealing_emails.append(email)
        
        print(f"Dealing emails (to/cc dealing@neo-group.in): {len(dealing_emails)}")
        
        if dealing_emails:
            print(f"\n📋 DEALING EMAILS LIST:")
            print("-" * 60)
            for i, email in enumerate(dealing_emails[:10], 1):  # Show first 10
                from_addr = email.get("from", {}).get("emailAddress", {}).get("address", "Unknown")
                subject = email.get("subject", "No Subject")
                received = email.get("receivedDateTime", "")[:19]  # Format datetime
                has_att = "📎" if email.get("hasAttachments", False) else ""
                print(f"{i}. [{received}] {from_addr}")
                print(f"   Subject: {subject} {has_att}")
            
            if len(dealing_emails) > 10:
                print(f"\n... and {len(dealing_emails) - 10} more dealing emails")
        else:
            print(f"\n⚠️  No dealing emails found for {target_date}")
            print("   (No emails to/cc dealing@neo-group.in)")
        
        return {
            'total_emails': len(all_emails),
            'dealing_emails': len(dealing_emails),
            'emails': dealing_emails
        }
        
    except Exception as e:
        print(f"❌ Error checking emails: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    # Check October 1st, 2025
    result = check_emails_for_date("2025-10-01")
    
    if result:
        print(f"\n✅ Summary: Found {result['total_emails']} total emails, {result['dealing_emails']} dealing emails")
    else:
        print(f"\n❌ Failed to check emails")


