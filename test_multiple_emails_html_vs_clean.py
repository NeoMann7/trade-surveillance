#!/usr/bin/env python3
"""
Comprehensive Test: Compare AI extraction with clean_text vs raw HTML
Tests multiple emails to verify consistency
"""

import json
import os
import sys
import re
import html as html_module
from datetime import datetime

# Add email_processing to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'email_processing'))

# Try to import AI module
try:
    from complete_email_surveillance_system import analyze_email_with_ai
    AI_AVAILABLE = True
except ImportError as e:
    print(f"❌ AI module not available: {e}")
    print(f"   Please activate virtual environment: source august_env/bin/activate")
    sys.exit(1)

def get_clean_text_from_html(html_content):
    """Current parsing logic (for comparison)"""
    if not html_content:
        return ""
    
    # Current approach: strip HTML tags
    clean_text = html_module.unescape(html_content)
    clean_text = re.sub(r'<[^>]+>', '', clean_text)
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    return clean_text

def fetch_emails_from_graph_api(target_date="2025-10-08", max_emails=10):
    """Fetch emails from Graph API"""
    try:
        import msal
        import requests
        
        # Use same credentials as process_emails_by_date.py
        TENANT_ID = "d3f35719-3f42-4550-b567-4421c83ca87b"
        CLIENT_ID = "6ceedeac-fa0a-4480-b09b-ddec4eacd285"
        AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
        SCOPES = ["Mail.Read"]
        
        # Create MSAL app
        app = msal.PublicClientApplication(CLIENT_ID, authority=AUTHORITY)
        
        # Try silent token first
        accounts = app.get_accounts()
        result = None
        if accounts:
            result = app.acquire_token_silent(SCOPES, account=accounts[0])
        
        if not result or "access_token" not in result:
            print("🔐 Opening browser for authentication...")
            result = app.acquire_token_interactive(scopes=SCOPES)
        
        if "access_token" not in result:
            print(f"❌ Auth failed: {result.get('error_description')}")
            return []
        
        token = result["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Search for emails
        start_date = f"{target_date}T00:00:00Z"
        end_date = f"{target_date}T23:59:59Z"
        
        messages_url = (
            f"https://graph.microsoft.com/v1.0/me/messages"
            f"?$filter=receivedDateTime ge {start_date} and receivedDateTime le {end_date}"
            f"&$select=id,receivedDateTime,from,subject,toRecipients,ccRecipients,body,hasAttachments"
            f"&$orderby=receivedDateTime desc"
            f"&$top={max_emails}"
        )
        
        resp = requests.get(messages_url, headers=headers, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        emails = data.get("value", [])
        
        # Filter for dealing emails
        dealing_emails = []
        for email in emails:
            to_recipients = email.get("toRecipients", [])
            cc_recipients = email.get("ccRecipients", [])
            
            to_dealing = any("dealing@neo-group.in" in (r.get("emailAddress", {}).get("address", "") or "").lower()
                           for r in to_recipients)
            cc_dealing = any("dealing@neo-group.in" in (r.get("emailAddress", {}).get("address", "") or "").lower()
                           for r in cc_recipients)
            
            if to_dealing or cc_dealing:
                body = email.get('body', {})
                html_content = body.get('content', '')
                if html_content:  # Only include emails with HTML content
                    dealing_emails.append({
                        'subject': email.get('subject', ''),
                        'sender': email.get('from', {}).get('emailAddress', {}).get('address', ''),
                        'html_content': html_content,
                        'date': email.get('receivedDateTime', '')
                    })
        
        return dealing_emails
        
    except Exception as e:
        print(f"❌ Error fetching emails: {e}")
        import traceback
        traceback.print_exc()
        return []

def test_ai_extraction(subject, sender, content, test_name):
    """Test AI extraction with given content"""
    try:
        ai_analysis = analyze_email_with_ai(subject, content, sender, None, None)
        
        order_details = ai_analysis.get('ai_order_details', [])
        if isinstance(order_details, dict):
            order_details = [order_details]
        
        return {
            'intent': ai_analysis.get('ai_email_intent', 'N/A'),
            'confidence': ai_analysis.get('ai_confidence_score', 0),
            'orders_count': len(order_details) if order_details else 0,
            'orders': order_details,
            'reasoning': ai_analysis.get('ai_reasoning', '')[:100]
        }
    except Exception as e:
        return {
            'error': str(e),
            'intent': 'error',
            'confidence': 0,
            'orders_count': 0,
            'orders': []
        }

def compare_extractions(clean_result, html_result):
    """Compare results from both approaches"""
    comparison = {
        'both_work': False,
        'clean_better': False,
        'html_better': False,
        'both_fail': False,
        'differences': []
    }
    
    clean_orders = clean_result.get('orders', [])
    html_orders = html_result.get('orders', [])
    
    # Compare order counts
    if len(clean_orders) != len(html_orders):
        comparison['differences'].append(f"Order count: clean_text={len(clean_orders)}, html={len(html_orders)}")
    
    # Compare quantities if orders exist
    if clean_orders and html_orders:
        for i, (clean_order, html_order) in enumerate(zip(clean_orders, html_orders), 1):
            clean_qty = clean_order.get('quantity', '')
            html_qty = html_order.get('quantity', '')
            
            if clean_qty != html_qty:
                comparison['differences'].append(f"Order {i} quantity: clean_text={clean_qty}, html={html_qty}")
            
            # Check other fields
            clean_symbol = clean_order.get('symbol', '')
            html_symbol = html_order.get('symbol', '')
            if clean_symbol != html_symbol:
                comparison['differences'].append(f"Order {i} symbol: clean_text={clean_symbol}, html={html_symbol}")
    
    # Determine which is better
    if len(clean_orders) > 0 and len(html_orders) > 0:
        comparison['both_work'] = True
        # Check if quantities match (both correct)
        if clean_orders and html_orders:
            clean_qty = clean_orders[0].get('quantity', '')
            html_qty = html_orders[0].get('quantity', '')
            if clean_qty == html_qty:
                comparison['both_work'] = True
    elif len(clean_orders) > 0:
        comparison['clean_better'] = True
    elif len(html_orders) > 0:
        comparison['html_better'] = True
    else:
        comparison['both_fail'] = True
    
    return comparison

def main():
    print("="*70)
    print("COMPREHENSIVE TEST: HTML vs Clean Text - Multiple Emails")
    print("="*70)
    
    # Fetch emails from Graph API
    print("\n📧 Fetching emails from Graph API for October 8th, 2025...")
    emails = fetch_emails_from_graph_api("2025-10-08", max_emails=10)
    
    # Always try to add the ACTIVEINFR email from saved file
    if os.path.exists('test_actual_email_html.html'):
        print("📂 Adding ACTIVEINFR email from saved file...")
        with open('test_actual_email_html.html', 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Get metadata from email surveillance
        date_str = "08102025"
        email_file = f"email_surveillance_{date_str}.json"
        if os.path.exists(email_file):
            with open(email_file, 'r') as f:
                email_surveillance = json.load(f)
            
            all_results = email_surveillance.get('all_results', [])
            for result in all_results:
                subject = result.get('subject', '')
                if 'ADCC' in subject and 'APPROVAL' in subject.upper():
                    # Add to emails list if not already there
                    email_exists = any('ADCC' in e.get('subject', '') and 'APPROVAL' in e.get('subject', '').upper() 
                                     for e in emails)
                    if not email_exists:
                        emails.append({
                            'subject': subject,
                            'sender': result.get('sender', ''),
                            'html_content': html_content,
                            'date': '2025-10-08'
                        })
                        print(f"   ✅ Added: {subject[:60]}...")
                    break
    
    if not emails:
        print("❌ No emails found for testing")
        return
    
    if not emails:
        print("❌ No emails available for testing")
        return
    
    print(f"✅ Found {len(emails)} emails to test\n")
    
    # Test each email
    results = []
    for i, email in enumerate(emails, 1):
        subject = email['subject']
        sender = email['sender']
        html_content = email['html_content']
        
        print(f"{'='*70}")
        print(f"EMAIL {i}/{len(emails)}: {subject[:60]}...")
        print(f"{'='*70}")
        
        # Generate clean_text
        clean_text = get_clean_text_from_html(html_content)
        
        print(f"\n📊 Content Analysis:")
        print(f"   HTML length: {len(html_content)} chars")
        print(f"   Clean text length: {len(clean_text)} chars")
        
        # Check for table
        has_table = '<table' in html_content.lower()
        print(f"   Has table: {has_table}")
        
        # Test with clean_text
        print(f"\n🤖 Testing with clean_text (current approach)...")
        clean_result = test_ai_extraction(subject, sender, clean_text, "clean_text")
        print(f"   Intent: {clean_result['intent']}")
        print(f"   Orders: {clean_result['orders_count']}")
        if clean_result['orders']:
            for j, order in enumerate(clean_result['orders'][:2], 1):
                print(f"   Order {j}: {order.get('symbol', 'N/A')} - Qty: {order.get('quantity', 'N/A')}")
        
        # Test with HTML
        print(f"\n🤖 Testing with raw HTML (new approach)...")
        html_result = test_ai_extraction(subject, sender, html_content, "raw HTML")
        print(f"   Intent: {html_result['intent']}")
        print(f"   Orders: {html_result['orders_count']}")
        if html_result['orders']:
            for j, order in enumerate(html_result['orders'][:2], 1):
                print(f"   Order {j}: {order.get('symbol', 'N/A')} - Qty: {order.get('quantity', 'N/A')}")
        
        # Compare
        comparison = compare_extractions(clean_result, html_result)
        print(f"\n📊 Comparison:")
        if comparison['both_work']:
            print(f"   ✅ Both approaches work")
        elif comparison['html_better']:
            print(f"   ✅ HTML approach is BETTER")
        elif comparison['clean_better']:
            print(f"   ⚠️  Clean text approach is better")
        else:
            print(f"   ❌ Both approaches failed")
        
        if comparison['differences']:
            print(f"   Differences:")
            for diff in comparison['differences']:
                print(f"     - {diff}")
        
        results.append({
            'subject': subject,
            'clean_result': clean_result,
            'html_result': html_result,
            'comparison': comparison
        })
        
        print()
    
    # Summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    
    both_work = sum(1 for r in results if r['comparison']['both_work'])
    html_better = sum(1 for r in results if r['comparison']['html_better'])
    clean_better = sum(1 for r in results if r['comparison']['clean_better'])
    both_fail = sum(1 for r in results if r['comparison']['both_fail'])
    
    print(f"\n📊 Results across {len(results)} emails:")
    print(f"   Both work: {both_work}")
    print(f"   HTML better: {html_better}")
    print(f"   Clean text better: {clean_better}")
    print(f"   Both fail: {both_fail}")
    
    print(f"\n💡 Recommendation:")
    if html_better > 0 or (both_work > 0 and html_better == 0 and clean_better == 0):
        print(f"   ✅ PASSING RAW HTML TO AI IS PREFERABLE")
        print(f"   - HTML preserves table structure")
        print(f"   - More reliable for complex emails")
        print(f"   - Better handling of edge cases")
    elif clean_better > html_better:
        print(f"   ⚠️  Current approach (clean_text) seems sufficient")
    else:
        print(f"   ⚠️  Both approaches work similarly")
    
    print(f"\n{'='*70}")

if __name__ == "__main__":
    main()

