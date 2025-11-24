#!/usr/bin/env python3
"""
Test Script: Compare AI extraction with clean_text vs raw HTML
This script tests if passing raw HTML to AI improves quantity extraction
without modifying existing logic.
"""

import json
import os
import sys
import re
import html as html_module
from datetime import datetime

# Add email_processing to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'email_processing'))

# Try to import, but handle if venv is not activated
try:
    from complete_email_surveillance_system import analyze_email_with_ai
    AI_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  Warning: Could not import AI module: {e}")
    print(f"   This test requires the virtual environment to be activated")
    print(f"   Run: source august_env/bin/activate")
    AI_AVAILABLE = False
    
    # Create a mock function for testing structure
    def analyze_email_with_ai(subject, clean_text, sender, table_data=None, attachments=None):
        return {
            "ai_email_intent": "trade_instruction",
            "ai_confidence_score": 0,
            "ai_reasoning": "Mock - AI not available",
            "ai_order_details": [],
            "ai_instruction_type": "unknown"
        }

def get_clean_text_from_html(html_content):
    """Current parsing logic (for comparison)"""
    if not html_content:
        return ""
    
    # Current approach: strip HTML tags
    clean_text = html_module.unescape(html_content)
    clean_text = re.sub(r'<[^>]+>', '', clean_text)
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    return clean_text

def fetch_email_html_from_graph_api(target_date="2025-10-08"):
    """Fetch original HTML from Graph API for ACTIVEINFR email"""
    try:
        import msal
        import requests
        
        # Use same credentials as process_emails_by_date.py (hardcoded)
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
        
        # Search for ACTIVEINFR email
        start_date = f"{target_date}T00:00:00Z"
        end_date = f"{target_date}T23:59:59Z"
        
        messages_url = (
            f"https://graph.microsoft.com/v1.0/me/messages"
            f"?$filter=receivedDateTime ge {start_date} and receivedDateTime le {end_date}"
            f"&$select=id,receivedDateTime,from,subject,toRecipients,ccRecipients,body,hasAttachments"
            f"&$orderby=receivedDateTime desc"
        )
        
        resp = requests.get(messages_url, headers=headers, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        emails = data.get("value", [])
        
        # Find ACTIVEINFR email
        for email in emails:
            subject = email.get('subject', '')
            if 'ADCC' in subject and 'APPROVAL' in subject.upper():
                body = email.get('body', {})
                html_content = body.get('content', '')
                return {
                    'subject': subject,
                    'sender': email.get('from', {}).get('emailAddress', {}).get('address', ''),
                    'html_content': html_content,
                    'body': body
                }
        
        print("❌ ACTIVEINFR email not found")
        return None
        
    except Exception as e:
        print(f"❌ Error fetching email: {e}")
        return None

def test_ai_extraction(subject, sender, content, test_name):
    """Test AI extraction with given content"""
    print(f"\n{'='*70}")
    print(f"TEST: {test_name}")
    print(f"{'='*70}")
    print(f"Subject: {subject}")
    print(f"Content length: {len(content)} chars")
    print(f"Content preview (first 300 chars):")
    print(f"  {content[:300]}...")
    
    # Check if quantity is visible
    if '7,48,800' in content:
        print(f"  ✅ Contains '7,48,800'")
    if 'NE0KLO010257,48,800' in content:
        print(f"  ⚠️  Contains 'NE0KLO010257,48,800' (merged)")
    
    print(f"\n🤖 Calling AI...")
    try:
        ai_analysis = analyze_email_with_ai(subject, content, sender, None, None)
        
        print(f"\n📊 AI Analysis Results:")
        print(f"  Intent: {ai_analysis.get('ai_email_intent', 'N/A')}")
        print(f"  Confidence: {ai_analysis.get('ai_confidence_score', 'N/A')}")
        print(f"  Reasoning: {ai_analysis.get('ai_reasoning', 'N/A')[:200]}...")
        
        order_details = ai_analysis.get('ai_order_details', [])
        if isinstance(order_details, dict):
            order_details = [order_details]
        
        if order_details:
            print(f"\n  📋 Extracted Orders: {len(order_details)}")
            for i, order in enumerate(order_details, 1):
                print(f"\n  Order {i}:")
                print(f"    Client Code: {order.get('client_code', 'N/A')}")
                print(f"    Symbol: {order.get('symbol', 'N/A')}")
                print(f"    Quantity: {order.get('quantity', 'N/A')} ⭐")
                print(f"    Price: {order.get('price', 'N/A')}")
                print(f"    Buy/Sell: {order.get('buy_sell', 'N/A')}")
                
                # Check if quantity is correct
                qty = order.get('quantity', '')
                if qty == '748800' or qty == '748,800':
                    print(f"    ✅ CORRECT QUANTITY!")
                elif qty == '48800' or qty == '48,800':
                    print(f"    ❌ WRONG QUANTITY (missing '7,' prefix)")
                else:
                    print(f"    ⚠️  Quantity: {qty} (needs verification)")
        else:
            print(f"  ❌ No orders extracted")
        
        return ai_analysis
        
    except Exception as e:
        print(f"  ❌ AI analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    print("="*70)
    print("TEST: HTML vs Clean Text - AI Extraction Comparison")
    print("="*70)
    
    if not AI_AVAILABLE:
        print("\n❌ AI module not available. Please activate virtual environment:")
        print("   source august_env/bin/activate")
        print("\n   Or run the test from the email processing directory")
        return
    
    # Fetch email from Graph API
    print("\n📧 Fetching ACTIVEINFR email from Graph API...")
    email_data = fetch_email_html_from_graph_api()
    
    if not email_data:
        # Try to load from saved HTML file
        if os.path.exists('test_actual_email_html.html'):
            print("\n📂 Loading saved HTML from test_actual_email_html.html...")
            with open('test_actual_email_html.html', 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Get subject and sender from existing email surveillance data
            date_str = "08102025"
            email_file = f"email_surveillance_{date_str}.json"
            if os.path.exists(email_file):
                with open(email_file, 'r') as f:
                    email_surveillance = json.load(f)
                
                all_results = email_surveillance.get('all_results', [])
                for result in all_results:
                    subject = result.get('subject', '')
                    if 'ADCC' in subject and 'APPROVAL' in subject.upper():
                        sender = result.get('sender', '')
                        email_data = {
                            'subject': subject,
                            'sender': sender,
                            'html_content': html_content,
                            'clean_text': get_clean_text_from_html(html_content)
                        }
                        print("✅ Loaded HTML from saved file")
                        break
            
            if not email_data:
                print("❌ Could not find email metadata")
                return
        else:
            print("\n❌ Could not fetch email and no saved HTML file found")
            print("   Please run the email fetch script first")
            return
    
    subject = email_data['subject']
    sender = email_data['sender']
    html_content = email_data['html_content']
    
    # Test 1: Current approach (clean_text - stripped HTML)
    print(f"\n{'='*70}")
    print("TEST 1: CURRENT APPROACH (clean_text - stripped HTML)")
    print(f"{'='*70}")
    clean_text = get_clean_text_from_html(html_content)
    result1 = test_ai_extraction(subject, sender, clean_text, "Current Approach (Stripped HTML)")
    
    # Test 2: New approach (raw HTML)
    print(f"\n{'='*70}")
    print("TEST 2: NEW APPROACH (raw HTML)")
    print(f"{'='*70}")
    result2 = test_ai_extraction(subject, sender, html_content, "New Approach (Raw HTML)")
    
    # Comparison
    print(f"\n{'='*70}")
    print("COMPARISON")
    print(f"{'='*70}")
    
    if result1 and result2:
        orders1 = result1.get('ai_order_details', [])
        orders2 = result2.get('ai_order_details', [])
        
        if isinstance(orders1, dict):
            orders1 = [orders1]
        if isinstance(orders2, dict):
            orders2 = [orders2]
        
        print(f"\nCurrent Approach (clean_text):")
        print(f"  Orders extracted: {len(orders1)}")
        if orders1:
            qty1 = orders1[0].get('quantity', '')
            print(f"  Quantity: {qty1}")
            if qty1 in ['748800', '748,800']:
                print(f"  ✅ CORRECT")
            elif qty1 in ['48800', '48,800']:
                print(f"  ❌ WRONG (missing '7,' prefix)")
        
        print(f"\nNew Approach (raw HTML):")
        print(f"  Orders extracted: {len(orders2)}")
        if orders2:
            qty2 = orders2[0].get('quantity', '')
            print(f"  Quantity: {qty2}")
            if qty2 in ['748800', '748,800']:
                print(f"  ✅ CORRECT")
            elif qty2 in ['48800', '48,800']:
                print(f"  ❌ WRONG (missing '7,' prefix)")
        
        print(f"\n📊 VERDICT:")
        if orders2 and orders2[0].get('quantity', '') in ['748800', '748,800']:
            if not orders1 or orders1[0].get('quantity', '') not in ['748800', '748,800']:
                print(f"  ✅ Raw HTML approach is BETTER!")
                print(f"  ✅ Recommend passing HTML to AI")
            else:
                print(f"  ⚠️  Both approaches work")
        elif orders1 and orders1[0].get('quantity', '') in ['748800', '748,800']:
            print(f"  ⚠️  Current approach works, HTML doesn't help")
        else:
            print(f"  ❌ Both approaches failed")
    
    print(f"\n{'='*70}")

if __name__ == "__main__":
    main()

