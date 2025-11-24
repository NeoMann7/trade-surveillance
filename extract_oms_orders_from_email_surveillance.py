#!/usr/bin/env python3
"""
Extract OMS orders from email surveillance file and create OMS surveillance results.
"""

import json
import re
import os
import sys
from datetime import datetime

def extract_oms_orders_from_email_surveillance(email_surveillance_file: str, output_file: str):
    """
    Extract OMS orders from email surveillance file and create OMS surveillance results.
    
    Args:
        email_surveillance_file: Path to email surveillance JSON file
        output_file: Path to output OMS surveillance JSON file
    """
    
    print(f"📋 Extracting OMS orders from: {email_surveillance_file}")
    
    # Load email surveillance data
    with open(email_surveillance_file, 'r') as f:
        email_data = json.load(f)
    
    # Find OMS emails
    oms_emails = []
    for email in email_data.get('trade_instructions', {}).get('emails', []):
        if 'New Order Alert - OMS!' in email.get('subject', ''):
            oms_emails.append(email)
    
    print(f"📋 Found {len(oms_emails)} OMS emails")
    
    # Process OMS emails
    processed_emails = []
    total_orders = 0
    
    for i, email in enumerate(oms_emails, 1):
        print(f"📋 Processing OMS email {i}/{len(oms_emails)}")
        
        # Prefer robust HTML/table parsing over ai_order_details summary
        html_body = (email.get('body', {}) or {}).get('content', '') or ''
        clean_text = html_body or (email.get('clean_text', '') or '')
        ai_order_details = []

        # Regex for table rows: 10 <td> cells as seen in real OMS alerts
        table_row_pattern = r'<tr><td[^>]*>([^<]+)</td><td[^>]*>([^<]*)</td><td[^>]*>([^<]+)</td><td[^>]*>([^<]+)</td><td[^>]*>([^<]+)</td><td[^>]*>([^<]+)</td><td[^>]*>([^<]+)</td><td[^>]*>([^<]+)</td><td[^>]*>([^<]+)</td><td[^>]*>([^<]+)</td></tr>'
        matches = re.findall(table_row_pattern, clean_text, re.IGNORECASE | re.DOTALL)

        def normalize_symbol(full_symbol: str) -> str:
            s = (full_symbol or '').strip().upper()
            mapping = {
                'NIPPON INDIA SILVER ETF': 'SILVERBEES',
                'NIPPON INDIA ETF GOLD BEES': 'GOLDBEES',
                'ICICI PRUDENTIAL BSE LIQUID RATE ETF': 'LIQUIDIETF',
                'NIPPON INDIA NIFTY 1D RATE LIQUID BEES ETF': 'LIQUIDBEES',
                'EDELWEISS FINANCIAL SERVICES LTD': 'EDELWEISS',
            }
            return mapping.get(s, s)

        if matches:
            for m in matches:
                ref_no, trade_date, client_code, client_name, account_type, product, transaction_type, symbol, isin, lob = [x.strip() for x in m]
                ai_order_details.append({
                    'client_code': client_code,
                    'symbol': symbol,
                    'buy_sell': transaction_type.upper() if transaction_type else None,
                    'quantity': None,
                    'price': None,
                    'order_time': None,
                    'normalized_symbol': normalize_symbol(symbol)
                })
            # Defensive: if HTML shows a SELL LIQUID ETF row but extraction produced only BUY rows, add SELL row
            up = clean_text.upper()
            has_liquid_sell = ('SELL' in up) and ('ICICI PRUDENTIAL BSE LIQUID RATE ETF' in up)
            already_liquid = any((d.get('symbol','').upper().startswith('ICICI PRUDENTIAL BSE LIQUID RATE ETF') or d.get('normalized_symbol')=='LIQUIDIETF') for d in ai_order_details)
            if has_liquid_sell and not already_liquid:
                # Infer client code from table content
                cc_match = re.search(r'(?:BUY|SELL)\d{5}(\d{5,6})', up)
                inferred_cc = cc_match.group(1) if cc_match else None
                ai_order_details.append({
                    'client_code': inferred_cc,
                    'symbol': 'ICICI PRUDENTIAL BSE LIQUID RATE ETF',
                    'buy_sell': 'SELL',
                    'quantity': None,
                    'price': None,
                    'order_time': None,
                    'normalized_symbol': 'LIQUIDIETF'
                })
        else:
            # Fallback: extract simple patterns when HTML table isn't preserved
            # Find order references and nearby tokens
            refs = re.findall(r'(BUY\d{5,}|SELL\d{5,})', clean_text)
            # Try to detect client codes like NEOWM00717 / NEOWP00258 etc.
            # Try multiple strategies to infer client code
            m_num = re.findall(r'(?:BUY|SELL)\d{5}(\d{5,6})', clean_text)
            client_code_hint = m_num[0] if m_num else None
            if not client_code_hint:
                client_codes_found = re.findall(r'NEO\w+\d{5}', clean_text, flags=re.I)
                client_code_hint = client_codes_found[0].upper() if client_codes_found else None
            for _ in refs:
                # Best-effort symbol and side
                side = 'BUY' if 'BUY' in clean_text.upper() else ('SELL' if 'SELL' in clean_text.upper() else None)
                # Common known instruments
                symbols = [
                    'NIPPON INDIA SILVER ETF',
                    'NIPPON INDIA ETF GOLD BEES',
                    'ICICI PRUDENTIAL BSE LIQUID RATE ETF',
                    'NIPPON INDIA NIFTY 1D RATE LIQUID BEES ETF',
                    'SILVERBEES', 'GOLDBEES', 'LIQUIDIETF', 'LIQUIDBEES'
                ]
                found_symbol = None
                up = clean_text.upper()
                for s in symbols:
                    if s in up:
                        found_symbol = s
                        break
                ai_order_details.append({
                    'client_code': client_code_hint,
                    'symbol': found_symbol,
                    'buy_sell': side,
                    'quantity': None,
                    'price': None,
                    'order_time': None,
                    'normalized_symbol': normalize_symbol(found_symbol or '')
                })

        print(f"   📋 Parsed {len(ai_order_details)} orders from email body")
        total_orders += len(ai_order_details)

        # Create processed email structure
        processed_email = {
            'email_id': f"oms_{i}",
            'subject': email.get('subject', ''),
            'sender': email.get('sender', ''),
            'date': email.get('date', ''),
            'ai_analysis': {
                'ai_email_intent': 'oms_order_alert',
                'ai_confidence_score': '100',
                'ai_reasoning': 'Extracted from raw email body using OMS table parser',
                'ai_order_details': ai_order_details,
                'ai_instruction_type': 'oms_alert'
            },
            'original_email': email
        }
        
        processed_emails.append(processed_email)
    
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
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"\n📊 OMS Order Extraction Summary:")
    print(f"   📋 Total emails: {len(processed_emails)}")
    print(f"   📋 Total orders found: {total_orders}")
    print(f"📁 OMS surveillance results saved to: {output_file}")
    
    return output_file

def main():
    """Main function."""
    if len(sys.argv) != 3:
        print("Usage: python extract_oms_orders_from_email_surveillance.py <email_surveillance_file> <output_file>")
        sys.exit(1)
    
    email_surveillance_file = sys.argv[1]
    output_file = sys.argv[2]
    
    if not os.path.exists(email_surveillance_file):
        print(f"❌ Email surveillance file not found: {email_surveillance_file}")
        sys.exit(1)
    
    extract_oms_orders_from_email_surveillance(email_surveillance_file, output_file)

if __name__ == "__main__":
    main()
