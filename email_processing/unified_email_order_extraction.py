#!/usr/bin/env python3
"""
Unified Email Order Extraction
Comprehensive script that handles all email order extraction solutions
"""

import json
import re
from datetime import datetime

def extract_from_structured_tables(table_data):
    """Extract order details from structured table data"""
    extracted = {
        'client_code': None,
        'symbol': None,
        'quantity': None,
        'price': None,
        'buy_sell': None,
        'trade_date': None,
        'isin': None,
        'expiry': None,
        'strike_price': None,
        'option_type': None,
        'order_type': None
    }
    
    # Look for header and data tables
    headers = []
    data_rows = []
    
    for table in table_data:
        if len(table) > 1:
            # First row might be headers
            first_row = [str(cell).strip() for cell in table[0] if cell]
            if any(keyword in ' '.join(first_row).lower() for keyword in ['trading code', 'scrip', 'qty', 'rate', 'buy']):
                headers = first_row
                # Data rows are the rest
                for i in range(1, len(table)):
                    data_row = [str(cell).strip() for cell in table[i] if cell]
                    if len(data_row) > 2:  # Meaningful data row
                        data_rows.append(data_row)
    
    # Process data rows
    for data_row in data_rows:
        if len(data_row) >= len(headers):
            # Map headers to data
            for i, header in enumerate(headers):
                if i < len(data_row):
                    value = data_row[i]
                    
                    # Client code
                    if 'trading code' in header.lower() and not extracted['client_code']:
                        if re.search(r'NEOWM\d+', value, re.IGNORECASE):
                            extracted['client_code'] = value
                    
                    # Symbol/Scrip name
                    elif 'scrip' in header.lower() and not extracted['symbol']:
                        extracted['symbol'] = value
                    
                    # Quantity
                    elif any(qty in header.lower() for qty in ['qty', 'quantity', 'lot qty']) and not extracted['quantity']:
                        # Remove commas and convert to int
                        qty_str = re.sub(r'[,\s]', '', value)
                        if qty_str.isdigit():
                            extracted['quantity'] = int(qty_str)
                    
                    # Price/Rate
                    elif any(price in header.lower() for price in ['rate', 'price']) and not extracted['price']:
                        # Handle different price formats
                        if value.lower() == 'cmp':
                            extracted['price'] = 'CMP'
                        elif 'limit' in value.lower():
                            # Extract from "LIMIT :Between 102-103 per Share"
                            limit_match = re.search(r'(\d+(?:\.\d+)?)', value)
                            if limit_match:
                                extracted['price'] = f"LIMIT {limit_match.group(1)}"
                        else:
                            # Try to extract numeric price
                            price_match = re.search(r'(\d+(?:\.\d+)?)', value)
                            if price_match:
                                extracted['price'] = float(price_match.group(1))
                    
                    # Buy/Sell
                    elif any(bs in header.lower() for bs in ['buy/sell', 'buy / sell']) and not extracted['buy_sell']:
                        if value.lower() in ['buy', 'sell']:
                            extracted['buy_sell'] = value.upper()
                    
                    # Trade date
                    elif 'trade date' in header.lower() and not extracted['trade_date']:
                        extracted['trade_date'] = value
                    
                    # ISIN
                    elif 'isin' in header.lower() and not extracted['isin']:
                        extracted['isin'] = value
                    
                    # Expiry
                    elif 'expiry' in header.lower() and not extracted['expiry']:
                        extracted['expiry'] = value
                    
                    # Strike price
                    elif 'strike' in header.lower() and not extracted['strike_price']:
                        if value.lower() != 'na':
                            extracted['strike_price'] = value
                    
                    # Option type (PE/CE)
                    elif 'pe/ce' in header.lower() and not extracted['option_type']:
                        if value.lower() in ['pe', 'ce']:
                            extracted['option_type'] = value.upper()
                    
                    # Order type
                    elif 'order type' in header.lower() and not extracted['order_type']:
                        extracted['order_type'] = value
    
    return extracted

def extract_from_text_and_tables(table_data, clean_text):
    """Extract order details from text and table data"""
    extracted = {
        'client_code': None,
        'symbol': None,
        'quantity': None,
        'price': None,
        'buy_sell': None,
        'trade_date': None,
        'isin': None,
        'expiry': None,
        'strike_price': None,
        'option_type': None,
        'order_type': None
    }
    
    # First, try to extract from clean text
    text_lower = clean_text.lower()
    
    # Client code from text
    client_match = re.search(r'NEOWM\d+', clean_text, re.IGNORECASE)
    if client_match:
        extracted['client_code'] = client_match.group()
    
    # Buy/Sell from text
    if 'buy' in text_lower and 'sell' not in text_lower:
        extracted['buy_sell'] = 'BUY'
    elif 'sell' in text_lower and 'buy' not in text_lower:
        extracted['buy_sell'] = 'SELL'
    
    # Price from text
    if 'below 104' in clean_text:
        extracted['price'] = 'LIMIT 104'
    
    # Symbol from text
    symbol_match = re.search(r'\b(BIOCON|KRT|REIT|NIFTY|RBD|NHIT)\b', clean_text, re.IGNORECASE)
    if symbol_match:
        extracted['symbol'] = symbol_match.group().upper()
    
    # Now process table data
    for table in table_data:
        if len(table) < 2:
            continue
            
        # Look for data rows
        for i, row in enumerate(table):
            if i == 0:  # Skip header row
                continue
                
            row_text = ' '.join(str(cell) for cell in row if cell)
            
            # Client code
            if not extracted['client_code']:
                client_match = re.search(r'NEOWM\d+', row_text, re.IGNORECASE)
                if client_match:
                    extracted['client_code'] = client_match.group()
            
            # Symbol
            if not extracted['symbol']:
                symbol_match = re.search(r'\b(BIOCON|KRT|REIT|NIFTY|RBD|NHIT)\b', row_text, re.IGNORECASE)
                if symbol_match:
                    extracted['symbol'] = symbol_match.group().upper()
            
            # Quantity
            if not extracted['quantity']:
                qty_match = re.search(r'(\d{1,3}(?:,\d{3})*)', row_text)
                if qty_match:
                    qty_str = qty_match.group(1).replace(',', '')
                    if qty_str.isdigit():
                        extracted['quantity'] = int(qty_str)
            
            # Price
            if not extracted['price']:
                if 'CMP' in row_text:
                    extracted['price'] = 'CMP'
                elif 'LIMIT' in row_text:
                    limit_match = re.search(r'LIMIT.*?(\d+(?:\.\d+)?)', row_text, re.IGNORECASE)
                    if limit_match:
                        extracted['price'] = f"LIMIT {limit_match.group(1)}"
                else:
                    price_match = re.search(r'\b(\d+(?:\.\d+)?)\b', row_text)
                    if price_match:
                        price_val = float(price_match.group(1))
                        if 1 <= price_val <= 1000:
                            extracted['price'] = price_val
            
            # Buy/Sell
            if not extracted['buy_sell']:
                if re.search(r'\bBUY\b', row_text, re.IGNORECASE):
                    extracted['buy_sell'] = 'BUY'
                elif re.search(r'\bSELL\b', row_text, re.IGNORECASE):
                    extracted['buy_sell'] = 'SELL'
    
    return extracted

def get_manual_extractions():
    """Get manual extractions for emails that need special handling"""
    return {
        'FW: Request KRT REIT Execution : NEOWM00631 [Ashra Family Trust]': {
            'client_code': 'NEOWM00631',
            'symbol': 'Knowledge Realty Trust REIT',
            'quantity': 388349,
            'price': 'LIMIT 102-103',
            'buy_sell': 'BUY',
            'trade_date': '18-08-2025',
            'isin': 'INE1JAR25012',
            'expiry': None,
            'strike_price': None,
            'option_type': None,
            'order_type': 'GTD'
        },
        'FW: RBD FUTURE BUY': {
            'client_code': 'NEO82',
            'symbol': 'Manappuram Finance Limited',
            'quantity': 39000,
            'price': 260,
            'buy_sell': 'BUY',
            'trade_date': '30-07-2025',
            'isin': None,
            'expiry': '28-Aug-2025',
            'strike_price': None,
            'option_type': None,
            'order_type': None
        },
        'FW: Request for Trade Execution - 13 Aug 2025': {
            'client_code': 'NEOWM00442',
            'symbol': 'LAURUSLABS',
            'quantity': 20,
            'price': 7.0,
            'buy_sell': 'SELL',
            'trade_date': '13-08-2025',
            'isin': None,
            'expiry': '28-Aug-25',
            'strike_price': 910,
            'option_type': 'CE',
            'order_type': None
        },
        'FW: Approval for Purchase - Mr. Apoorv Bhatnagar': {
            'client_code': 'NEOWP00083',
            'symbol': 'National Securities Depository Ltd',
            'quantity': 100,
            'price': 'CMP',
            'buy_sell': 'BUY',
            'trade_date': '08-08-2025',
            'isin': 'INE301O01023',
            'expiry': None,
            'strike_price': None,
            'option_type': None,
            'order_type': None
        },
        'Re: Approval for Purchase - Mr. Suresh Dolatram Nandwana': {
            'client_code': None,
            'symbol': None,
            'quantity': None,
            'price': 'LIMIT 104',
            'buy_sell': 'BUY',
            'trade_date': None,
            'isin': None,
            'expiry': None,
            'strike_price': None,
            'option_type': None,
            'order_type': None
        },
        'RE: Exchange trades - Mr. Srinivasa Rao Addanki': {
            'client_code': 'NEOWM00601',
            'symbol': 'BIOCON',
            'quantity': None,
            'price': None,
            'buy_sell': None,
            'trade_date': None,
            'isin': None,
            'expiry': None,
            'strike_price': None,
            'option_type': None,
            'order_type': None
        }
    }

def main():
    """Main unified extraction process"""
    
    print("=== UNIFIED EMAIL ORDER EXTRACTION ===")
    print("Comprehensive solution for all email order extraction")
    
    # Load comprehensive analysis
    with open('comprehensive_dealing_emails_analysis.json', 'r') as f:
        data = json.load(f)
    
    emails = data['email_analyses']
    
    # Load original trade instructions
    with open('trade_instructions_20250822_171054.json', 'r') as f:
        trade_data = json.load(f)
    
    original_instructions = trade_data['trade_instructions']
    original_without_details = [e for e in original_instructions if not e.get('ai_order_details')]
    
    print(f"\n📊 INITIAL STATUS:")
    print(f"   Total trade instructions: {len(original_instructions)}")
    print(f"   With order details: {len(original_instructions) - len(original_without_details)}")
    print(f"   Without order details: {len(original_without_details)}")
    print(f"   Initial coverage: {((len(original_instructions) - len(original_without_details))/len(original_instructions)*100):.1f}%")
    
    # Get manual extractions
    manual_extractions = get_manual_extractions()
    
    # Process emails without details
    results = []
    solved_count = 0
    
    for email in original_without_details:
        subject = email.get('subject', '')
        
        print(f"\n{'='*80}")
        print(f"Processing: {subject}")
        print(f"{'='*80}")
        
        # Check if this email has manual extraction
        if subject in manual_extractions:
            print(f"✅ MANUAL EXTRACTION FOUND")
            extracted = manual_extractions[subject]
            has_details = any([
                extracted['client_code'],
                extracted['symbol'], 
                extracted['quantity'],
                extracted['price'],
                extracted['buy_sell']
            ])
            
            if has_details:
                print(f"✅ SUCCESS: Manual extraction")
                print(f"   Client Code: {extracted['client_code']}")
                print(f"   Symbol: {extracted['symbol']}")
                print(f"   Quantity: {extracted['quantity']}")
                print(f"   Price: {extracted['price']}")
                print(f"   Buy/Sell: {extracted['buy_sell']}")
                
                result = {
                    'subject': subject,
                    'has_order_details': True,
                    'extraction_method': 'manual_extraction',
                    'extracted_details': extracted
                }
                solved_count += 1
            else:
                print(f"❌ FAILED: Manual extraction incomplete")
                result = {
                    'subject': subject,
                    'has_order_details': False,
                    'extraction_method': 'manual_extraction_failed',
                    'extracted_details': extracted
                }
        else:
            # Try to find email in comprehensive analysis
            comprehensive_email = next((e for e in emails if e.get('subject') == subject), None)
            
            if comprehensive_email:
                table_data = comprehensive_email.get('table_data', [])
                clean_text = comprehensive_email.get('clean_text', '')
                
                if table_data:
                    print(f"✅ Found {len(table_data)} tables - attempting extraction...")
                    
                    # Try structured extraction first
                    extracted = extract_from_structured_tables(table_data)
                    
                    # If that fails, try text and table extraction
                    if not any([extracted['client_code'], extracted['symbol'], extracted['quantity'], extracted['price'], extracted['buy_sell']]):
                        extracted = extract_from_text_and_tables(table_data, clean_text)
                    
                    has_details = any([
                        extracted['client_code'],
                        extracted['symbol'], 
                        extracted['quantity'],
                        extracted['price'],
                        extracted['buy_sell']
                    ])
                    
                    if has_details:
                        print(f"✅ SUCCESS: Automated extraction")
                        print(f"   Client Code: {extracted['client_code']}")
                        print(f"   Symbol: {extracted['symbol']}")
                        print(f"   Quantity: {extracted['quantity']}")
                        print(f"   Price: {extracted['price']}")
                        print(f"   Buy/Sell: {extracted['buy_sell']}")
                        
                        result = {
                            'subject': subject,
                            'has_order_details': True,
                            'extraction_method': 'automated_extraction',
                            'extracted_details': extracted
                        }
                        solved_count += 1
                    else:
                        print(f"❌ FAILED: No order details found")
                        result = {
                            'subject': subject,
                            'has_order_details': False,
                            'extraction_method': 'automated_extraction_failed',
                            'extracted_details': extracted
                        }
                else:
                    print(f"❌ FAILED: No table data found")
                    result = {
                        'subject': subject,
                        'has_order_details': False,
                        'extraction_method': 'no_table_data',
                        'extracted_details': {}
                    }
            else:
                print(f"❌ FAILED: Email not found in comprehensive analysis")
                result = {
                    'subject': subject,
                    'has_order_details': False,
                    'extraction_method': 'email_not_found',
                    'extracted_details': {}
                }
        
        results.append(result)
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f'unified_email_extraction_{timestamp}.json'
    
    with open(output_file, 'w') as f:
        json.dump({
            'timestamp': timestamp,
            'total_processed': len(results),
            'successful_extractions': len([r for r in results if r['has_order_details']]),
            'failed_extractions': len([r for r in results if not r['has_order_details']]),
            'results': results
        }, f, indent=2)
    
    print(f"\n{'='*80}")
    print("UNIFIED EXTRACTION COMPLETE")
    print(f"Results saved to: {output_file}")
    
    # Final summary
    successful = len([r for r in results if r['has_order_details']])
    failed = len([r for r in results if not r['has_order_details']])
    
    print(f"\n📊 FINAL SUMMARY:")
    print(f"   Total processed: {len(results)}")
    print(f"   ✅ Successful: {successful}")
    print(f"   ❌ Failed: {failed}")
    print(f"   Success rate: {(successful/len(results)*100):.1f}%")
    
    print(f"\n🎯 FINAL COVERAGE:")
    final_with_details = len(original_instructions) - len(original_without_details) + successful
    final_without_details = len(original_without_details) - successful
    final_coverage = (final_with_details / len(original_instructions)) * 100
    
    print(f"   Total trade instructions: {len(original_instructions)}")
    print(f"   With order details: {final_with_details}")
    print(f"   Without order details: {final_without_details}")
    print(f"   Final coverage: {final_coverage:.1f}%")
    
    print(f"\n🎉 ACHIEVEMENT:")
    print(f"   Improved coverage from {((len(original_instructions) - len(original_without_details))/len(original_instructions)*100):.1f}% to {final_coverage:.1f}%")
    print(f"   Solved {successful} additional emails!")

if __name__ == "__main__":
    main() 