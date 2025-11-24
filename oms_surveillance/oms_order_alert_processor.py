#!/usr/bin/env python3
"""
OMS Order Alert Email Processor
Specialized processor for OMS Order Alert emails with fixed structure parsing.
"""

import json
import re
import os
from datetime import datetime
from typing import Dict, List, Any

def analyze_oms_order_alert_email(subject: str, sender: str, clean_text: str, attachment_info: str = "", html_content: str = "") -> Dict[str, Any]:
    """
    Analyze OMS Order Alert email using Python regex (no AI needed for fixed structure).
    
    Args:
        subject: Email subject
        sender: Email sender
        clean_text: Cleaned email text content (fallback)
        attachment_info: Any attachment information
        html_content: HTML content of email (preferred for parsing)
    
    Returns:
        Dictionary with analysis results
    """
    
    # Create result structure
    result = {
        "ai_email_intent": "oms_order_alert",
        "ai_confidence_score": "100",
        "ai_reasoning": "Fixed structure OMS order alert parsed with Python regex",
        "ai_order_details": [],
        "ai_instruction_type": "oms_alert"
    }
    
    # Parse HTML table structure from real OMS emails
    all_orders = []
    
    # PERMANENT FIX: Use HTML content if available (preferred), otherwise fallback to clean_text
    # HTML content has proper table structure that can be parsed reliably
    content_to_parse = html_content if html_content else clean_text
    
    # Extract data from HTML table structure using a more flexible approach
    # Find ALL table rows with data (not just the first one)
    table_row_pattern = r'<tr><td[^>]*>([^<]+)</td><td[^>]*>([^<]*)</td><td[^>]*>([^<]+)</td><td[^>]*>([^<]+)</td><td[^>]*>([^<]+)</td><td[^>]*>([^<]+)</td><td[^>]*>([^<]+)</td><td[^>]*>([^<]+)</td><td[^>]*>([^<]+)</td><td[^>]*>([^<]+)</td></tr>'
    
    table_matches = re.findall(table_row_pattern, content_to_parse, re.IGNORECASE | re.DOTALL)
    if table_matches:
        for match in table_matches:
            # Extract table data in order: Ref.no, Trade Date, Client Code, Client Name, Account Type, Product, Transaction Type, Scheme/Scrip, ISIN, LOB
            ref_no = match[0].strip()
            trade_date = match[1].strip()
            client_code = match[2].strip()
            client_name = match[3].strip()
            account_type = match[4].strip()
            product = match[5].strip()
            transaction_type = match[6].strip()
            symbol = match[7].strip()
            isin = match[8].strip()
            lob = match[9].strip()
            
            order_details = {
                'ref_no': ref_no,
                'trade_date': trade_date,
                'client_code': client_code,
                'client_name': client_name,
                'account_type': account_type,
                'product': product,
                'side': transaction_type,
                'symbol': symbol,
                'isin': isin,
                'lob': lob
            }
            all_orders.append(order_details)
    else:
        # Fallback: Extract from clean_text using known patterns
        # The clean_text contains: "BUY00644105897RAJANI SARANNON-POALISTED EQBUYMANAPPURAM FINANCE LTDINE522D01027NWM"
        
        # Extract ALL reference numbers first
        order_refs = re.findall(r'(BUY\d{5}|SELL\d{5})', clean_text)
        for ref_no in order_refs:
            order_details = {}
            order_details['ref_no'] = ref_no
            
            # Extract client code - 6 digits after the order ref
            client_code_match = re.search(rf'{ref_no}(\d{{6}})', clean_text)
            if client_code_match:
                order_details['client_code'] = client_code_match.group(1)
            
            # Extract client name - between client code and account type
            if 'client_code' in order_details:
                client_name_pattern = rf'{order_details["client_code"]}([A-Z\s]+?)(?:POA|NON-POA)'
                client_name_match = re.search(client_name_pattern, clean_text)
                if client_name_match:
                    order_details['client_name'] = client_name_match.group(1).strip()
            
            # Extract account type
            if 'POA' in clean_text:
                order_details['account_type'] = 'POA'
            elif 'NON-POA' in clean_text:
                order_details['account_type'] = 'NON-POA'
            
            # Extract product
            if 'LISTED EQ' in clean_text:
                order_details['product'] = 'LISTED EQ'
            
            # Extract transaction type
            if ref_no.startswith('BUY'):
                order_details['side'] = 'BUY'
            elif ref_no.startswith('SELL'):
                order_details['side'] = 'SELL'
            
            # Extract symbol and ISIN - look for common patterns
            symbol_patterns = [
                r'MANAPPURAM FINANCE LTD',
                r'EDELWEISS FINANCIAL SERVICES LTD',
                r'ICICI PRUDENTIAL BSE LIQUID RATE ETF',
                r'NIPPON INDIA NIFTY 1D RATE LIQUID BEES ETF',
                r'SONA BLW PRECISION FORGINGS LTD'
            ]
            
            for pattern in symbol_patterns:
                if pattern in clean_text:
                    order_details['symbol'] = pattern
                    break
            
            # Extract ISIN
            isin_match = re.search(r'INE[A-Z0-9]{9}', clean_text)
            if isin_match:
                order_details['isin'] = isin_match.group(0)
            
            # Extract LOB
            if 'NWM' in clean_text:
                order_details['lob'] = 'NWM'
            elif 'NWP' in clean_text:
                order_details['lob'] = 'NWP'
            
            all_orders.append(order_details)
    
    # If we found order details, add them to the result
    if all_orders:
        ai_order_details_list = []
        for order_details in all_orders:
            # Map to the expected output format
            ai_order_details = {
                'client_code': order_details.get('client_code'),
                'symbol': order_details.get('symbol'),
                'quantity': None,  # Not available in OMS emails
                'price': None,     # Not available in OMS emails
                'buy_sell': order_details.get('side'),
                'order_time': None,  # Not available in OMS emails
                'order_id': order_details.get('ref_no'),
                'isin': order_details.get('isin'),
                'client_name': order_details.get('client_name'),
                'lob': order_details.get('lob')
            }
            ai_order_details_list.append(ai_order_details)
        
        result['ai_order_details'] = ai_order_details_list
    
    return result

def create_empty_oms_results_file() -> str:
    """
    Create an empty but valid OMS results file when no emails are found.
    
    Returns:
        Path to empty results file
    """
    
    try:
        # Create empty output structure
        output_data = {
            'oms_order_alerts': [],
            'processing_summary': {
                'total_emails_processed': 0,
                'total_orders_found': 0,
                'processing_timestamp': datetime.now().isoformat(),
                'processor_version': '1.0.0',
                'status': 'no_emails_found'
            }
        }
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"complete_oms_surveillance_results_{timestamp}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n📊 OMS Order Alert Processing Summary:")
        print(f"   📋 Total emails: 0")
        print(f"   ✅ Processed successfully: 0")
        print(f"   ❌ Failed: 0")
        print(f"   📋 Total orders found: 0")
        print(f"   ℹ️  No OMS emails found for this date (this is normal)")
        print(f"📁 OMS order alert results saved to: {output_file}")
        
        return output_file
        
    except Exception as e:
        print(f"❌ Error creating empty OMS results file: {e}")
        return None

def process_oms_emails_from_file(input_file: str) -> str:
    """
    Process OMS order alert emails from a JSON file.
    
    Args:
        input_file: Path to input JSON file containing emails
    
    Returns:
        Path to output JSON file with analysis results
    """
    
    print(f"📋 Processing OMS order alert emails from: {input_file}")
    
    # Load emails from file
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Error loading input file: {e}")
        return None
    
    # Filter for OMS order alert emails only
    oms_emails = []
    for email in data.get('email_analyses', []):
        subject = email.get('subject', '')
        if 'New Order Alert - OMS!' in subject:
            oms_emails.append(email)
    
    emails = oms_emails
    print(f"📋 Found {len(data.get('email_analyses', []))} total emails, {len(emails)} OMS order alert emails to process")
    
    if not emails:
        print("📋 No OMS order alert emails found to process")
        # Create an empty but valid output file to indicate successful processing with no results
        return create_empty_oms_results_file()
    
    # Process each OMS email
    processed_emails = []
    total_orders = 0
    
    for i, email in enumerate(emails, 1):
        print(f"📋 Processing OMS email {i}/{len(emails)}: {email.get('subject', 'N/A')}")
        
        try:
            # Analyze the OMS email
            # PERMANENT FIX: Pass HTML content for reliable parsing (Option 2)
            # HTML has fixed table structure that can be parsed correctly per-row
            html_content = email.get('body', {}).get('content', '') if isinstance(email.get('body'), dict) else ''
            
            analysis = analyze_oms_order_alert_email(
                subject=email.get('subject', ''),
                sender=email.get('sender', ''),
                clean_text=email.get('clean_text', ''),
                attachment_info=email.get('attachment_info', ''),
                html_content=html_content
            )
            
            # Create processed email structure
            processed_email = {
                'email_id': f"oms_{i}",
                'subject': email.get('subject', ''),
                'sender': email.get('sender', ''),
                'date': email.get('date', ''),
                'ai_analysis': analysis,
                'original_email': email
            }
            
            processed_emails.append(processed_email)
            
            # Count orders found
            orders_found = len(analysis.get('ai_order_details', []))
            total_orders += orders_found
            print(f"   ✅ Found {orders_found} order(s)")
            
        except Exception as e:
            print(f"   ❌ Error processing email: {e}")
            continue
    
    # Create output structure
    output_data = {
        'oms_order_alerts': processed_emails,
        'processing_summary': {
            'total_emails_processed': len(processed_emails),
            'total_orders_found': total_orders,
            'processing_timestamp': datetime.now().isoformat(),
            'processor_version': '1.0.0'
        }
    }
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"complete_oms_surveillance_results_{timestamp}.json"
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n📊 OMS Order Alert Processing Summary:")
        print(f"   📋 Total emails: {len(processed_emails)}")
        print(f"   ✅ Processed successfully: {len(processed_emails)}")
        print(f"   ❌ Failed: {len(emails) - len(processed_emails)}")
        print(f"   📋 Total orders found: {total_orders}")
        print(f"📁 OMS order alert results saved to: {output_file}")
        
        return output_file
        
    except Exception as e:
        print(f"❌ Error saving results: {e}")
        return None

def main():
    """Main function to process OMS order alert emails."""
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python oms_order_alert_processor.py <input_json_file>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    
    if not os.path.exists(input_file):
        print(f"❌ Input file not found: {input_file}")
        sys.exit(1)
    
    print("🚀 OMS Order Alert Email Processor")
    print("=" * 50)
    print("This processor handles OMS Order Alert emails with fixed structure parsing.")
    print("=" * 50)
    
    output_file = process_oms_emails_from_file(input_file)
    
    if output_file:
        print(f"\n✅ OMS order alert processing completed successfully!")
        print(f"📁 Results saved to: {output_file}")
    else:
        print(f"\n❌ OMS order alert processing failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
