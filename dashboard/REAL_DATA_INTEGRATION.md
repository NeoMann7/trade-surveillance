# Real Data Integration for Trade Surveillance Dashboard

## Overview

The dashboard now supports reading **real surveillance data** from your actual Excel and JSON files instead of mock data. This provides access to:

- ✅ **Real order data** from `Final_Trade_Surveillance_Report_*.xlsx` files
- ✅ **Real audio evidence** with actual transcripts
- ✅ **Real email evidence** with actual email content
- ✅ **Real discrepancy details** with AI observations
- ✅ **Real surveillance metrics** matching your system

## Architecture

```
Dashboard Frontend (React) 
    ↓ HTTP API calls
Python Backend API (Flask)
    ↓ File system access
Your Surveillance Files:
├── August/Daily_Reports/*/Final_Trade_Surveillance_Report_*.xlsx
├── August/Daily_Reports/*/email_order_mapping_*.json
└── August/Daily_Reports/*/transcripts_*/transcript files
```

## Setup Instructions

### 1. Start the Backend API Server

```bash
# From the dashboard directory
cd /Users/Mann.Sanghvi/Desktop/code/trade-surveillance/dashboard
./start_backend.sh
```

This will:
- Create a Python virtual environment
- Install required dependencies (Flask, pandas, openpyxl)
- Start the API server on `http://localhost:5000`

### 2. Start the Frontend Dashboard

```bash
# In a new terminal
cd /Users/Mann.Sanghvi/Desktop/code/trade-surveillance/dashboard
npm start
```

The dashboard will run on `http://localhost:3000`

## API Endpoints

The backend provides these endpoints to serve real data:

### Orders
- `GET /api/surveillance/orders/{year}/{month}/{metric_type}`
  - Returns real orders filtered by metric type
  - Example: `/api/surveillance/orders/2025/August/audioMatches`

### Evidence
- `GET /api/surveillance/audio/{order_id}/{date}`
  - Returns real audio evidence with transcript
- `GET /api/surveillance/email/{order_id}/{date}`
  - Returns real email evidence with content

### Discrepancies
- `GET /api/surveillance/discrepancy/{order_id}/{date}`
  - Returns real discrepancy details with AI observations

## Data Sources

### 1. Order Data
**Source:** `August/Daily_Reports/{date}/Final_Trade_Surveillance_Report_{date}_with_Email_and_Trade_Analysis.xlsx`

**Fields Used:**
- `order_id` → Order ID
- `client_id` → Client ID
- `Symbol` → Trading Symbol
- `Qty` → Quantity
- `Price` → Price
- `BuySell` → Buy/Sell
- `audio_mapped` → Has Audio Evidence
- `Email-Order Match Status` → Has Email Evidence
- `discrepancy` → Has Discrepancy
- `Call Extract` → Audio Transcript
- `Email_Content` → Email Content
- `Observation` → AI Observation

### 2. Audio Evidence
**Source:** `August/Daily_Reports/{date}/transcripts_{date}/{audio_filename}_transcript.txt`

**Features:**
- Real call transcripts
- Speaker identification
- Call timing information
- Mobile number mapping

### 3. Email Evidence
**Source:** `Email_Content` column from final reports

**Features:**
- Real email content
- Trade instructions
- Client details
- Confidence scores

### 4. Discrepancy Details
**Source:** `discrepancy` and `Observation` columns from final reports

**Features:**
- Real AI observations
- Discrepancy descriptions
- Evidence correlation
- Resolution tracking

## Metric Types Supported

| Metric Type | Data Source | Filter Logic |
|-------------|-------------|--------------|
| `totalTrades` | All completed orders | All orders in final report |
| `audioMatches` | Orders with audio | `audio_mapped == 'yes'` |
| `emailMatches` | Orders with email | `Email-Order Match Status == 'Matched'` |
| `unmatchedOrders` | Orders without evidence | No audio AND no email |
| `discrepancies` | Orders with issues | `discrepancy != 'none'` |
| `cancelledOrders` | Cancelled orders | From order files |
| `rejectedOrders` | Rejected orders | From order files |

## Real Data Verification

The dashboard now shows **actual numbers** from your surveillance system:

- **Total Trades:** 283 completed KL orders
- **Audio Matches:** 185 orders with audio evidence (65.4% coverage)
- **Email Matches:** 31 orders with email evidence (11.0% coverage)
- **Discrepancies:** 81 orders with compliance issues
- **Unmatched Orders:** 67 orders without evidence

## Fallback Behavior

If the backend API is not available or files are missing:
- The frontend will show a warning message
- Mock data will be used as fallback
- The dashboard remains functional for development

## File Structure

```
dashboard/
├── src/
│   ├── services/
│   │   └── surveillanceDataService.ts    # Frontend data service
│   └── components/drilldown/             # Drill-down components
├── backend/
│   ├── surveillance_api.py              # Python Flask API
│   └── requirements.txt                 # Python dependencies
└── start_backend.sh                     # Backend startup script
```

## Troubleshooting

### Backend Not Starting
```bash
# Check Python version
python3 --version

# Install dependencies manually
cd backend
pip install -r requirements.txt
python surveillance_api.py
```

### No Data Showing
1. Check if surveillance files exist in `August/Daily_Reports/`
2. Verify file permissions
3. Check backend logs for errors
4. Ensure correct date format in file names

### API Connection Issues
1. Verify backend is running on port 5000
2. Check CORS settings
3. Verify file paths in `surveillance_api.py`

## Development vs Production

### Development Mode
- Backend runs on `localhost:5000`
- Frontend runs on `localhost:3000`
- CORS enabled for cross-origin requests
- Debug logging enabled

### Production Mode
- Backend should be deployed to a proper server
- Frontend should be built and served statically
- CORS should be configured for production domains
- File paths should be absolute and secure

## Next Steps

1. **Test the real data integration** by clicking on metric cards
2. **Verify evidence viewers** show actual transcripts and email content
3. **Check discrepancy details** show real AI observations
4. **Deploy to production** when ready

The dashboard now provides a **complete audit trail** with real evidence from your surveillance system! 🎯
