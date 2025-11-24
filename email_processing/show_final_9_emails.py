#!/usr/bin/env python3
"""
Show Final 9 Emails Without Order Details
Display the actual emails that still need manual review
"""

import json

def main():
    """Show the final 9 emails without order details"""
    
    print("=== FINAL 9 EMAILS WITHOUT ORDER DETAILS ===")
    
    # Load the original trade instructions
    with open('trade_instructions_20250822_171054.json', 'r') as f:
        data = json.load(f)
    
    instructions = data['trade_instructions']
    original_without_details = [e for e in instructions if not e.get('ai_order_details')]
    
    print(f"Original emails without order details: {len(original_without_details)}")
    
    # Load our solved results
    with open('solved_remaining_emails_20250824_211601.json', 'r') as f:
        solved_data = json.load(f)
    
    solved_results = solved_data['results']
    solved_without_details = [r for r in solved_results if not r['has_order_details']]
    
    print(f"Emails still without order details after our solutions: {len(solved_without_details)}")
    
    # Create a mapping of subjects to their solved status
    solved_subjects = {r['subject']: r['has_order_details'] for r in solved_results}
    
    # Show the final 9 emails that still don't have order details
    print(f"\n=== THE ACTUAL 9 EMAILS WITHOUT ORDER DETAILS ===")
    
    final_without_details = []
    
    for email in original_without_details:
        subject = email.get('subject', '')
        if subject in solved_subjects:
            if not solved_subjects[subject]:
                final_without_details.append(email)
        else:
            # This email wasn't in our solved analysis, so it still doesn't have details
            final_without_details.append(email)
    
    print(f"Final count: {len(final_without_details)} emails without order details")
    print("\nThese emails still need manual review:")
    
    for i, email in enumerate(final_without_details, 1):
        subject = email.get('subject', 'No subject')
        print(f"{i}. {subject}")
        
        # Categorize the email
        if 'FW:' in subject:
            category = "Forwarded"
        elif 'RE:' in subject:
            category = "Reply"
        elif 'Cash Trade' in subject:
            category = "Cash Trade"
        else:
            category = "Other"
        
        print(f"   Category: {category}")
        print(f"   Issue: Needs manual investigation")
        print()

if __name__ == "__main__":
    main() 