# Trade Surveillance Process Documentation

## Overview
This document outlines the complete process for trade surveillance analysis, from raw audio files and order data to the final comprehensive Excel file with all required columns.

## Process Flow

### 1. Audio File Processing
**Script:** `extract_call_info.py`
**Input:** Raw audio files in `June/Call Records/`
**Output:** `June/call_info_output.xlsx`

**What it does:**
- Extracts mobile numbers from audio file names using regex
- Determines call start/end times and duration
- Maps mobile numbers to client IDs using UCC database
- Creates comprehensive call information file

**Columns generated:**
- filename (audio file name)
- mobile_number (extracted from filename)
- present_in_ucc (Y/N based on UCC database)
- call_start, call_end, duration_seconds
- client_id (mapped from UCC database)

### 2. Audio-Order Validation & Mapping
**Script:** `comprehensive_audio_trading_validation.py`
**Input:** 
- `June/call_info_output.xlsx`
- Order files in `June/Order Files/`
- `June/UCC database.xlsx`
**Output:** `June/audio_order_kl_orgtimestamp_validation.xlsx`

**What it does:**
- Matches audio files with order data based on client ID and date
- Creates multiple sheets for different analysis perspectives
- Uses OrgTimeStamp for order timing
- Filters for KL users only

**Sheets generated:**
- Audio_To_Orders
- Orders_To_Audio  
- Order_Audio_Mapping
- All_Audio_Files
- All_KL_Orders

### 3. Audio Transcription
**Script:** `transcribe_calls.py`
**Input:** Audio files in `June/Call Records/`
**Output:** Transcript files in `June/transcripts/`

**What it does:**
- Transcribes all audio files using Google Vertex AI
- Saves transcripts as .txt files
- Maintains speaker identification (Client/Dealer)

### 4. AI Analysis of Orders with Audio
**Script:** `order_transcript_analysis.py`
**Input:**
- `June/audio_order_kl_orgtimestamp_validation.xlsx`
- Transcript files from `June/transcripts/`
**Output:** Multiple analysis files with timestamps

**What it does:**
- Groups orders by audio file
- Analyzes each order against its corresponding transcript
- Uses OpenAI models for compliance analysis
- Generates AI reasoning for each order

**Analysis includes:**
- order_discussed (Y/N)
- discrepancy (Y/N with explanation)
- complaint (Y/N with explanation)
- action (none/review/investigate/reverse)
- ai_reasoning (detailed analysis)

### 5. Final Required Columns Mapping
**Script:** `add_required_columns_to_excel.py`
**Input:**
- AI analysis file (e.g., `order_transcript_analysis_mapping_all_dates_20250715_095106.xlsx`)
- Order files in `June/Order Files/`
- `June/call_info_output.xlsx`
- Transcript files in `June/transcripts/`
**Output:** `June/order_transcript_analysis_mapping_all_dates_20250715_095106_with_required_columns.xlsx`

**What it does:**
- Adds all required columns to the final analysis file
- Maps data from multiple sources using appropriate keys
- Ensures no missing data where available

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

## Key Features

### Mobile Number Mapping Logic
- **Before:** Mapped by client_id (caused missing mobile numbers)
- **After:** Mapped by audio filename (resolves all missing cases)
- **Condition:** Only maps when audio file exists

### Dealer ID Mapping
- Uses `User` column from order files
- Matches on `ExchOrderID`
- Handles multiple order file formats (xlsx/csv)

### Transcript Mapping
- Reads transcript files from `June/transcripts/`
- Uses audio filename to locate correct transcript
- Handles missing transcript files gracefully

## File Structure

```
trade_surveillance/
├── June/
│   ├── Call Records/           # Raw audio files
│   ├── Order Files/           # Order data files
│   ├── Trade Files/           # Trade execution data
│   ├── transcripts/           # Generated transcripts
│   ├── call_info_output.xlsx  # Step 1 output
│   ├── audio_order_kl_orgtimestamp_validation.xlsx  # Step 2 output
│   ├── UCC database.xlsx      # Client-mobile mapping
│   └── order_transcript_analysis_mapping_all_dates_20250715_095106_with_required_columns.xlsx  # Final output
├── extract_call_info.py       # Step 1 script
├── comprehensive_audio_trading_validation.py  # Step 2 script
├── transcribe_calls.py        # Step 3 script
├── order_transcript_analysis.py  # Step 4 script
└── add_required_columns_to_excel.py  # Step 5 script
```

## Final Output

The final Excel file contains:
- All original analysis columns
- All required columns properly mapped
- No missing mobile numbers for orders with audio
- Complete dealer ID mapping from order files
- Full transcript extracts for orders with audio
- AI analysis observations for compliance review

## Quality Checks

- **Mobile Number Mapping:** 0 rows with audio but missing mobile number
- **Dealer ID Mapping:** Filled from User column in order files
- **Transcript Mapping:** Available for all orders with audio files
- **Data Integrity:** All required columns present and properly mapped

## Usage

1. Run scripts in sequence (1-5)
2. Check final output file for complete analysis
3. Use for compliance review and audit purposes
4. All data sources properly integrated and mapped 