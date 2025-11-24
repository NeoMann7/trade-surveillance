# Trade Surveillance Process Documentation

## Overview
This document outlines the complete process for trade surveillance analysis, from raw audio files and order data to the final comprehensive Excel file with all required columns, including email surveillance integration.

## Process Flow

### 1. Audio File Processing
**Script:** `extract_call_info_august_daily.py`
**Input:** Raw audio files in `August/Call Records/Call_YYYYMMDD/`
**Output:** `August/Daily_Reports/YYYYMMDD/call_info_output_YYYYMMDD.xlsx`

**What it does:**
- Extracts mobile numbers from audio file names using regex
- Determines call start/end times and duration
- Maps mobile numbers to client IDs using UCC database
- Creates comprehensive call information file
- **NEW:** Prioritizes date suffix extraction (e.g., `20250818072409`) for accurate timestamp parsing

**Columns generated:**
- filename (audio file name)
- mobile_number (extracted from filename)
- present_in_ucc (Y/N based on UCC database)
- call_start, call_end, duration_seconds
- client_id (mapped from UCC database)

### 2. Audio-Order Validation & Mapping
**Script:** `comprehensive_audio_trading_validation_august_daily.py`
**Input:** 
- `August/Daily_Reports/YYYYMMDD/call_info_output_YYYYMMDD.xlsx`
- Order files in `August/Order Files/`
- `August/UCC database.xlsx`
**Output:** `August/Daily_Reports/YYYYMMDD/audio_order_kl_orgtimestamp_validation_YYYYMMDD.xlsx`

**What it does:**
- Matches audio files with order data based on client ID and date
- Creates multiple sheets for different analysis perspectives
- Uses OrgTimeStamp for order timing
- Filters for KL users only
- **NEW:** Implements intelligent fallback matching logic

**NEW Audio-Order Matching Logic:**
1. **Primary Match:** Try to match orders within ±5 minutes of call start/end times
2. **Fallback Match:** If no ±5 minute match, match with ANY call from that client for the entire day
3. **Result:** Dramatically improved match rates (from 1.5% to 46.8% coverage)

**Match Status Types:**
- `matched_in_time_range`: Orders matched within ±5 minutes
- `matched_daily_fallback`: Orders matched using daily fallback logic
- `no_audio_matched`: Orders with no audio source

**Sheets generated:**
- Audio_To_Orders
- Orders_To_Audio  
- Order_Audio_Mapping
- All_Audio_Files
- All_KL_Orders

### 3. Audio Transcription
**Script:** `transcribe_calls_august_daily.py`
**Input:** Audio files in `August/Call Records/Call_YYYYMMDD/`
**Output:** Transcript files in `August/Daily_Reports/YYYYMMDD/transcripts_YYYYMMDD/`

**What it does:**
- Transcribes all audio files using Google Vertex AI (Gemini-2.5-flash)
- Saves transcripts as .txt files
- Maintains speaker identification (Client/Dealer)

### 4. AI Analysis of Orders with Audio
**Script:** `order_transcript_analysis_august_daily.py`
**Input:**
- `August/Daily_Reports/YYYYMMDD/audio_order_kl_orgtimestamp_validation_YYYYMMDD.xlsx`
- Transcript files from `August/Daily_Reports/YYYYMMDD/transcripts_YYYYMMDD/`
**Output:** `August/Daily_Reports/YYYYMMDD/order_transcript_analysis_YYYYMMDD.xlsx`

**What it does:**
- Groups orders by audio file
- Analyzes each order against its corresponding transcript
- Uses OpenAI models (o3, gpt-4) for compliance analysis
- Generates AI reasoning for each order

**Analysis includes:**
- order_discussed (Y/N)
- discrepancy (Y/N with explanation)
- complaint (Y/N with explanation)
- action (none/review/investigate/reverse)
- ai_reasoning (detailed analysis)

### 5. Email Surveillance & Order Mapping
**Script:** `email_order_validation_august_daily.py`
**Input:**
- Email surveillance results from `email_surveillance_YYYYMMDD.json`
- Order files in `August/Order Files/`
**Output:** 
- `August/Daily_Reports/YYYYMMDD/email_order_mapping_YYYYMMDD.xlsx`
- `August/Daily_Reports/YYYYMMDD/email_order_mapping_YYYYMMDD.json`

**What it does:**
- Matches email trade instructions to actual orders using AI
- Groups related emails into instruction threads
- Uses intelligent symbol matching for variations
- Handles CMP (Current Market Price) instructions
- **NEW:** Implements order ID normalization for scientific notation handling

**Email Matching Features:**
- **AI-Powered Matching:** Uses GPT models for intelligent symbol matching
- **Thread Analysis:** Analyzes entire email chains as single instructions
- **CMP Handling:** Matches "CMP" prices with any actual price, flags as discrepancy
- **Fallback Logic:** Matches by client code, symbol, and quantity if order ID fails

### 6. Final Required Columns Mapping
**Script:** `add_required_columns_to_excel_august_daily.py`
**Input:**
- AI analysis file from Step 4
- Order files in `August/Order Files/`
- Call info from Step 1
- Email mapping data from Step 5
**Output:** `August/Daily_Reports/YYYYMMDD/Final_Trade_Surveillance_Report_YYYYMMDD_with_Email_and_Trade_Analysis.xlsx`

**What it does:**
- Adds all required columns to the final analysis file
- Maps data from multiple sources using appropriate keys
- **NEW:** Integrates email surveillance results
- **NEW:** Implements highlighting for orders with no audit source
- **NEW:** Adds comprehensive email content column

## Required Columns Mapping

| Required Column | Source | Mapping Logic |
|----------------|--------|---------------|
| Order Date | order_date | Direct from main file |
| Order ID | order_id | Direct from main file |
| Client Code | client_id | Direct from main file |
| Dealer ID | Order Files | Match by ExchOrderID → User column |
| Mobile No. | call_info_output.xlsx | Match by audio filename → mobile_number |
| Call received from Registered Number (Y/N) | call_info_output.xlsx | Match by audio filename → present_in_ucc |
| Call Records matched with Order File (Y/N) | order_discussed | Direct from main file |
| Order Executed (Y/N) | Order Files | Match by ExchOrderID → Status column |
| Call Extract | transcripts/ | Read transcript file using audio filename |
| Call File Name | audio_file | Direct from main file |
| Observation | ai_reasoning | Direct from main file |
| **Email-Order Match Status** | **Email mapping** | **Match by client_code → match status** |
| **Email Confidence Score** | **Email mapping** | **Match by client_code → confidence score** |
| **Email Discrepancy Details** | **Email mapping** | **Match by client_code → discrepancy details** |
| **Email_Content** | **Email mapping** | **Match by client_code → full email content** |

## NEW Features

### Audio-Order Matching Improvements
- **Fallback Logic:** Daily client-based matching when ±5 minute window fails
- **Realistic Timing:** Accounts for real-world trading delays
- **Better Coverage:** 28x improvement in audio mapping coverage

### Email Surveillance Integration
- **Thread-Based Analysis:** Groups related emails for comprehensive analysis
- **AI-Powered Matching:** Intelligent symbol and instruction matching
- **CMP Handling:** Proper handling of Current Market Price instructions
- **Order ID Normalization:** Handles scientific notation in order IDs

### Highlighting System
- **No Source Highlighting:** Orders with no audio AND no email are highlighted in red
- **Completed Orders Focus:** Only highlights completed orders (not cancelled/rejected)
- **Visual Compliance:** Easy identification of orders requiring audit review

### Email Content Column
- **Comprehensive Details:** Subject, sender, client, symbol, quantity, price, action
- **Full Audit Trail:** Complete email instruction details for matched orders
- **Structured Format:** Consistent formatting for easy review

## File Structure

```
trade_surveillance/
├── August/
│   ├── Call Records/Call_YYYYMMDD/     # Raw audio files
│   ├── Order Files/                    # Order data files
│   ├── Trade Files/                    # Trade execution data
│   ├── Daily_Reports/YYYYMMDD/
│   │   ├── transcripts_YYYYMMDD/       # Generated transcripts
│   │   ├── call_info_output_YYYYMMDD.xlsx
│   │   ├── audio_order_kl_orgtimestamp_validation_YYYYMMDD.xlsx
│   │   ├── order_transcript_analysis_YYYYMMDD.xlsx
│   │   ├── email_order_mapping_YYYYMMDD.xlsx
│   │   └── Final_Trade_Surveillance_Report_YYYYMMDD_with_Email_and_Trade_Analysis.xlsx
│   └── UCC database.xlsx               # Client-mobile mapping
├── email_processing/                   # Email surveillance scripts
├── extract_call_info_august_daily.py   # Step 1 script
├── comprehensive_audio_trading_validation_august_daily.py  # Step 2 script
├── transcribe_calls_august_daily.py    # Step 3 script
├── order_transcript_analysis_august_daily.py  # Step 4 script
├── email_order_validation_august_daily.py  # Step 5 script
└── add_required_columns_to_excel_august_daily.py  # Step 6 script
```

## Final Output

The final Excel file contains:
- All original analysis columns
- All required columns properly mapped
- **Email surveillance results** with confidence scores
- **Email content** for all matched orders
- **Highlighting** for orders with no audit source
- Complete audit trail for compliance review

## Quality Metrics

### Coverage Statistics
- **Audio Coverage:** 46.8% (29/62 orders)
- **Email Coverage:** 19.4% (12/62 orders)
- **Combined Coverage:** 66.1% (41/62 orders)
- **Orders Highlighted:** 30.6% (19/62 orders)

### Match Quality
- **Audio Matches:** 7 within ±5 min, 22 with daily fallback
- **Email Matches:** 3 exact matches, 2 partial matches
- **AI Confidence:** 70-100% confidence scores for email matches

## Usage

1. Run `run_daily_trade_surveillance.py YYYYMMDD` for complete automation
2. Check final output file for complete analysis
3. Review highlighted orders (red) for compliance gaps
4. Use email content for detailed audit trail
5. All data sources properly integrated and mapped

## Troubleshooting

### Common Issues
- **Low Audio Coverage:** Check if fallback logic is working
- **Email Not Matching:** Verify JSON structure in email mapping
- **Missing Highlighting:** Ensure openpyxl is installed
- **Order ID Issues:** Check for scientific notation normalization 