import json
import os
from openai import OpenAI
from dotenv import load_dotenv
import pandas as pd
from datetime import datetime
import re

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def analyze_email_with_ai_gpt41(email_body, subject, sender):
    """Analyze email with gpt-4.1-mini using entire email body."""
    
    prompt = f"""
    You are a trade surveillance analyst. Analyze this email to determine if it contains a trade instruction and extract order details.

    **TRADE INSTRUCTION DEFINITION:**
    A trade instruction is any email that contains a request to execute, modify, or cancel a trade order. This includes:
    - Direct buy/sell requests
    - Order modifications (price changes, quantity changes)
    - Order cancellations
    - Forwarded trade requests from clients
    - Trade confirmations with new instructions

    **EMAIL TO ANALYZE:**
    Subject: {subject}
    Sender: {sender}
    Body: {email_body}

    **ANALYSIS INSTRUCTIONS:**
    1. First, determine if this is a trade instruction based on the definition above
    2. If it's a trade instruction, extract order details from the email content
    3. Look for tables, structured data, or text that contains trade information
    4. Extract EXACT values - do not make up or estimate values
    5. If a value is not present, use null

    **ORDER DETAILS TO EXTRACT:**
    1. Client Code (e.g., NEOWM00123, NEOC4, NEO135)
    2. Symbol (e.g., NIFTY, KRT, NHIT, YASHO INDUSTRIES)
    3. Quantity (numeric value)
    4. Price (numeric value)
    5. Buy/Sell (BUY or SELL)
    6. Order Time (if explicitly mentioned)

    **CRITICAL:**
    - Extract EXACT values from the email content
    - Do NOT make up or estimate values
    - If a value is not present in the email, use null
    - Pay attention to tables, structured data, and any trade-related information

    Return a JSON object with these fields:
    {{
        "ai_email_intent": "trade_instruction" or "not_trade_instruction",
        "ai_confidence_score": 0-100,
        "ai_reasoning": "brief explanation",
        "ai_order_details": {{
            "client_code": "extracted client code or null",
            "symbol": "extracted symbol or null",
            "quantity": numeric_value_or_null,
            "price": numeric_value_or_null,
            "buy_sell": "BUY" or "SELL" or null,
            "order_time": "time if mentioned or null",
            "trade_date": null,
            "isin": null,
            "expiry": null,
            "strike_price": null,
            "option_type": null,
            "order_type": null
        }},
        "ai_instruction_type": "rm_forwarded" or "client_direct" or "unknown"
    }}
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": "You are a trade surveillance analyst. Extract trade instruction details accurately from emails."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=1000
        )
        
        ai_response = response.choices[0].message.content.strip()
        
        # Try to parse JSON response
        try:
            # Remove markdown code blocks if present
            if ai_response.startswith('```json'):
                ai_response = ai_response[7:]
            if ai_response.endswith('```'):
                ai_response = ai_response[:-3]
            
            ai_analysis = json.loads(ai_response.strip())
            return ai_analysis
        except json.JSONDecodeError as e:
            print(f"❌ JSON parse error: {e}")
            print(f"Raw response: {ai_response}")
            return None
            
    except Exception as e:
        print(f"❌ AI analysis error: {e}")
        return None

def process_august1_emails_only():
    """Process only August 1st emails with GPT-4.1-mini."""
    
    # Load comprehensive emails
    email_file = "email_processing/august_dealing_emails_comprehensive.json"
    print(f"📧 Loading comprehensive emails from: {email_file}")
    
    with open(email_file, 'r', encoding='utf-8') as f:
        all_emails = json.load(f)
    
    print(f"📧 Loaded {len(all_emails)} emails from comprehensive file")
    
    # Filter for August 1st emails only
    august_1_emails = []
    for email in all_emails:
        subject = email.get('subject', '').lower()
        if any(pattern in subject for pattern in ['010825', '01 aug 25', '01/08/25', '01-08-25']):
            august_1_emails.append(email)
    
    print(f"🔍 Found {len(august_1_emails)} emails for August 1st")
    print("🤖 Starting AI analysis with GPT-4.1-mini...")
    
    trade_instructions = []
    trade_confirmations = []
    other_emails = []
    
    for i, email in enumerate(august_1_emails):
        print(f"📧 Processing email {i+1}/{len(august_1_emails)}: {email.get('subject', '')[:50]}...")
        
        subject = email.get('subject', '')
        sender = email.get('from', {}).get('emailAddress', {}).get('address', '')
        email_body = email.get('body', {}).get('content', '')
        
        # Analyze with GPT-4.1-mini
        ai_analysis = analyze_email_with_ai_gpt41(email_body, subject, sender)
        
        if ai_analysis:
            email_result = {
                'subject': subject,
                'sender': sender,
                'ai_analysis': ai_analysis
            }
            
            # Categorize based on AI intent
            intent = ai_analysis.get('ai_email_intent', '')
            if intent == 'trade_instruction':
                trade_instructions.append(email_result)
                print(f"  ✅ Trade Instruction: {ai_analysis.get('ai_order_details', {}).get('client_code', 'Unknown')}")
            elif intent == 'trade_confirmation':
                trade_confirmations.append(email_result)
                print(f"  📋 Trade Confirmation: {ai_analysis.get('ai_order_details', {}).get('client_code', 'Unknown')}")
            else:
                other_emails.append(email_result)
                print(f"  📧 Other: {intent}")
        else:
            # If AI analysis fails, categorize as other
            other_emails.append({
                'subject': subject,
                'sender': sender,
                'ai_analysis': None
            })
            print(f"  ❌ Analysis failed")
    
    # Create results structure (compatible with existing format)
    results = {
        'timestamp': datetime.now().strftime('%Y%m%d_%H%M%S'),
        'total_emails_analyzed': len(august_1_emails),
        'trade_instructions': {
            'count': len(trade_instructions),
            'emails': trade_instructions
        },
        'trade_confirmations': {
            'count': len(trade_confirmations),
            'emails': trade_confirmations
        },
        'other_emails': {
            'count': len(other_emails),
            'emails': other_emails
        },
        'all_results': {
            'emails': august_1_emails
        }
    }
    
    # Save results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f"complete_surveillance_results_gpt41_{timestamp}.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Analysis complete!")
    print(f"📊 Results:")
    print(f"   - Trade Instructions: {len(trade_instructions)}")
    print(f"   - Trade Confirmations: {len(trade_confirmations)}")
    print(f"   - Other Emails: {len(other_emails)}")
    print(f"💾 Results saved to: {output_file}")
    
    return output_file

if __name__ == "__main__":
    process_august1_emails_only() 