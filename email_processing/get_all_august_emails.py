#!/usr/bin/env python3
"""
Get ALL August Emails - Comprehensive Search
Handles pagination and searches all email folders
"""

import msal
import requests
import json
import os
from datetime import datetime

# Your App Registration credentials
TENANT_ID = "d3f35719-3f42-4550-b567-4421c83ca87b"
CLIENT_ID = "6ceedeac-fa0a-4480-b09b-ddec4eacd285"
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPES = ["Mail.Read"]

def get_all_emails_with_pagination(headers, base_url):
    """Get all emails using pagination"""
    all_emails = []
    next_link = base_url
    
    print(f"🔍 Starting pagination search...")
    
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
    
    return all_emails

def main():
    print("📧 Get ALL August Emails - Comprehensive Search")
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
        return
    
    print("✅ Authentication successful!")
    token = result["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Search for ALL emails in August 2025 with pagination
    print(f"\n🔍 Searching ALL emails from August 2025 with pagination...")
    
    # Method 1: Search all messages (not just inbox)
    all_messages_url = (
        f"https://graph.microsoft.com/v1.0/me/messages"
        f"?$filter=receivedDateTime ge 2025-08-01T00:00:00Z and receivedDateTime lt 2025-09-01T00:00:00Z"
        f"&$select=receivedDateTime,from,subject,toRecipients,ccRecipients,body,hasAttachments"
        f"&$orderby=receivedDateTime desc"
    )
    
    print(f"📧 Method 1: Searching ALL messages...")
    all_august_emails = get_all_emails_with_pagination(headers, all_messages_url)
    print(f"📧 Method 1 Results: {len(all_august_emails)} emails")
    
    # Method 2: Search specific folders
    folders_to_search = ['inbox', 'sentitems', 'drafts', 'deleteditems', 'archive']
    folder_emails = {}
    
    for folder in folders_to_search:
        print(f"\n📧 Method 2: Searching {folder} folder...")
        folder_url = (
            f"https://graph.microsoft.com/v1.0/me/mailFolders/{folder}/messages"
            f"?$filter=receivedDateTime ge 2025-08-01T00:00:00Z and receivedDateTime lt 2025-09-01T00:00:00Z"
            f"&$select=receivedDateTime,from,subject,toRecipients,ccRecipients,body,hasAttachments"
            f"&$orderby=receivedDateTime desc"
        )
        
        folder_emails[folder] = get_all_emails_with_pagination(headers, folder_url)
        print(f"📧 {folder}: {len(folder_emails[folder])} emails")
    
    # Combine all results
    all_emails_combined = all_august_emails.copy()
    
    # Add folder-specific emails (avoid duplicates)
    seen_ids = set(email.get('id') for email in all_emails_combined)
    for folder, emails in folder_emails.items():
        for email in emails:
            if email.get('id') not in seen_ids:
                all_emails_combined.append(email)
                seen_ids.add(email.get('id'))
    
    print(f"\n📊 COMBINED RESULTS")
    print("=" * 40)
    print(f"All Messages Search: {len(all_august_emails)} emails")
    for folder, emails in folder_emails.items():
        print(f"{folder.capitalize()} Folder: {len(emails)} emails")
    print(f"Total Unique Emails: {len(all_emails_combined)} emails")
    
    # Filter for dealing emails
    dealing_emails = []
    other_emails = []
    
    for msg in all_emails_combined:
        to_recipients = msg.get("toRecipients", [])
        cc_recipients = msg.get("ccRecipients", [])
        
        # Check if email was sent to or CC'd to Dealing@neo-group.in
        to_dealing = any("dealing@neo-group.in" in r.get("emailAddress", {}).get("address", "").lower() 
                       for r in to_recipients)
        cc_dealing = any("dealing@neo-group.in" in r.get("emailAddress", {}).get("address", "").lower() 
                       for r in cc_recipients)
        
        if to_dealing or cc_dealing:
            dealing_emails.append({
                **msg,
                'to_dealing': to_dealing,
                'cc_dealing': cc_dealing
            })
        else:
            other_emails.append(msg)
    
    print(f"\n📧 FILTERING RESULTS")
    print("=" * 40)
    print(f"📧 Found {len(dealing_emails)} emails to/cc Dealing@neo-group.in")
    print(f"📧 Found {len(other_emails)} other emails")
    
    if dealing_emails:
        print("\n📋 Emails to/cc Dealing@neo-group.in in August:")
        for i, email in enumerate(dealing_emails):
            sender = email.get("from", {}).get("emailAddress", {}).get("address", "(no sender)")
            subject = email.get("subject", "(no subject)")
            date = email.get("receivedDateTime", "")
            
            print(f"\n{i+1}. {date}")
            print(f"   From: {sender}")
            print(f"   Subject: {subject}")
            print(f"   To Dealing: {'✅' if email.get('to_dealing') else '❌'}")
            print(f"   CC Dealing: {'✅' if email.get('cc_dealing') else '❌'}")
            print(f"   Has Attachments: {'✅' if email.get('hasAttachments') else '❌'}")
        
        # Save all results
        os.makedirs("email_processing", exist_ok=True)
        
        # Save all August emails
        with open("email_processing/august_all_emails_comprehensive.json", "w") as f:
            json.dump(all_emails_combined, f, indent=2, default=str, ensure_ascii=False)
        
        # Save dealing emails
        with open("email_processing/august_dealing_emails_comprehensive.json", "w") as f:
            json.dump(dealing_emails, f, indent=2, default=str, ensure_ascii=False)
        
        # Save folder breakdown
        folder_summary = {
            'search_methods': {
                'all_messages': len(all_august_emails),
                'folder_breakdown': {folder: len(emails) for folder, emails in folder_emails.items()}
            },
            'results': {
                'total_unique_emails': len(all_emails_combined),
                'dealing_emails_found': len(dealing_emails),
                'other_emails': len(other_emails),
                'dealing_to_count': len([e for e in dealing_emails if e.get('to_dealing')]),
                'dealing_cc_count': len([e for e in dealing_emails if e.get('cc_dealing')])
            }
        }
        
        with open("email_processing/august_email_search_summary.json", "w") as f:
            json.dump(folder_summary, f, indent=2, default=str, ensure_ascii=False)
        
        print(f"\n✅ Results saved to email_processing/")
        print(f"   - august_all_emails_comprehensive.json ({len(all_emails_combined)} emails)")
        print(f"   - august_dealing_emails_comprehensive.json ({len(dealing_emails)} emails)")
        print(f"   - august_email_search_summary.json (search summary)")
        
    else:
        print("❌ No emails found to/cc Dealing@neo-group.in in August")
        
        # Show sample of other emails for debugging
        print("\n📧 Sample of other August emails (first 10):")
        for i, email in enumerate(other_emails[:10]):
            sender = email.get("from", {}).get("emailAddress", {}).get("address", "(no sender)")
            subject = email.get("subject", "(no subject)")
            to_recipients = email.get("toRecipients", [])
            to_emails = [r.get("emailAddress", {}).get("address", "") for r in to_recipients]
            
            print(f"\n{i+1}. From: {sender}")
            print(f"   Subject: {subject}")
            print(f"   To: {', '.join(to_emails[:3])}")

if __name__ == "__main__":
    main() 