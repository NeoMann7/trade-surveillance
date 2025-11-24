# Dashboard KL Orders Requirement

## Overview
The Trade Surveillance Dashboard is designed to focus **exclusively on KL (Kotak Life) orders** for compliance monitoring and surveillance analysis.

## KL Orders Definition
- **KL Orders**: Orders placed by dealers with client IDs starting with "KL" (e.g., KL01, KL02, KL03, etc.)
- **Purpose**: These are dealer-placed orders that require special surveillance and compliance monitoring
- **Scope**: All dashboard metrics, reports, and analysis should be filtered to show only KL orders

## Dashboard Metrics (KL Orders Only)
The dashboard displays the following metrics for **completed KL orders only**:

### Primary Metrics
- **Total KL Trades**: Completed KL orders only (from surveillance reports)
- **Completed KL Orders**: Successfully executed KL orders
- **Cancelled KL Orders**: Not included (surveillance reports only contain completed orders)
- **Rejected KL Orders**: Not included (surveillance reports only contain completed orders)

### Evidence Metrics
- **KL Orders with Email Evidence**: KL orders matched to email instructions
- **KL Orders with Audio Evidence**: KL orders matched to call recordings
- **KL Orders with Discrepancies**: KL orders with compliance issues
- **Unmatched KL Orders**: KL orders without email or audio evidence

## Data Sources
1. **Surveillance Reports**: Completed KL orders with evidence analysis (PRIMARY SOURCE)
2. **Call Records**: Audio evidence for KL orders
3. **Email Data**: Email instructions for KL orders
4. **Order Files**: Not used (contain all orders, not just completed KL orders)

## Filtering Logic
- **Surveillance Reports Only**: Dashboard uses only surveillance reports (Final_Trade_Surveillance_Report_*_with_Email_and_Trade_Analysis.xlsx)
- **Completed Orders Only**: Surveillance reports contain only completed KL orders
- **Dealer Orders**: Focus on orders placed by dealers (KL01, KL02, KL03, etc.)
- **Compliance Focus**: Special attention to completed dealer-placed orders for regulatory compliance

## Implementation Notes
- All API endpoints should filter for KL orders only
- Dashboard UI should clearly indicate "KL Orders" in all metrics
- Reports and exports should be limited to KL orders
- Evidence analysis should focus on KL order compliance

## Compliance Purpose
This filtering ensures the dashboard provides focused surveillance on:
- Dealer trading activities
- Regulatory compliance for dealer-placed orders
- Risk management for institutional trading
- Audit trails for dealer-client interactions

---
**Last Updated**: October 7, 2025
**Status**: Active Requirement
