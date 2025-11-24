# Email Daily Process Documentation

## **Overview**
This document outlines the complete daily email surveillance process that integrates with the trade surveillance system, including AI-powered matching and comprehensive audit trail generation.

## **Process Flow**

### **Step 1: Email Access and Processing**
**Purpose**: Access emails through Graph API, filter by dealing desk email ID, and run order classification/extraction

**Process**:
1. **Access emails** through Microsoft Graph API
2. **Filter emails** by dealing desk email ID for the specific date provided
3. **Run order classification and extraction** using AI analysis

**Command**:
```bash
python email_processing/process_emails_by_date.py 2025-08-XX
```

**Input**: Direct API access to emails (no input file)
**Output**: `email_surveillance_XX082025.json`

**What it does**:
- Connects to email API and accesses emails directly
- Filters emails by dealing desk email ID and date
- Groups related emails into threads based on subject patterns
- Passes email body content to AI for analysis
- Uses AI to classify each email and extract trade details
- Groups related emails into instruction groups
- Saves results in fixed naming format

**Note**: The AI handles all content extraction (symbols, quantities, prices, etc.) directly from the email body content.

### **Step 2: Email-Order Validation with AI-Powered Matching**
**Purpose**: Match email trade instructions to executed orders using intelligent AI matching

**Process**:
1. **Load email surveillance results** from Step 1
2. **Load KL order book** for the specific date
3. **Group emails by instruction** (same client + symbol + date)
4. **Extract final instructions** from each group
5. **Use AI-powered matching** to match instructions to orders with intelligent symbol matching
6. **Generate comprehensive reports** with match details and discrepancies

**Command**:
```bash
python email_order_validation_august_daily.py XX082025
```

**Input**: 
- `email_surveillance_XX082025.json` (from Step 1)
- `August/Order Files/OrderBook-Closed-XX082025.csv`

**Output**: 
- `August/Daily_Reports/XX082025/email_order_mapping_XX082025.xlsx`
- `August/Daily_Reports/XX082025/email_order_mapping_XX082025.json`

**AI-Powered Matching Features**:
- **Intelligent Symbol Matching**: AI understands symbol variations (e.g., "Manappuram Finance Limited" = "MANAPPURAM")
- **Quantity Matching**: Handles exact matches and split executions
- **Price Matching**: Allows for small variations and market price changes
- **CMP Handling**: Properly matches "CMP" or "Current Market Price" with any actual price, flags as discrepancy
- **Confidence Scoring**: Provides 0-100% confidence scores for each match
- **Discrepancy Detection**: Identifies and flags any differences between email instructions and executed orders
- **Order ID Normalization**: Handles scientific notation in order IDs for robust matching

### **Step 3: Final Report Integration**
**Purpose**: Integrate email surveillance results into the final comprehensive trade surveillance report

**Process**:
1. **Load audio surveillance Excel** file for the date
2. **Apply email-order mapping** results from Step 2
3. **Add new columns**:
   - `Email-Order Match Status`: 'Matched' for matched orders, 'No Email Match' for unmatched
   - `Email Confidence Score`: AI confidence score (0-100%)
   - `Email Discrepancy Details`: Any differences found between email and orders
   - `Email_Content`: Complete email instruction details (subject, sender, client, symbol, qty, price, action)
4. **Implement highlighting** for orders with no audit source
5. **Save final comprehensive report**

**Input**: 
- Audio surveillance Excel file: `August/Daily_Reports/XX082025/order_transcript_analysis_XX082025.xlsx`
- Email mapping data from Step 2

**Output**: `August/Daily_Reports/XX082025/Final_Trade_Surveillance_Report_XX082025_with_Email_and_Trade_Analysis.xlsx`

## **File Naming Convention**

### **Email Surveillance Results**
- **Format**: `email_surveillance_XX082025.json`
- **Example**: `email_surveillance_01082025.json`

### **Email-Order Mapping Reports**
- **Excel**: `August/Daily_Reports/XX082025/email_order_mapping_XX082025.xlsx`
- **JSON**: `August/Daily_Reports/XX082025/email_order_mapping_XX082025.json`

### **Final Comprehensive Report**
- **Format**: `August/Daily_Reports/XX082025/Final_Trade_Surveillance_Report_XX082025_with_Email_and_Trade_Analysis.xlsx`

## **JSON Structure**

### **Email Mapping JSON Structure**
```json
{
  "timestamp": "20250818_143022",
  "total_instructions": 8,
  "matched_instructions": 5,
  "unmatched_instructions": 3,
  "matches": [
    {
      "email_instruction": {
        "client_code": "NEOWM00629",
        "symbol": "KRT",
        "quantity": 1000000,
        "price": "CMP",
        "buy_sell": "SELL",
        "source_email": {
          "subject": "Approval - SELL Trade - KRT",
          "sender": "Isani.majumdar@neo-group.in"
        }
      },
      "matched_orders": [...],
      "match_type": "PARTIAL_MATCH",
      "confidence_score": 85,
      "discrepancies": [...],
      "review_flags": [...]
    }
  ]
}
```

### **Key Structure Changes**
- **Fixed JSON Structure**: Uses `email_instruction.client_code` instead of nested structure
- **Proper Field Mapping**: Ensures client codes are correctly extracted for final report integration
- **Complete Email Details**: Includes full email metadata for audit trail

## **AI Capabilities**

### **Email Analysis (Step 1)**
- **Content Extraction**: Extracts symbols, quantities, prices, client codes from email bodies
- **Thread Analysis**: Groups related emails and identifies final instructions
- **Classification**: Distinguishes between trade instructions, confirmations, and other emails

### **Order Matching (Step 2)**
- **Symbol Intelligence**: Matches "Manappuram Finance Limited" to "MANAPPURAM"
- **Split Execution Detection**: Identifies when single email instruction results in multiple orders
- **Price Variation Handling**: Accounts for market price changes and small variations
- **CMP Handling**: Properly handles "Current Market Price" instructions
- **Confidence Assessment**: Provides detailed reasoning and confidence scores

## **Final Report Integration**

### **Email Columns Added**
| Column | Description | Source |
|--------|-------------|--------|
| Email-Order Match Status | 'Matched' or 'No Email Match' | email_instruction.client_code mapping |
| Email Confidence Score | AI confidence (0-100%) | match.confidence_score |
| Email Discrepancy Details | Discrepancy descriptions | match.discrepancies |
| Email_Content | Complete email details | email_instruction + source_email |

### **Email Content Format**
```
Subject: Approval - SELL Trade - KRT
Sender: Isani.majumdar@neo-group.in
Date: 2025-08-18T10:30:00Z
Client: NEOWM00629
Symbol: KRT
Qty: 1000000
Price: CMP
Action: SELL

--- EMAIL BODY ---
[Complete email body content including HTML and text]

--- PDF ATTACHMENTS ---
PDF: trade_instructions.pdf
[Complete PDF attachment content extracted as text]
```

### **Highlighting System**
- **No Source Highlighting**: Orders with no audio AND no email are highlighted in red
- **Completed Orders Focus**: Only highlights completed orders (not cancelled/rejected)
- **Visual Compliance**: Easy identification of orders requiring audit review

## **Quality Metrics**

### **Coverage Targets**
- **Email Analysis**: Target 90%+ coverage for trade instruction identification
- **Order Matching**: Target 80%+ match rate for valid trade instructions
- **Final Integration**: 100% of email matches properly integrated into final report

### **Review Flags**
- **Quantity Mismatches**: When email quantity ≠ order quantity
- **Price Discrepancies**: When email price ≠ order price (including CMP handling)
- **Split Executions**: When single email results in multiple orders
- **AI Review Required**: When AI confidence is low or discrepancies detected

## **Error Handling**

### **Fallback Mechanisms**
- **AI Matching Failure**: Falls back to exact matching if AI fails
- **Missing Data**: Gracefully handles missing email or order data
- **API Failures**: Retries and provides clear error messages
- **JSON Structure Issues**: Fixed structure mapping for reliable integration

### **Data Validation**
- **Order ID Normalization**: Converts scientific notation to full order IDs
- **Type Conversion**: Handles string/numeric conversions safely
- **Missing Values**: Provides defaults for missing fields
- **Client Code Mapping**: Ensures proper case-sensitive matching

## **Complete Daily Workflow**

### **For a Single Date (e.g., August 18th):**
```bash
# Step 1: Email Surveillance
python email_processing/process_emails_by_date.py 2025-08-18

# Step 2: Email-Order Validation with AI
python email_order_validation_august_daily.py 18082025

# Step 3: Final Report Integration (automatic in Step 2)
# Final report: Final_Trade_Surveillance_Report_18082025_with_Email_and_Trade_Analysis.xlsx
```

### **Expected Results:**
- **Email Analysis**: Trade instructions identified with 90%+ coverage
- **Order Matching**: 80%+ match rate using AI-powered intelligent matching
- **Final Integration**: All matched orders properly integrated with email content
- **Highlighting**: Orders with no audit source clearly highlighted
- **Complete Audit Trail**: Full email details available for compliance review

## **Troubleshooting**

### **Common Issues**
1. **Low Match Rate**: Check if AI matching is enabled and working
2. **Missing Emails**: Verify Graph API access and dealing desk email filtering
3. **Email Not Showing in Final Report**: Verify JSON structure uses `email_instruction.client_code`
4. **Missing Email Content**: Check if Email_Content column is properly mapped
5. **Highlighting Not Working**: Ensure openpyxl is installed for Excel formatting

### **Debugging Commands**
```bash
# Check email surveillance results
python -c "import json; data=json.load(open('email_surveillance_XX082025.json')); print(f'Total emails: {len(data[\"email_analyses\"])}')"

# Check order matching results
python -c "import json; data=json.load(open('August/Daily_Reports/XX082025/email_order_mapping_XX082025.json')); print(f'Match rate: {data[\"matched_instructions\"]}/{data[\"total_instructions\"]}')"

# Check final report integration
python -c "import pandas as pd; df=pd.read_excel('August/Daily_Reports/XX082025/Final_Trade_Surveillance_Report_XX082025_with_Email_and_Trade_Analysis.xlsx'); print(f'Matched orders: {(df[\"Email-Order Match Status\"] == \"Matched\").sum()}')"

# Check email content
python -c "import pandas as pd; df=pd.read_excel('August/Daily_Reports/XX082025/Final_Trade_Surveillance_Report_XX082025_with_Email_and_Trade_Analysis.xlsx'); matched=df[df['Email-Order Match Status'] == 'Matched']; print(f'Orders with email content: {len(matched[matched[\"Email_Content\"] != \"\"])}')"
```

### **Recent Fixes Applied**
1. **JSON Structure Fix**: Updated to use `email_instruction.client_code` for proper mapping
2. **Email Content Column**: Added comprehensive email content to final report
3. **Highlighting Implementation**: Added visual highlighting for orders with no audit source
4. **Order ID Normalization**: Fixed scientific notation handling for robust matching
5. **CMP Handling**: Improved handling of "Current Market Price" instructions 