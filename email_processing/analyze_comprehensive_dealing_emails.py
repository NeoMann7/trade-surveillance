#!/usr/bin/env python3
"""
Analyze Comprehensive Dealing Emails
Analyze the full dataset of 227 dealing emails from August 2025
"""

import json
import re
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
from collections import Counter

def clean_html_content(html_content):
    """Extract clean text from HTML content"""
    if not html_content:
        return ""
    
    # Parse HTML
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.decompose()
    
    # Get text and clean it
    text = soup.get_text()
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = ' '.join(chunk for chunk in chunks if chunk)
    
    return text

def extract_table_data(html_content):
    """Extract table data from HTML content"""
    if not html_content:
        return []
    
    soup = BeautifulSoup(html_content, 'html.parser')
    tables = soup.find_all('table')
    
    table_data = []
    for table in tables:
        rows = table.find_all('tr')
        for row in rows:
            cells = row.find_all(['td', 'th'])
            row_data = []
            for cell in cells:
                cell_text = cell.get_text(strip=True)
                if cell_text:
                    row_data.append(cell_text)
            if row_data:
                table_data.append(row_data)
    
    return table_data

def analyze_email_content(email):
    """Analyze individual email content"""
    analysis = {
        'email_id': email.get('id', ''),
        'subject': email.get('subject', ''),
        'sender': email.get('from', {}).get('emailAddress', {}).get('address', ''),
        'date': email.get('receivedDateTime', ''),
        'has_attachments': email.get('hasAttachments', False),
        'to_dealing': email.get('to_dealing', False),
        'cc_dealing': email.get('cc_dealing', False),
        'content_type': 'unknown',
        'extracted_data': {},
        'client_codes': [],
        'amounts': [],
        'account_names': [],
        'order_keywords': []
    }
    
    # Get email body
    body = email.get('body', {})
    html_content = body.get('content', '')
    
    # Clean HTML content
    clean_text = clean_html_content(html_content)
    analysis['clean_text'] = clean_text[:200] + "..." if len(clean_text) > 200 else clean_text
    
    # Extract table data
    table_data = extract_table_data(html_content)
    analysis['table_data'] = table_data
    
    # Analyze content type based on subject and content
    subject_lower = analysis['subject'].lower()
    text_lower = clean_text.lower()
    
    # Enhanced content type detection
    if 'debit' in subject_lower or 'debit' in text_lower:
        analysis['content_type'] = 'debit_list'
    elif 'trail balance' in subject_lower or 'trial balance' in text_lower:
        analysis['content_type'] = 'trial_balance'
    elif any(keyword in subject_lower for keyword in ['trade instruction', 'trade confirmation', 'trade conformation']):
        analysis['content_type'] = 'trade_instruction'
    elif any(keyword in subject_lower for keyword in ['order', 'buy', 'sell', 'execute']):
        analysis['content_type'] = 'order'
    elif any(keyword in subject_lower for keyword in ['approval', 'approve', 'confirm']):
        analysis['content_type'] = 'approval'
    elif any(keyword in subject_lower for keyword in ['process file', 'settlement']):
        analysis['content_type'] = 'settlement'
    elif any(keyword in subject_lower for keyword in ['monitoring', 'alert']):
        analysis['content_type'] = 'monitoring'
    else:
        analysis['content_type'] = 'other'
    
    # Extract client codes (NEO patterns)
    client_codes = re.findall(r'NEO[A-Z0-9]+', clean_text)
    analysis['client_codes'] = list(set(client_codes))
    
    # Extract amounts (currency patterns)
    amount_patterns = [
        r'₹\s*([0-9,]+\.?[0-9]*)',
        r'Rs\.\s*([0-9,]+\.?[0-9]*)',
        r'([0-9,]+\.?[0-9]*)\s*(?:₹|Rs\.)',
        r'([0-9,]+\.?[0-9]*)'
    ]
    
    amounts = []
    for pattern in amount_patterns:
        found = re.findall(pattern, clean_text)
        amounts.extend(found)
    
    # Clean and filter amounts
    cleaned_amounts = []
    for amount in amounts:
        try:
            # Remove commas and convert to float
            clean_amount = float(amount.replace(',', ''))
            if clean_amount > 0:  # Only positive amounts
                cleaned_amounts.append(clean_amount)
        except:
            continue
    
    analysis['amounts'] = cleaned_amounts
    
    # Extract account names from table data
    account_names = []
    for row in table_data:
        if len(row) >= 2:  # At least Acc Code and Account Name columns
            # Look for account names (usually in second column)
            potential_name = row[1] if len(row) > 1 else row[0]
            if potential_name and not potential_name.isdigit() and len(potential_name) > 3:
                account_names.append(potential_name)
    
    analysis['account_names'] = list(set(account_names))
    
    # Extract order-related keywords
    order_keywords = []
    keywords_to_find = ['buy', 'sell', 'execute', 'order', 'trade', 'instruction', 'confirmation', 'approval']
    for keyword in keywords_to_find:
        if keyword in text_lower:
            order_keywords.append(keyword)
    
    analysis['order_keywords'] = order_keywords
    
    return analysis

def main():
    print("📧 Analyzing Comprehensive Dealing Emails (227 emails)")
    print("=" * 60)
    
    # Load comprehensive dealing emails
    try:
        with open("august_dealing_emails_comprehensive.json", "r") as f:
            dealing_emails = json.load(f)
    except FileNotFoundError:
        print("❌ File not found: august_dealing_emails_comprehensive.json")
        return
    
    print(f"📧 Found {len(dealing_emails)} dealing emails to analyze")
    
    # Analyze each email
    email_analyses = []
    content_types = Counter()
    senders = Counter()
    dates = Counter()
    
    for i, email in enumerate(dealing_emails):
        if i % 50 == 0:  # Progress indicator
            print(f"🔍 Analyzing email {i+1}/{len(dealing_emails)}...")
        
        analysis = analyze_email_content(email)
        email_analyses.append(analysis)
        
        # Count content types, senders, and dates
        content_types[analysis['content_type']] += 1
        senders[analysis['sender']] += 1
        date = analysis['date'][:10] if analysis['date'] else 'unknown'
        dates[date] += 1
    
    # Create comprehensive summary
    summary = {
        'total_emails': len(dealing_emails),
        'content_types': dict(content_types),
        'top_senders': dict(senders.most_common(10)),
        'daily_distribution': dict(dates),
        'all_client_codes': [],
        'all_amounts': [],
        'all_account_names': [],
        'email_analyses': email_analyses
    }
    
    # Aggregate data
    for analysis in email_analyses:
        # Client codes
        summary['all_client_codes'].extend(analysis['client_codes'])
        
        # Amounts
        summary['all_amounts'].extend(analysis['amounts'])
        
        # Account names
        summary['all_account_names'].extend(analysis['account_names'])
    
    # Remove duplicates
    summary['all_client_codes'] = list(set(summary['all_client_codes']))
    summary['all_account_names'] = list(set(summary['all_account_names']))
    
    # Save detailed analysis
    with open("email_processing/comprehensive_dealing_emails_analysis.json", "w") as f:
        json.dump(summary, f, indent=2, default=str, ensure_ascii=False)
    
    # Print comprehensive summary
    print(f"\n📊 COMPREHENSIVE ANALYSIS SUMMARY")
    print("=" * 50)
    print(f"Total Emails Analyzed: {summary['total_emails']}")
    
    print(f"\n📋 Content Types:")
    for content_type, count in sorted(summary['content_types'].items(), key=lambda x: x[1], reverse=True):
        percentage = (count / summary['total_emails']) * 100
        print(f"   {content_type}: {count} emails ({percentage:.1f}%)")
    
    print(f"\n👤 Top Senders:")
    for sender, count in summary['top_senders'].items():
        percentage = (count / summary['total_emails']) * 100
        print(f"   {sender}: {count} emails ({percentage:.1f}%)")
    
    print(f"\n📅 Daily Distribution (Top 10):")
    sorted_dates = sorted(summary['daily_distribution'].items(), key=lambda x: x[1], reverse=True)
    for date, count in sorted_dates[:10]:
        print(f"   {date}: {count} emails")
    
    print(f"\n👥 Client Codes Found ({len(summary['all_client_codes'])}):")
    for code in sorted(summary['all_client_codes']):
        print(f"   {code}")
    
    print(f"\n💰 Amount Analysis:")
    if summary['all_amounts']:
        print(f"   Total Amounts: {len(summary['all_amounts'])}")
        print(f"   Total Value: ₹{sum(summary['all_amounts']):,.2f}")
        print(f"   Average Amount: ₹{sum(summary['all_amounts'])/len(summary['all_amounts']):,.2f}")
        print(f"   Min Amount: ₹{min(summary['all_amounts']):,.2f}")
        print(f"   Max Amount: ₹{max(summary['all_amounts']):,.2f}")
    
    print(f"\n🏢 Account Names Found ({len(summary['all_account_names'])}):")
    for name in sorted(summary['all_account_names'])[:10]:  # Show first 10
        print(f"   {name}")
    if len(summary['all_account_names']) > 10:
        print(f"   ... and {len(summary['all_account_names']) - 10} more")
    
    # Determine next steps
    print(f"\n🚀 NEXT STEPS RECOMMENDATIONS")
    print("=" * 40)
    
    if summary['content_types'].get('trade_instruction', 0) > 0:
        print(f"✅ {summary['content_types']['trade_instruction']} TRADE INSTRUCTION emails found")
        print("   → Extract order details (buy/sell, quantity, price)")
        print("   → Match with audio orders for validation")
    
    if summary['content_types'].get('debit_list', 0) > 0:
        print(f"✅ {summary['content_types']['debit_list']} DEBIT LIST emails found")
        print("   → Extract client codes and amounts for surveillance")
        print("   → Map to UCC database for client identification")
    
    if summary['content_types'].get('trial_balance', 0) > 0:
        print(f"✅ {summary['content_types']['trial_balance']} TRIAL BALANCE emails found")
        print("   → Extract account balances and client information")
        print("   → Monitor for unusual balance changes")
    
    if len(summary['all_client_codes']) > 0:
        print(f"✅ {len(summary['all_client_codes'])} CLIENT CODES identified")
        print("   → Cross-reference with UCC database")
        print("   → Create client mapping for surveillance")
    
    if len(summary['all_amounts']) > 0:
        print(f"✅ {len(summary['all_amounts'])} AMOUNTS extracted")
        print("   → Analyze for unusual transaction patterns")
        print("   → Set up amount-based alerts")
    
    print(f"\n📁 Analysis saved to: email_processing/comprehensive_dealing_emails_analysis.json")
    
    # Create actionable recommendations
    recommendations = {
        'immediate_actions': [
            "Set up daily email monitoring for new dealing emails",
            "Create client code mapping with UCC database",
            "Implement amount-based alerting system",
            "Develop email content parsing pipeline",
            f"Process {summary['total_emails']} emails daily for surveillance"
        ],
        'integration_steps': [
            "Merge email data with audio processing results",
            "Create unified client identification system",
            "Develop comprehensive surveillance dashboard",
            "Set up automated daily reporting"
        ],
        'data_quality': [
            f"Found {len(summary['all_client_codes'])} unique client codes",
            f"Extracted {len(summary['all_amounts'])} financial amounts",
            f"Identified {len(summary['all_account_names'])} account names",
            f"Processed {summary['total_emails']} emails with {len(summary['content_types'])} content types",
            "Email structure is consistent and parseable"
        ],
        'surveillance_coverage': {
            'total_emails': summary['total_emails'],
            'unique_clients': len(summary['all_client_codes']),
            'total_amount': sum(summary['all_amounts']) if summary['all_amounts'] else 0,
            'content_types': len(summary['content_types']),
            'daily_volume': max(summary['daily_distribution'].values()) if summary['daily_distribution'] else 0
        }
    }
    
    with open("email_processing/comprehensive_email_recommendations.json", "w") as f:
        json.dump(recommendations, f, indent=2, ensure_ascii=False)
    
    print(f"📋 Recommendations saved to: email_processing/comprehensive_email_recommendations.json")

if __name__ == "__main__":
    main() 