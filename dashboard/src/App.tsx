import React, { useState, useEffect, useCallback } from 'react';
import { Header } from './components/layout/Header';
import { Sidebar } from './components/layout/Sidebar';
import { MonthSummary } from './components/dashboard/MonthSummary';
import { DrillDownView } from './components/drilldown/DrillDownView';
import { DateFilter } from './components/filters/DateFilter';
import { SurveillanceRunner } from './components/surveillance/SurveillanceRunner';
import { FileUpload } from './components/upload/FileUpload';
import { surveillanceDataService } from './services/surveillanceDataService';

function App() {
  const [selectedMonth, setSelectedMonth] = useState('September');
  const [currentView, setCurrentView] = useState<'dashboard' | 'process' | 'upload' | 'drilldown'>('dashboard');
  const [drillDownMetric, setDrillDownMetric] = useState<string>('');
  
  // Date filtering state
  const [dateFilter, setDateFilter] = useState<{
    startDate: string | null;
    endDate: string | null;
  }>({ startDate: null, endDate: null });

  // Fetch real data from backend - OPTIMIZED: Use metrics endpoint (counts only, not full order lists)
  const fetchRealData = useCallback(async () => {
    try {
        // Fetch all months in parallel using fast metrics endpoint (returns counts only)
        const [augustMetrics, septemberMetrics, octoberMetrics, novemberMetrics, decemberMetrics, januaryMetrics] = await Promise.all([
          surveillanceDataService.getMetricsForMonth('August', 2025),
          surveillanceDataService.getMetricsForMonth('September', 2025),
          surveillanceDataService.getMetricsForMonth('October', 2025),
          surveillanceDataService.getMetricsForMonth('November', 2025),
          surveillanceDataService.getMetricsForMonth('December', 2025),
          surveillanceDataService.getMetricsForMonth('January', 2026)
        ]);

        setRealData(prev => ({
          ...prev,
          August: {
            ...prev.August,
            ...augustMetrics
          },
          September: {
            ...prev.September,
            ...septemberMetrics
          },
          October: {
            ...prev.October,
            ...octoberMetrics
          },
          November: {
            ...prev.November,
            ...novemberMetrics
          },
          December: {
            ...prev.December,
            ...decemberMetrics
          },
          January: {
            ...prev.January,
            ...januaryMetrics
          }
        }));
      } catch (error) {
        console.error('Error fetching real data:', error);
      }
    }, []);

  useEffect(() => {
    fetchRealData();
  }, [fetchRealData]);

  // Fetch filtered data when date filter changes - OPTIMIZED: Use metrics endpoint
  useEffect(() => {
    const fetchFilteredData = async () => {
      if (!dateFilter.startDate && !dateFilter.endDate) {
        return; // No filter applied, use existing data
      }

      try {
        const currentYear = selectedMonth === 'January' ? 2026 : 2025;
        const metrics = await surveillanceDataService.getMetricsForMonth(
          selectedMonth, 
          currentYear, 
          dateFilter.startDate || undefined, 
          dateFilter.endDate || undefined
        );

        setRealData(prev => ({
          ...prev,
          [selectedMonth]: {
            ...prev[selectedMonth as keyof typeof prev],
            ...metrics
          }
        }));
      } catch (error) {
        console.error('Error fetching filtered data:', error);
      }
    };

    fetchFilteredData();
  }, [dateFilter.startDate, dateFilter.endDate, selectedMonth]);

  // Real data from surveillance system (fetched from backend)
  const [realData, setRealData] = useState({
    August: {
      month: 'August',
      year: 2025,
      totalTrades: 0, // Will be fetched from backend
      emailMatches: 0, // Will be fetched from backend
      omsMatches: 0, // Will be fetched from backend
      audioMatches: 0, // Will be fetched from backend
      unmatchedOrders: 0, // Will be calculated
      actualDiscrepancies: 0, // Will be fetched from backend
      reportingDiscrepancies: 0, // Will be fetched from backend
      cancelledOrders: 0, // Will be fetched from backend
      rejectedOrders: 0 // Will be fetched from backend
    },
    July: {
      month: 'July',
      year: 2025,
      totalTrades: 0, // No July data available yet
      emailMatches: 0,
      omsMatches: 0,
      audioMatches: 0,
      unmatchedOrders: 0,
      actualDiscrepancies: 0,
      reportingDiscrepancies: 0,
      cancelledOrders: 0,
      rejectedOrders: 0
    },
    September: {
      month: 'September',
      year: 2025,
      totalTrades: 0, // Will be fetched from backend
      emailMatches: 0, // Will be fetched from backend
      omsMatches: 0, // Will be fetched from backend
      audioMatches: 0, // Will be fetched from backend
      unmatchedOrders: 0, // Will be calculated
      actualDiscrepancies: 0, // Will be fetched from backend
      reportingDiscrepancies: 0, // Will be fetched from backend
      cancelledOrders: 0, // Will be fetched from backend
      rejectedOrders: 0 // Will be fetched from backend
    },
    October: {
      month: 'October',
      year: 2025,
      totalTrades: 0, // Will be fetched from backend
      emailMatches: 0, // Will be fetched from backend
      omsMatches: 0, // Will be fetched from backend
      audioMatches: 0, // Will be fetched from backend
      unmatchedOrders: 0, // Will be calculated
      actualDiscrepancies: 0, // Will be fetched from backend
      reportingDiscrepancies: 0, // Will be fetched from backend
      cancelledOrders: 0, // Will be fetched from backend
      rejectedOrders: 0 // Will be fetched from backend
    },
    November: {
      month: 'November',
      year: 2025,
      totalTrades: 0, // Will be fetched from backend
      emailMatches: 0, // Will be fetched from backend
      omsMatches: 0, // Will be fetched from backend
      audioMatches: 0, // Will be fetched from backend
      unmatchedOrders: 0, // Will be calculated
      actualDiscrepancies: 0, // Will be fetched from backend
      reportingDiscrepancies: 0, // Will be fetched from backend
      cancelledOrders: 0, // Will be fetched from backend
      rejectedOrders: 0 // Will be fetched from backend
    },
    December: {
      month: 'December',
      year: 2025,
      totalTrades: 0, // Will be fetched from backend
      emailMatches: 0, // Will be fetched from backend
      omsMatches: 0, // Will be fetched from backend
      audioMatches: 0, // Will be fetched from backend
      unmatchedOrders: 0, // Will be calculated
      actualDiscrepancies: 0, // Will be fetched from backend
      reportingDiscrepancies: 0, // Will be fetched from backend
      cancelledOrders: 0, // Will be fetched from backend
      rejectedOrders: 0 // Will be fetched from backend
    },
    January: {
      month: 'January',
      year: 2026,
      totalTrades: 0, // Will be fetched from backend
      emailMatches: 0, // Will be fetched from backend
      omsMatches: 0, // Will be fetched from backend
      audioMatches: 0, // Will be fetched from backend
      unmatchedOrders: 0, // Will be calculated
      actualDiscrepancies: 0, // Will be fetched from backend
      reportingDiscrepancies: 0, // Will be fetched from backend
      cancelledOrders: 0, // Will be fetched from backend
      rejectedOrders: 0 // Will be fetched from backend
    },
    June: {
      month: 'June',
      year: 2025,
      totalTrades: 0, // No June data available yet
      emailMatches: 0,
      omsMatches: 0,
      audioMatches: 0,
      unmatchedOrders: 0,
      actualDiscrepancies: 0,
      reportingDiscrepancies: 0,
      cancelledOrders: 0,
      rejectedOrders: 0
    }
  });

  // Get current month data - fallback to empty data structure if month not found
  const currentMonthData = realData[selectedMonth as keyof typeof realData] || {
    month: selectedMonth,
    year: 2025,
    totalTrades: 0,
    emailMatches: 0,
    omsMatches: 0,
    audioMatches: 0,
    unmatchedOrders: 0,
    actualDiscrepancies: 0,
    reportingDiscrepancies: 0,
    cancelledOrders: 0,
    rejectedOrders: 0
  };

  const handleMonthSelect = (month: string) => {
    console.log(`Selected month: ${month}`);
    setSelectedMonth(month);
    setCurrentView('dashboard');
    // Reset date filter when month changes
    setDateFilter({ startDate: null, endDate: null });
  };

  const handleDateRangeChange = useCallback((startDate: string | null, endDate: string | null) => {
    setDateFilter({ startDate, endDate });
  }, []);

  const handleRunSurveillance = () => {
    console.log('Run Surveillance clicked');
    setCurrentView('process');
  };

  const handleUploadFiles = () => {
    console.log('Upload Files clicked');
    setCurrentView('upload');
  };

  const handleMonitorProcess = () => {
    console.log('Monitor Process clicked');
    setCurrentView('process');
  };

  const handleMetricClick = (metric: string) => {
    console.log(`Clicked on metric: ${metric}`);
    setDrillDownMetric(metric);
    setCurrentView('drilldown');
  };

  const handleBackToDashboard = () => {
    setCurrentView('dashboard');
    setDrillDownMetric('');
  };

  const handleSettings = () => {
    console.log('Settings clicked');
  };

  const handleNotifications = () => {
    console.log('Notifications clicked');
  };

  const handleUserProfile = () => {
    console.log('User profile clicked');
  };

  const handleSurveillanceComplete = (results: any) => {
    console.log('Surveillance completed:', results);
    // Refresh dashboard data after surveillance completion
    fetchRealData();
    // Show success message or redirect to dashboard
    setCurrentView('dashboard');
  };

  const handleUploadComplete = (files: any[]) => {
    console.log('Files uploaded:', files);
    // Could show success message or redirect to surveillance
    // For now, just log the completion
  };

  const renderMainContent = () => {
    switch (currentView) {
      case 'dashboard':
        return (
          <MonthSummary
            month={currentMonthData.month}
            year={currentMonthData.year}
            totalTrades={currentMonthData.totalTrades}
            emailMatches={currentMonthData.emailMatches}
            omsMatches={currentMonthData.omsMatches}
            audioMatches={currentMonthData.audioMatches}
            unmatchedOrders={currentMonthData.unmatchedOrders}
            actualDiscrepancies={currentMonthData.actualDiscrepancies}
            reportingDiscrepancies={currentMonthData.reportingDiscrepancies}
            cancelledOrders={currentMonthData.cancelledOrders}
            rejectedOrders={currentMonthData.rejectedOrders}
            onMetricClick={handleMetricClick}
          />
        );
      case 'drilldown':
        return (
          <DrillDownView
            metricType={drillDownMetric}
            month={currentMonthData.month}
            year={currentMonthData.year}
            onBack={handleBackToDashboard}
            dateFilter={dateFilter}
          />
        );
      case 'process':
        return (
          <SurveillanceRunner
            onComplete={handleSurveillanceComplete}
            onCancel={handleBackToDashboard}
          />
        );
      case 'upload':
        return (
          <FileUpload
            onUploadComplete={handleUploadComplete}
            onCancel={handleBackToDashboard}
          />
        );
      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <Header
        onSettings={handleSettings}
        onNotifications={handleNotifications}
        onUserProfile={handleUserProfile}
      />
      <div className="flex h-[calc(100vh-4rem)]">
        <Sidebar
          selectedMonth={selectedMonth}
          onMonthSelect={handleMonthSelect}
          onRunSurveillance={handleRunSurveillance}
          onUploadFiles={handleUploadFiles}
          onMonitorProcess={handleMonitorProcess}
        />
        <main className="flex-1 overflow-auto p-6">
          <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
            <p className="text-sm text-blue-800">
              <strong>Current View:</strong> {currentView} | <strong>Selected Month:</strong> {selectedMonth}
            </p>
          </div>
          
          {/* Date Filter - Show on dashboard and drilldown views */}
          {(currentView === 'dashboard' || currentView === 'drilldown') && (
            <DateFilter
              month={selectedMonth}
              year={2025}
              onDateRangeChange={handleDateRangeChange}
              className="mb-6"
            />
          )}
          
          {renderMainContent()}
        </main>
      </div>
    </div>
  );
}

export default App;
