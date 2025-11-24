# FINAL EMAIL SURVEILLANCE PROCESS - PRODUCTION READY

**Date:** October 6, 2025  
**Status:** PRODUCTION READY - DO NOT CHANGE  
**Version:** 1.0 Final

## Overview

This document describes the **FINAL** email surveillance process that has been tested, validated, and is ready for production use. This process should **NOT** be modified without explicit approval.

## Process Flow

### 1. Email Fetching and Processing
- **Script:** `email_processing/process_emails_by_date.py`
- **Input:** Date (format: YYYYMMDD)
- **Output:** `email_surveillance_YYYYMMDD.json`

### 2. Email Analysis (AI-Powered)
- **Script:** `email_processing/complete_email_surveillance_system.py`
- **AI Models Used:**
  - **Primary:** `gpt-4.1` (legacy system with improved prompts)
  - **Fallback:** None (single model approach for stability)

### 3. Email-Order Matching
- **Script:** `email_order_validation_august_daily.py`
- **AI Model:** `gpt-4.1`
- **Features:**
  - Client code normalization (WM00542 → NEOWM00542)
  - Split execution detection
  - Intelligent symbol matching
  - Value-based quantity matching

### 4. Final Report Generation
- **Output:** `Final_Trade_Surveillance_Report_YYYYMMDD_with_Email_and_Trade_Analysis.xlsx`

## Key Features

### Email Classification Rules
1. **Trade Confirmation Rule:** Only classify as "trade_confirmation" if Subject contains "Trade Confirmation"
2. **Trade Instruction Detection:** Look for keywords like "execution", "execute", "buy", "sell", "place order"
3. **Instruction Precedence:** If ANY part contains NEW instructions, classify as "trade_instruction"

### Client Code Normalization
- `WM00542` → `NEOWM00542`
- `05523` → `NEO05523`
- Handles partial client codes in emails

### Split Execution Detection
- Detects when single email instruction is executed as multiple orders
- Calculates total quantity and average price
- Matches within acceptable tolerance (₹1-2 price difference)

### Symbol Matching Intelligence
- "blue jet healthcare" = "BLUEJET"
- "Energy Infrastructure Trust" = "ENERGYINF"
- "Manappuram Finance Limited" = "MANAPPURAM"

## File Structure

```
email_processing/
├── complete_email_surveillance_system.py    # Main email analysis
├── process_emails_by_date.py               # Email fetching
└── two_stage_email_analysis.py             # Backup (not used)

email_order_validation_august_daily.py      # Email-order matching
```

## Usage

### Run Complete Process for a Date
```bash
# Step 1: Fetch and analyze emails
python email_processing/process_emails_by_date.py 22092025

# Step 2: Match emails to orders
python email_order_validation_august_daily.py 22092025
```

### Expected Outputs
- `email_surveillance_YYYYMMDD.json` - Email analysis results
- `email_order_mapping_YYYYMMDD.json` - Matching results
- `Final_Trade_Surveillance_Report_YYYYMMDD_with_Email_and_Trade_Analysis.xlsx` - Final report

## Performance Metrics

### September 22, 2025 Results
- **Total Email Groups:** 7
- **Matched Instructions:** 5 (71.4%)
- **Unmatched Instructions:** 2 (legitimate - no corresponding orders)
- **Split Executions Detected:** 1 (WM00542 DIVISLAB case)

### Match Types
- **EXACT_MATCH:** Direct 1:1 email to order matching
- **SPLIT_EXECUTION:** Single email instruction executed as multiple orders
- **PARTIAL_MATCH:** Some fields match, flagged for review
- **NO_MATCH:** No corresponding orders found

## Error Handling

### Client Code Issues
- Automatic normalization for common patterns
- Fallback to exact match if normalization fails

### AI Model Issues
- Single model approach (gpt-4.1) for stability
- Retry logic with exponential backoff
- Graceful degradation on API failures

### Data Quality Issues
- Handles missing quantity/price in emails
- Validates order status (Complete/Rejected/Cancelled)
- Flags discrepancies for manual review

## Configuration

### Environment Variables Required
- `OPENAI_API_KEY` - OpenAI API key
- `GRAPH_API_CLIENT_ID` - Microsoft Graph API client ID
- `GRAPH_API_CLIENT_SECRET` - Microsoft Graph API client secret
- `GRAPH_API_TENANT_ID` - Microsoft Graph API tenant ID

### File Paths
- Order files: `September/Order Files/OrderBook-Closed-YYYYMMDD.csv`
- Output directory: `September/Daily_Reports/YYYYMMDD/`

## Validation

### Tested Scenarios
1. ✅ Single instruction emails
2. ✅ Multiple instruction emails
3. ✅ Split execution detection
4. ✅ Client code normalization
5. ✅ Symbol alias matching
6. ✅ Price range matching
7. ✅ Order status validation

### Known Limitations
1. Incomplete email extractions (missing quantity/price) cannot be matched
2. Orders on different dates than email date will not match
3. Rejected/Cancelled orders are flagged but not excluded from matching

## Maintenance

### Regular Checks
- Monitor match rates (should be >60%)
- Review unmatched instructions for data quality issues
- Validate split execution detection accuracy

### Updates
- **DO NOT** modify core logic without approval
- **DO NOT** change AI models without testing
- **DO NOT** modify client code normalization rules
- Only configuration changes (paths, API keys) are allowed

## Support

For issues or questions:
1. Check logs in terminal output
2. Verify input file formats
3. Confirm API credentials
4. Review unmatched cases for data quality

---

**This process is PRODUCTION READY and should NOT be modified without explicit approval.**
