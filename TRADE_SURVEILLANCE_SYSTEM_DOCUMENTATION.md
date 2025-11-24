# Trade Surveillance System - Complete Documentation

## 📋 Table of Contents
1. [System Overview](#system-overview)
2. [Architecture](#architecture)
3. [Complete Process Flow](#complete-process-flow)
4. [File Structure](#file-structure)
5. [Scripts and Functions](#scripts-and-functions)
6. [Data Flow](#data-flow)
7. [Usage Instructions](#usage-instructions)
8. [Configuration](#configuration)
9. [Output Files](#output-files)
10. [Troubleshooting](#troubleshooting)
11. [API Integration](#api-integration)

---

## 🎯 System Overview

The Trade Surveillance System is a comprehensive automated solution for monitoring and validating trading activities through both audio call recordings and email communications. The system ensures compliance by matching trade instructions from multiple sources to actual executed orders.

### Key Features:
- **Dual Source Validation**: Audio calls + Email instructions
- **AI-Powered Analysis**: Intelligent matching and discrepancy detection
- **Automated Processing**: Single command execution for complete surveillance
- **Compliance Highlighting**: Automatic flagging of orders without audit trails
- **Real-time Email Processing**: Microsoft Graph API integration
- **Comprehensive Reporting**: Excel-based final reports with visual indicators

---

## 🏗️ Architecture

### Core Components:
1. **Master Orchestrator**: `run_daily_trade_surveillance.py`
2. **Audio Processing Pipeline**: Call extraction, transcription, AI analysis
3. **Email Processing Pipeline**: Graph API integration, AI classification
4. **Order Validation Engine**: Multi-source matching with fallback logic
5. **Report Generator**: Comprehensive Excel output with highlighting

### Technology Stack:
- **Python 3.x**: Core processing language
- **OpenAI GPT Models**: AI analysis and matching
- **Google Vertex AI**: Audio transcription
- **Microsoft Graph API**: Email access
- **Pandas**: Data manipulation
- **OpenPyXL**: Excel report generation

---

## 🔄 Complete Process Flow

### Master Process (7 Steps):

```
┌─────────────────────────────────────────────────────────────┐
│                TRADE SURVEILLANCE PROCESS                   │
└─────────────────────────────────────────────────────────────┘

Step 0: Email Processing
├── Check if email_surveillance_YYYYMMDD.json exists
├── If missing: Access emails via Microsoft Graph API
├── Filter for dealing@neo-group.in emails on specified date
├── Group emails by subject into threads
├── AI classification (trade instruction, confirmation, other)
├── Extract order details from trade instructions
└── Save to email_surveillance_YYYYMMDD.json

Step 1: Audio File Processing
├── Scan August/Call Records/Call_YYYYMMDD/ for .wav files
├── Extract mobile numbers from filenames
├── Load UCC database (August/UCC Database.xlsx)
├── Check mobile number registration status
├── Map mobile numbers to client codes
├── Extract timestamps from filenames
└── Save to call_info_output_YYYYMMDD.xlsx

Step 2: Audio-Order Validation & Mapping
├── Load call info and order files
├── Filter for KL users only
├── Primary matching: ±5 minutes around call time
├── Fallback matching: Same client, entire day
├── Create mobile-to-client mapping
└── Save to audio_order_kl_orgtimestamp_validation_YYYYMMDD.xlsx

Step 3: Audio Transcription
├── Use Google Vertex AI (Gemini-2.5-flash)
├── Process all .wav files
├── Handle transcription errors gracefully
└── Save transcripts to transcripts_YYYYMMDD/ directory

Step 4: AI Analysis
├── Load order-audio mappings and transcripts
├── Use OpenAI models (o3, fallback to gpt-4)
├── Analyze each audio file with mapped orders
├── Determine if orders were discussed
├── Identify discrepancies, complaints, actions
└── Save to order_transcript_analysis_YYYYMMDD.xlsx

Step 5: Email-Order Validation & Mapping
├── Load email surveillance results
├── Group related emails into instruction threads
├── AI-powered symbol/quantity/price matching
├── Handle "CMP" (Current Market Price) instructions
├── Generate confidence scores and discrepancy flags
└── Save to email_order_mapping_YYYYMMDD.xlsx

Step 6: Final Required Columns Mapping
├── Combine all data sources
├── Add required compliance columns
├── Implement highlighting logic for orders without sources
├── Generate email content summaries
└── Save final comprehensive report
```

---

## 📁 File Structure

```
trade-surveillance/
├── run_daily_trade_surveillance.py          # Master orchestrator
├── extract_call_info_august_daily.py        # Step 1: Audio file processing
├── comprehensive_audio_trading_validation_august_daily.py  # Step 2: Audio-order mapping
├── transcribe_calls_august_daily.py         # Step 3: Audio transcription
├── order_transcript_analysis_august_daily.py # Step 4: AI analysis
├── email_order_validation_august_daily.py   # Step 5: Email-order mapping
├── add_required_columns_to_excel_august_daily.py  # Step 6: Final report
├── email_processing/
│   ├── process_emails_by_date.py            # Email processing function
│   ├── complete_email_surveillance_system.py # AI email analysis
│   └── EMAIL_DAILY_PROCESS.md               # Email process documentation
├── August/
│   ├── Call Records/
│   │   └── Call_YYYYMMDD/                   # Audio files by date
│   ├── Order Files/
│   │   └── OrderBook-Closed-YYYYMMDD.csv    # Order data by date
│   ├── Daily_Reports/
│   │   └── YYYYMMDD/                        # Daily output directory
│   │       ├── call_info_output_YYYYMMDD.xlsx
│   │       ├── audio_order_kl_orgtimestamp_validation_YYYYMMDD.xlsx
│   │       ├── transcripts_YYYYMMDD/
│   │       ├── order_transcript_analysis_YYYYMMDD.xlsx
│   │       ├── email_order_mapping_YYYYMMDD.xlsx
│   │       └── Final_Trade_Surveillance_Report_YYYYMMDD_with_Email_and_Trade_Analysis.xlsx
│   └── UCC Database.xlsx                    # Client-mobile mapping
└── .env                                     # Environment variables
```

---

## 🔧 Scripts and Functions

### 1. Master Orchestrator
**File**: `run_daily_trade_surveillance.py`

**Purpose**: Coordinates all 7 steps of the surveillance process

**Key Functions**:
- `run_email_processing_step()`: Handles email processing using existing function
- `run_step()`: Executes individual processing steps
- `validate_date_format()`: Validates DDMMYYYY format
- `check_data_exists()`: Verifies required input files exist

**Usage**:
```bash
python run_daily_trade_surveillance.py 25082025
```

### 2. Audio File Processing
**File**: `extract_call_info_august_daily.py`

**Purpose**: Extract metadata from audio filenames and validate against UCC database

**Key Functions**:
- `extract_mobile()`: Extract mobile numbers from filenames
- `extract_call_info_for_date()`: Main processing function

**Input**: Audio files in `August/Call Records/Call_YYYYMMDD/`
**Output**: `call_info_output_YYYYMMDD.xlsx`

### 3. Audio-Order Validation
**File**: `comprehensive_audio_trading_validation_august_daily.py`

**Purpose**: Match audio calls to actual orders with intelligent fallback logic

**Key Functions**:
- `create_mobile_to_client_mapping()`: Create UCC-based client mapping
- `validate_audio_trading_for_date()`: Main validation function

**Matching Logic**:
1. **Primary**: ±5 minutes around call time
2. **Fallback**: Same client, entire day

### 4. Audio Transcription
**File**: `transcribe_calls_august_daily.py`

**Purpose**: Convert audio files to text using Google Vertex AI

**Technology**: Google Vertex AI (Gemini-2.5-flash)
**Error Handling**: Continues processing if individual files fail

### 5. AI Analysis
**File**: `order_transcript_analysis_august_daily.py`

**Purpose**: Analyze transcripts to determine order discussion status

**AI Models**: OpenAI o3 (primary), gpt-4 (fallback)
**Analysis**: Order discussion, discrepancies, complaints, required actions

### 6. Email-Order Validation
**File**: `email_order_validation_august_daily.py`

**Purpose**: Match email trade instructions to orders using AI

**Key Functions**:
- `match_email_group_to_orders_with_ai()`: AI-powered matching
- `calculate_match_score()`: Scoring algorithm with CMP handling
- `normalize_order_id()`: Handle scientific notation in order IDs

### 7. Final Report Generation
**File**: `add_required_columns_to_excel_august_daily.py`

**Purpose**: Combine all data into comprehensive final report

**Key Features**:
- **Highlighting Logic**: Red highlighting for orders without sources
- **Email Content**: Summary of matched email instructions
- **Compliance Columns**: All required surveillance fields

### 8. Email Processing
**File**: `email_processing/process_emails_by_date.py`

**Purpose**: Access and analyze emails via Microsoft Graph API

**Key Functions**:
- `process_emails_for_date()`: Main email processing function
- Graph API integration for email access
- AI-powered email classification and extraction

---

## 📊 Data Flow

### Input Data Sources:
1. **Audio Files**: `.wav` files with embedded metadata
2. **Order Files**: CSV files with trade execution data
3. **UCC Database**: Excel file with client-mobile mappings
4. **Email Data**: Microsoft Graph API access

### Processing Pipeline:
```
Audio Files → Mobile Extraction → UCC Validation → Order Matching → Transcription → AI Analysis
     ↓
Email Data → Thread Grouping → AI Classification → Order Matching → Discrepancy Detection
     ↓
Combined Analysis → Final Report → Compliance Highlighting
```

### Output Data:
1. **Intermediate Files**: Step-specific Excel/JSON outputs
2. **Final Report**: Comprehensive Excel with all surveillance data
3. **Highlighted Orders**: Visual indicators for compliance review

---

## 🚀 Usage Instructions

### Prerequisites:
1. **Python Environment**: Python 3.x with required packages
2. **API Keys**: OpenAI, Google Vertex AI, Microsoft Graph
3. **Data Files**: Audio files, order files, UCC database
4. **Environment Setup**: `.env` file with API credentials

### Single Command Execution:
```bash
# Complete surveillance for a specific date
python run_daily_trade_surveillance.py 25082025

# The system will automatically:
# 1. Process emails (if needed)
# 2. Process audio files
# 3. Validate audio-order mapping
# 4. Transcribe calls
# 5. Run AI analysis
# 6. Validate email-order mapping
# 7. Generate final report
```

### Individual Step Execution:
```bash
# Run individual steps if needed
python extract_call_info_august_daily.py 25082025
python comprehensive_audio_trading_validation_august_daily.py 25082025
python transcribe_calls_august_daily.py 25082025
python order_transcript_analysis_august_daily.py 25082025
python email_order_validation_august_daily.py 25082025
python add_required_columns_to_excel_august_daily.py 25082025
```

### Email Processing Only:
```bash
# Process emails for a specific date
python email_processing/process_emails_by_date.py 2025-08-25
```

---

## ⚙️ Configuration

### Environment Variables (`.env` file):
```env
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Google Vertex AI Configuration
GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json
PROJECT_ID=your_gcp_project_id
LOCATION=us-central1

# Microsoft Graph API Configuration
CLIENT_ID=your_azure_app_client_id
CLIENT_SECRET=your_azure_app_client_secret
TENANT_ID=your_azure_tenant_id
```

### File Paths:
- **Audio Files**: `August/Call Records/Call_YYYYMMDD/`
- **Order Files**: `August/Order Files/OrderBook-Closed-YYYYMMDD.csv`
- **UCC Database**: `August/UCC Database.xlsx`
- **Output Directory**: `August/Daily_Reports/YYYYMMDD/`

### Date Format:
- **Input**: `DDMMYYYY` (e.g., `25082025` for August 25, 2025)
- **Internal Processing**: `YYYY-MM-DD` for API calls
- **File Naming**: `YYYYMMDD` for output files

---

## 📄 Output Files

### Intermediate Files:
1. **`call_info_output_YYYYMMDD.xlsx`**: Audio file metadata and UCC validation
2. **`audio_order_kl_orgtimestamp_validation_YYYYMMDD.xlsx`**: Audio-order mappings
3. **`transcripts_YYYYMMDD/`**: Directory containing transcript files
4. **`order_transcript_analysis_YYYYMMDD.xlsx`**: AI analysis results
5. **`email_order_mapping_YYYYMMDD.xlsx`**: Email-order mappings
6. **`email_surveillance_YYYYMMDD.json`**: Email processing results

### Final Report:
**`Final_Trade_Surveillance_Report_YYYYMMDD_with_Email_and_Trade_Analysis.xlsx`**

**Key Columns**:
- **Order Information**: Order ID, Symbol, Quantity, Price, Buy/Sell
- **Audio Mapping**: Call file name, mobile number, registration status
- **Email Mapping**: Match status, confidence score, discrepancy details
- **Compliance**: Execution status, discussion status, highlighting
- **Content**: Call extracts, email content summaries, AI reasoning

### Highlighting Logic:
Orders are highlighted in **red** when:
- `Call Records matched with Order File (Y/N)` != 'yes'
- `Email-Order Match Status` != 'Matched'
- `Order Executed (Y/N)` == 'Y'

---

## 🔍 Troubleshooting

### Common Issues:

#### 1. Email Processing Failures
**Error**: `Email surveillance file not found`
**Solution**: Check Microsoft Graph API credentials and permissions

#### 2. Audio Transcription Errors
**Error**: `Multiple content parts are not supported`
**Solution**: System continues with other files; check audio file format

#### 3. AI Analysis Failures
**Error**: `JSON parse error (Empty AI response)`
**Solution**: System automatically retries with fallback model (gpt-4)

#### 4. Order ID Mismatches
**Error**: Scientific notation in order IDs
**Solution**: System includes normalization logic for order ID comparison

#### 5. File Not Found Errors
**Error**: Missing order files or audio directories
**Solution**: Verify data files exist for the specified date

### Debug Commands:
```bash
# Check if data files exist
ls August/Call\ Records/Call_25082025/
ls August/Order\ Files/OrderBook-Closed-25082025.csv

# Verify email surveillance file
ls email_surveillance_25082025.json

# Check final report
ls August/Daily_Reports/25082025/Final_Trade_Surveillance_Report_25082025_with_Email_and_Trade_Analysis.xlsx
```

---

## 🔌 API Integration

### Microsoft Graph API
**Purpose**: Email access and processing
**Authentication**: OAuth 2.0 with client credentials
**Endpoints**: `/me/messages` for email retrieval
**Rate Limits**: Handled with pagination and batching

### OpenAI API
**Purpose**: AI analysis and matching
**Models**: o3 (primary), gpt-4 (fallback)
**Usage**: Text analysis, order matching, discrepancy detection
**Error Handling**: Automatic retry with fallback models

### Google Vertex AI
**Purpose**: Audio transcription
**Model**: Gemini-2.5-flash
**Input**: Audio files (.wav format)
**Output**: Text transcripts
**Error Handling**: Graceful failure with continuation

---

## 📈 Performance Metrics

### Processing Times (Typical):
- **Email Processing**: 30-60 seconds
- **Audio File Processing**: 1-2 seconds
- **Audio-Order Validation**: 1-2 seconds
- **Audio Transcription**: 60-120 seconds (depends on file count)
- **AI Analysis**: 30-90 seconds
- **Email-Order Validation**: 5-10 seconds
- **Final Report Generation**: 2-5 seconds

### Coverage Metrics:
- **Audio Coverage**: 40-100% (varies by date)
- **Email Coverage**: 0-100% (varies by date)
- **Overall Coverage**: 60-95% (combined audio + email)
- **Highlighted Orders**: 0-25% (orders without sources)

---

## 🔒 Security and Compliance

### Data Protection:
- **API Keys**: Stored in environment variables
- **Sensitive Data**: No hardcoded credentials
- **File Access**: Restricted to necessary directories
- **Error Handling**: No sensitive data in error messages

### Compliance Features:
- **Audit Trail**: Complete processing logs
- **Source Validation**: Dual-source verification
- **Discrepancy Detection**: Automated flagging
- **Visual Indicators**: Highlighted compliance issues

---

## 📞 Support and Maintenance

### Regular Maintenance:
1. **API Key Rotation**: Update credentials as needed
2. **Data Cleanup**: Remove old intermediate files
3. **Log Monitoring**: Check processing logs for errors
4. **Performance Tuning**: Optimize based on usage patterns

### Monitoring:
- **Processing Success Rates**: Track step completion rates
- **Coverage Metrics**: Monitor audio and email coverage
- **Error Rates**: Track and resolve common failures
- **Performance Metrics**: Monitor processing times

---

## 📚 Additional Resources

### Documentation Files:
- `email_processing/EMAIL_DAILY_PROCESS.md`: Detailed email process
- `trade_surveillance_process.md`: Overall process documentation
- `trade_surveillance_solution.md`: Solution architecture

### Configuration Files:
- `.env`: Environment variables
- `requirements.txt`: Python dependencies
- `August/UCC Database.xlsx`: Client-mobile mapping

### Sample Commands:
```bash
# Run complete process
python run_daily_trade_surveillance.py 25082025

# Check processing status
ls August/Daily_Reports/25082025/

# View final report
open August/Daily_Reports/25082025/Final_Trade_Surveillance_Report_25082025_with_Email_and_Trade_Analysis.xlsx
```

---

*This documentation covers the complete Trade Surveillance System. For specific implementation details, refer to the individual script files and their inline documentation.*
