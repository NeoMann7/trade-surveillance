# Trade Surveillance Dashboard - Development Brief

## 📋 Project Overview

**Purpose:** Create a comprehensive dashboard for compliance officers to monitor and analyze trade surveillance results.

**Technology Stack:** React + shadcn/ui components + TypeScript

**Target Users:** Compliance officers and trading supervisors

---

## 🎯 Core Requirements

### **Dashboard Capabilities**
- ✅ **Visualization Layer:** Reads from existing surveillance output files
- ✅ **Process Execution:** Compliance team can run surveillance process directly
- ✅ **File Management:** Upload audio files, trade files, and UCC database
- ✅ **Real-time Monitoring:** Live updates during surveillance execution
- ✅ **No Changes to Core Logic:** Uses existing Python surveillance scripts as-is

---

## 🏗️ Dashboard Architecture

### **Layout Structure**
```
┌─────────────────────────────────────────────────────────┐
│                    Header Bar                           │
│  Trade Surveillance Dashboard | User Info | Settings   │
├─────────────┬───────────────────────────────────────────┤
│             │                                           │
│   Sidebar   │              Main Content                 │
│             │                                           │
│  📅 Months  │        Month Summary View                 │
│  • June     │    ┌─────────┬─────────┬─────────┐        │
│  • July     │    │ Total   │ Email   │ Audio   │        │
│  • August   │    │ Trades  │ Matches │ Matches │        │
│  • Sept     │    └─────────┴─────────┴─────────┘        │
│             │    ┌─────────┬─────────┐                  │
│             │    │ Unmatched│ Discrep.│                  │
│             │    │ Orders   │ Count   │                  │
│             │    └─────────┴─────────┘                  │
│             │                                           │
│  🚀 Actions │        Drill-down Views                   │
│  • Run New  │    (Order Details, Evidence, etc.)        │
│  • Upload   │                                           │
│  • Monitor  │        Process Execution View             │
│             │    ┌─────────────────────────────┐        │
│             │    │ Step 1: Audio Processing    │ ✅     │
│             │    │ Step 2: Email Processing    │ 🔄     │
│             │    │ Step 3: AI Analysis         │ ⏳     │
│             │    │ Step 4: Report Generation   │ ⏳     │
│             │    └─────────────────────────────┘        │
└─────────────┴───────────────────────────────────────────┘
```

---

## 📊 Data Sources

### **Primary Data Files**
1. **Final Reports:** `Final_Trade_Surveillance_Report_YYYYMMDD_with_Email_and_Trade_Analysis.xlsx`
2. **Email Mapping:** `email_order_mapping_YYYYMMDD.xlsx`
3. **Audio Analysis:** `order_transcript_analysis_YYYYMMDD.xlsx`
4. **Call Info:** `call_info_output_YYYYMMDD.xlsx`
5. **Email Surveillance:** `email_surveillance_YYYYMMDD.json`

### **Evidence Files**
- **Audio Files:** `August/Call Records/Call_YYYYMMDD/`
- **Email Content:** Extracted from JSON surveillance files
- **Transcripts:** `August/Daily_Reports/YYYYMMDD/transcripts_YYYYMMDD/`

---

## 🎨 UI Components (shadcn/ui)

### **Layout Components**
- `Sidebar` - Month navigation
- `Card` - Metric display containers
- `Badge` - Status indicators
- `Button` - Action buttons
- `Tabs` - Day-wise view switching

### **Data Display Components**
- `Table` - Order listings with sorting/filtering
- `Dialog` - Evidence viewer modals
- `Alert` - Discrepancy notifications
- `Progress` - Processing status indicators
- `Tooltip` - Hover information

### **Charts & Visualization**
- `Chart` components for trend analysis
- Custom data visualization for compliance metrics

---

## 📱 Feature Specifications

### **1. Process Execution & File Management**

#### **New Surveillance Run**
```typescript
interface SurveillanceRun {
  id: string;
  date: string;           // DDMMYYYY format
  status: 'pending' | 'running' | 'completed' | 'failed';
  steps: SurveillanceStep[];
  uploadedFiles: UploadedFile[];
  startTime: Date;
  endTime?: Date;
  errorMessage?: string;
}

interface SurveillanceStep {
  name: string;           // "Audio Processing", "Email Processing", etc.
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: number;       // 0-100
  startTime?: Date;
  endTime?: Date;
  output?: string;
  errorMessage?: string;
}

interface UploadedFile {
  type: 'audio' | 'trade' | 'ucc';
  name: string;
  size: number;
  uploadTime: Date;
  status: 'uploaded' | 'validating' | 'valid' | 'invalid';
  validationMessage?: string;
}
```

#### **File Upload Interface**
- **Audio Files:** Drag & drop multiple audio files
- **Trade Files:** Upload CSV order files
- **UCC Database:** Upload Excel UCC database file
- **Validation:** Real-time file validation and feedback
- **Progress:** Upload progress indicators

#### **Process Execution**
- **Date Selection:** Choose surveillance date (DDMMYYYY format)
- **Step Monitoring:** Real-time progress of each surveillance step
- **Log Streaming:** Live log output from Python scripts
- **Error Handling:** Clear error messages and recovery options
- **Auto-refresh:** Dashboard updates automatically when process completes

### **2. Month Navigation (Sidebar)**
```typescript
interface MonthData {
  month: string;        // "August", "July", etc.
  year: number;         // 2025
  totalTrades: number;
  emailMatches: number;
  audioMatches: number;
  unmatchedOrders: number;
  discrepancies: number;
  lastUpdated: Date;
  hasRecentRun: boolean; // True if surveillance was run recently
  runStatus?: 'completed' | 'running' | 'failed';
}
```

**Functionality:**
- List all available months with data
- Show summary metrics for each month
- Highlight current selected month
- Show recent run status indicators
- Auto-refresh when new data is available
- Quick access to run new surveillance for any month

### **3. Month Summary View**
**Key Metrics Cards:**
- **Total Trades** - Count of all orders processed
- **Email Matches** - Orders with email evidence
- **Audio Matches** - Orders with audio evidence  
- **Unmatched Orders** - Orders without evidence
- **Discrepancies** - Orders with compliance issues

**Each metric card includes:**
- Large number display
- Percentage change from previous month
- Click-to-drill-down functionality
- Color coding (green/yellow/red based on compliance)

### **4. Day-wise View**
**Toggle between:**
- Month summary view
- Daily breakdown view

**Daily view shows:**
- Calendar grid with daily metrics
- Click on any day to see that day's details
- Trend indicators (up/down arrows)
- Quick access to daily reports

### **5. Drill-down Capabilities**

#### **Total Trades Drill-down**
```typescript
interface OrderDetail {
  orderId: string;
  clientId: string;
  symbol: string;
  quantity: number;
  price: number;
  timestamp: Date;
  status: 'compliant' | 'flagged' | 'pending';
  audioEvidence?: AudioEvidence;
  emailEvidence?: EmailEvidence;
  discrepancies?: Discrepancy[];
  aiObservations?: string[];
}
```

**Display:**
- Sortable/filterable table of all orders
- Status badges (compliant/flagged/pending)
- Quick access to evidence files
- AI observation highlights

#### **Email Matches Drill-down**
- Orders with email evidence
- Email content preview
- Full email thread access
- Confidence scores from AI analysis

#### **Audio Matches Drill-down**
- Orders with audio evidence
- Audio file playback controls
- Transcript display
- Call duration and timing

#### **Unmatched Orders Drill-down**
- Orders without evidence
- Highlighted for manual review
- Bulk action capabilities
- Export for compliance review

#### **Discrepancies Drill-down**
- Orders with compliance issues
- Detailed discrepancy descriptions
- Severity levels (high/medium/low)
- Recommended actions

---

## 🔍 Evidence Viewer

### **Audio Evidence Modal**
- Audio player with waveform visualization
- Transcript display with timestamps
- Order matching confidence score
- Download audio file option

### **Email Evidence Modal**
- Full email thread display
- Order instruction extraction
- AI analysis results
- Attachment access

### **Discrepancy Details**
- Clear description of the issue
- Affected order details
- Recommended resolution steps
- Historical similar cases

---

## 📈 Advanced Features

### **Process Management**
- **Queue Management:** Multiple surveillance runs can be queued
- **Resource Monitoring:** CPU, memory, and disk usage during processing
- **Log Management:** Centralized logging with search and filtering
- **Backup & Recovery:** Automatic backup of surveillance results
- **Scheduling:** Option to schedule surveillance runs for specific dates

### **Search & Filtering**
- Global search across all orders
- Filter by client, symbol, date range
- Advanced filters for compliance status
- Saved filter presets

### **Export Capabilities**
- Export filtered results to Excel
- Generate compliance reports
- PDF summary reports
- Bulk evidence download

### **Real-time Updates**
- Auto-refresh when new surveillance runs complete
- Push notifications for new discrepancies
- Live status updates during processing

### **Compliance Workflow**
- Mark orders as reviewed
- Add compliance notes
- Escalate to supervisors
- Track resolution status

---

## 🎨 Design System

### **Color Scheme**
- **Primary:** Blue (#3b82f6) - Trust, compliance
- **Success:** Green (#10b981) - Compliant orders
- **Warning:** Yellow (#f59e0b) - Pending review
- **Error:** Red (#ef4444) - Discrepancies
- **Neutral:** Gray (#6b7280) - Unmatched orders

### **Typography**
- **Headers:** Inter font family
- **Body:** System font stack
- **Code:** JetBrains Mono

### **Spacing & Layout**
- Consistent 8px grid system
- Card-based layout with subtle shadows
- Responsive design for different screen sizes
- Dark/light mode support

---

## 🚀 Implementation Plan

### **Phase 1: Core Dashboard**
1. Set up React + shadcn/ui project
2. Implement sidebar navigation
3. Create month summary view
4. Basic drill-down functionality

### **Phase 2: Process Execution**
1. File upload interface with drag & drop
2. Integration with existing Python surveillance scripts
3. Real-time process monitoring and progress tracking
4. Error handling and recovery mechanisms

### **Phase 3: Data Integration**
1. Connect to existing Excel/JSON files
2. Implement data parsing and caching
3. Add real-time file monitoring
4. Auto-refresh when new surveillance completes

### **Phase 4: Advanced Features**
1. Evidence viewer modals
2. Search and filtering
3. Export capabilities
4. Compliance workflow tools
5. Process queue management

### **Phase 5: Polish & Optimization**
1. Performance optimization
2. Mobile responsiveness
3. Accessibility improvements
4. User testing and refinements

---

## 📁 Project Structure

```
trade-surveillance-dashboard/
├── src/
│   ├── components/
│   │   ├── ui/                 # shadcn/ui components
│   │   ├── layout/
│   │   │   ├── Sidebar.tsx
│   │   │   ├── Header.tsx
│   │   │   └── MainContent.tsx
│   │   ├── dashboard/
│   │   │   ├── MonthSummary.tsx
│   │   │   ├── MetricCard.tsx
│   │   │   └── DayView.tsx
│   │   ├── process/
│   │   │   ├── FileUpload.tsx
│   │   │   ├── ProcessMonitor.tsx
│   │   │   ├── StepProgress.tsx
│   │   │   └── LogViewer.tsx
│   │   ├── drilldown/
│   │   │   ├── OrderTable.tsx
│   │   │   ├── EvidenceViewer.tsx
│   │   │   └── DiscrepancyDetails.tsx
│   │   └── charts/
│   │       ├── ComplianceChart.tsx
│   │       └── TrendChart.tsx
│   ├── hooks/
│   │   ├── useSurveillanceData.ts
│   │   ├── useFileWatcher.ts
│   │   ├── useProcessExecution.ts
│   │   └── useExport.ts
│   ├── services/
│   │   ├── dataParser.ts
│   │   ├── fileWatcher.ts
│   │   ├── processExecutor.ts
│   │   ├── fileUpload.ts
│   │   └── exportService.ts
│   ├── types/
│   │   ├── surveillance.ts
│   │   ├── order.ts
│   │   ├── evidence.ts
│   │   └── process.ts
│   └── utils/
│       ├── dateUtils.ts
│       ├── formatters.ts
│       └── constants.ts
├── backend/
│   ├── surveillance_runner.py  # Wrapper for existing Python scripts
│   ├── file_handler.py         # File upload and validation
│   └── process_monitor.py      # Process status monitoring
├── public/
│   └── assets/
└── package.json
```

---

## ✅ Success Criteria

1. **Performance:** Dashboard loads within 2 seconds
2. **Usability:** Compliance officers can find any order within 30 seconds
3. **Process Execution:** Surveillance runs complete successfully with real-time monitoring
4. **File Management:** Upload and validation of files works seamlessly
5. **Reliability:** 99.9% uptime with proper error handling
6. **Accessibility:** WCAG 2.1 AA compliance
7. **Mobile:** Responsive design for tablet access

---

## 🔧 Technical Considerations

### **Data Processing**
- Parse Excel files using `xlsx` library
- Handle large datasets with virtualization
- Implement efficient caching strategy
- Background file monitoring
- Real-time process status updates via WebSocket/SSE

### **Process Execution**
- Python subprocess management for surveillance scripts
- File upload handling with validation
- Process queue management for multiple runs
- Log streaming and error capture
- Resource monitoring during execution

### **Security**
- No sensitive data in client-side code
- Secure file access patterns
- Audit logging for compliance actions
- Role-based access control
- File upload security and validation

### **Performance**
- Lazy loading for large datasets
- Virtual scrolling for order tables
- Optimized re-renders with React.memo
- Service worker for offline capability
- Efficient file upload with progress tracking

---

**Ready for Development Approval?** 

This brief provides a comprehensive roadmap for building a professional, compliance-focused dashboard using modern React and shadcn/ui components. The design prioritizes usability for compliance officers while maintaining the integrity of your existing surveillance system.
