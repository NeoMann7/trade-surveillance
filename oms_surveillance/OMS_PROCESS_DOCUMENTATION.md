# OMS Order Alert Email Processing - Complete Documentation

## Overview

This document describes the complete OMS (Order Management System) Order Alert email processing system that has been implemented as a separate, independent process from the regular email surveillance system.

## System Architecture

The OMS process consists of the following components:

1. **OMS Email Fetcher** - Fetches OMS emails from Microsoft Graph API
2. **OMS Email Parser** - Parses OMS emails using Python regex (no AI needed)
3. **Wealth Spectrum API Client** - Maps client codes to actual UCC codes
4. **OMS Order Validator** - Matches OMS orders to order book and updates Excel
5. **Master OMS Surveillance Script** - Orchestrates the entire process

## Process Flow

```
1. Fetch OMS Emails (Graph API)
   ↓
2. Parse OMS Emails (Python Regex)
   ↓
3. Map Client Codes (Wealth Spectrum API)
   ↓
4. Load Order Book (CSV Files)
   ↓
5. Match Orders (AI-like Logic)
   ↓
6. Update Excel File
```

## Key Features

### 1. Independent Processing
- **Completely separate** from regular email surveillance
- **No interference** with existing email processing
- **Dedicated file structure** and processing pipeline

### 2. Fixed Structure Parsing
- **No AI required** for OMS email parsing
- **Python regex-based** extraction for reliable, fast processing
- **Structured data extraction** from HTML table format

### 3. Client Code Mapping
- **Wealth Spectrum API integration** for client code mapping
- **USERNAME/CLIENTCODE → REFCODE6** mapping
- **Batch processing** for multiple client codes

### 4. Order Matching
- **AI-like matching logic** between OMS orders and KL orders
- **Symbol and side matching** with confidence scoring
- **Extensible matching criteria** for future enhancements

### 5. Excel Integration
- **Reuses existing columns** (no new columns added)
- **Email_Match_Type = 'OMS_MATCH'** for identification
- **Seamless integration** with existing surveillance reports

## File Structure

```
oms_surveillance/
├── fetch_oms_emails.py          # OMS email fetching from Graph API
├── oms_order_alert_processor.py # OMS email parsing and analysis
├── wealth_spectrum_api_client.py # Client code mapping API client
├── oms_order_validation.py      # Order matching and Excel updates
├── run_oms_surveillance.py      # Master orchestration script
└── OMS_PROCESS_DOCUMENTATION.md # This documentation
```

## Data Flow

### Input Data
- **OMS Emails**: "New Order Alert - OMS!" emails from Graph API
- **Order Book**: KL orders CSV files
- **Client Master**: Wealth Spectrum API client data

### Processing Steps
1. **Email Fetching**: Filter and fetch OMS emails by date
2. **Email Parsing**: Extract order details using regex patterns
3. **Client Mapping**: Map Wealth Spectrum codes to actual client codes
4. **Order Matching**: Match OMS orders to KL orders
5. **Excel Update**: Update surveillance Excel with OMS matches

### Output Data
- **OMS Surveillance Results**: `oms_email_surveillance_YYYYMMDD.json`
- **Updated Excel**: Enhanced with OMS match data
- **Processing Logs**: Detailed processing information

## API Integration

### Wealth Spectrum API
- **Endpoint**: `https://ws.neo-wealth.com/wealthspectrum/app/api/boQueries/execute`
- **Authentication**: Bearer token
- **Query**: ClientMaster.xml for client data
- **Mapping**: USERNAME/CLIENTCODE → REFCODE6

### Microsoft Graph API
- **Email Filtering**: Subject contains "New Order Alert - OMS!"
- **Date Range**: Configurable date filtering
- **Content Extraction**: HTML table parsing

## Error Handling

### Robust Error Management
- **Graceful degradation** for missing data
- **Detailed logging** for troubleshooting
- **Partial success handling** for batch operations
- **Retry mechanisms** for API calls

### Validation Checks
- **Date format validation**
- **File existence checks**
- **Data integrity verification**
- **API response validation**

## Performance Considerations

### Optimization Features
- **Batch API calls** for client code mapping
- **Efficient regex patterns** for email parsing
- **Memory-efficient** data processing
- **Parallel processing** capabilities

### Scalability
- **Configurable date ranges**
- **Batch processing** for multiple dates
- **Resource management** for large datasets
- **Modular architecture** for easy extension

## Usage Examples

### Single Date Processing
```bash
python run_oms_surveillance.py 20250902
```

### Batch Processing
```bash
python run_oms_surveillance.py 20250901 20250902 20250903
```

### Individual Component Testing
```bash
# Test OMS email parsing
python oms_order_alert_processor.py input_file.json

# Test client code mapping
python wealth_spectrum_api_client.py

# Test order validation
python oms_order_validation.py 20250902
```

## Configuration

### Environment Variables
- **Graph API credentials** (inherited from main system)
- **Wealth Spectrum API token** (configurable)
- **File paths** (configurable)
- **Processing parameters** (configurable)

### Customization Options
- **Matching thresholds** for order matching
- **Date ranges** for processing
- **Output formats** for results
- **Logging levels** for debugging

## Monitoring and Logging

### Comprehensive Logging
- **Processing steps** with timestamps
- **Success/failure rates** for each component
- **Performance metrics** for optimization
- **Error details** for troubleshooting

### Status Reporting
- **Real-time progress** updates
- **Summary statistics** for each run
- **Error notifications** for failures
- **Success confirmations** for completion

## Future Enhancements

### Planned Improvements
- **Advanced AI matching** algorithms
- **Real-time processing** capabilities
- **Dashboard integration** for monitoring
- **Automated scheduling** for regular runs

### Extensibility
- **Plugin architecture** for new data sources
- **Custom matching rules** for different order types
- **API versioning** for backward compatibility
- **Multi-tenant support** for different clients

## Troubleshooting

### Common Issues
1. **API Authentication**: Check token validity and permissions
2. **File Not Found**: Verify file paths and date formats
3. **Parsing Errors**: Check email format changes
4. **Mapping Failures**: Verify client code formats

### Debug Mode
- **Verbose logging** for detailed information
- **Step-by-step execution** for isolation
- **Data validation** at each stage
- **Error recovery** mechanisms

## Conclusion

The OMS Order Alert email processing system provides a robust, independent solution for processing OMS emails with fixed structure parsing, client code mapping, and order validation. The system is designed for reliability, performance, and easy maintenance while remaining completely separate from the existing email surveillance infrastructure.

## Support

For technical support or questions about the OMS processing system, please refer to the logging output and error messages for detailed information about any issues encountered during processing.
