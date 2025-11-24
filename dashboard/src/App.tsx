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

  // Fetch real data from backend
  const fetchRealData = useCallback(async () => {
    try {
        // Fetch August data
        const [augustTotalTrades, augustEmailMatches, augustOmsMatches, augustAudioMatches, augustActualDiscrepancies, augustReportingDiscrepancies] = await Promise.all([
          surveillanceDataService.getOrdersForMetric('totalTrades', 'August', 2025),
          surveillanceDataService.getOrdersForMetric('emailMatches', 'August', 2025),
          surveillanceDataService.getOrdersForMetric('omsMatches', 'August', 2025),
          surveillanceDataService.getOrdersForMetric('audioMatches', 'August', 2025),
          surveillanceDataService.getOrdersForMetric('discrepancies', 'August', 2025),
          surveillanceDataService.getOrdersForMetric('reportingDiscrepancies', 'August', 2025)
        ]);

        // Fetch September data
        const [septemberTotalTrades, septemberEmailMatches, septemberOmsMatches, septemberAudioMatches, septemberActualDiscrepancies, septemberReportingDiscrepancies, septemberUnmatchedOrders] = await Promise.all([
          surveillanceDataService.getOrdersForMetric('totalTrades', 'September', 2025),
          surveillanceDataService.getOrdersForMetric('emailMatches', 'September', 2025),
          surveillanceDataService.getOrdersForMetric('omsMatches', 'September', 2025),
          surveillanceDataService.getOrdersForMetric('audioMatches', 'September', 2025),
          surveillanceDataService.getOrdersForMetric('discrepancies', 'September', 2025),
          surveillanceDataService.getOrdersForMetric('reportingDiscrepancies', 'September', 2025),
          surveillanceDataService.getOrdersForMetric('unmatchedOrders', 'September', 2025)
        ]);

        // Fetch October data
        const [octoberTotalTrades, octoberEmailMatches, octoberOmsMatches, octoberAudioMatches, octoberActualDiscrepancies, octoberReportingDiscrepancies, octoberUnmatchedOrders] = await Promise.all([
          surveillanceDataService.getOrdersForMetric('totalTrades', 'October', 2025),
          surveillanceDataService.getOrdersForMetric('emailMatches', 'October', 2025),
          surveillanceDataService.getOrdersForMetric('omsMatches', 'October', 2025),
          surveillanceDataService.getOrdersForMetric('audioMatches', 'October', 2025),
          surveillanceDataService.getOrdersForMetric('discrepancies', 'October', 2025),
          surveillanceDataService.getOrdersForMetric('reportingDiscrepancies', 'October', 2025),
          surveillanceDataService.getOrdersForMetric('unmatchedOrders', 'October', 2025)
        ]);

        setRealData(prev => ({
          ...prev,
          August: {
            ...prev.August,
            totalTrades: augustTotalTrades.length,
            emailMatches: augustEmailMatches.length,
            omsMatches: augustOmsMatches.length,
            audioMatches: augustAudioMatches.length,
            actualDiscrepancies: augustActualDiscrepancies.length,
            reportingDiscrepancies: augustReportingDiscrepancies.length,
            unmatchedOrders: augustTotalTrades.length - augustEmailMatches.length - augustAudioMatches.length - augustOmsMatches.length
          },
          September: {
            ...prev.September,
            totalTrades: septemberTotalTrades.length,
            emailMatches: septemberEmailMatches.length,
            omsMatches: septemberOmsMatches.length,
            audioMatches: septemberAudioMatches.length,
            actualDiscrepancies: septemberActualDiscrepancies.length,
            reportingDiscrepancies: septemberReportingDiscrepancies.length,
            unmatchedOrders: septemberUnmatchedOrders.length
          },
          October: {
            ...prev.October,
            totalTrades: octoberTotalTrades.length,
            emailMatches: octoberEmailMatches.length,
            omsMatches: octoberOmsMatches.length,
            audioMatches: octoberAudioMatches.length,
            actualDiscrepancies: octoberActualDiscrepancies.length,
            reportingDiscrepancies: octoberReportingDiscrepancies.length,
            unmatchedOrders: octoberUnmatchedOrders.length
          }
        }));
      } catch (error) {
        console.error('Error fetching real data:', error);
      }
    }, []);

  useEffect(() => {
    fetchRealData();
  }, [fetchRealData]);

  // Fetch filtered data when date filter changes
  useEffect(() => {
    const fetchFilteredData = async () => {
      if (!dateFilter.startDate && !dateFilter.endDate) {
        return; // No filter applied, use existing data
      }

      try {
        const currentYear = 2025;
        const [filteredTotalTrades, filteredEmailMatches, filteredOmsMatches, filteredAudioMatches, filteredActualDiscrepancies, filteredReportingDiscrepancies, filteredUnmatchedOrders] = await Promise.all([
          surveillanceDataService.getOrdersForMetric('totalTrades', selectedMonth, currentYear, dateFilter.startDate || undefined, dateFilter.endDate || undefined),
          surveillanceDataService.getOrdersForMetric('emailMatches', selectedMonth, currentYear, dateFilter.startDate || undefined, dateFilter.endDate || undefined),
          surveillanceDataService.getOrdersForMetric('omsMatches', selectedMonth, currentYear, dateFilter.startDate || undefined, dateFilter.endDate || undefined),
          surveillanceDataService.getOrdersForMetric('audioMatches', selectedMonth, currentYear, dateFilter.startDate || undefined, dateFilter.endDate || undefined),
          surveillanceDataService.getOrdersForMetric('discrepancies', selectedMonth, currentYear, dateFilter.startDate || undefined, dateFilter.endDate || undefined),
          surveillanceDataService.getOrdersForMetric('reportingDiscrepancies', selectedMonth, currentYear, dateFilter.startDate || undefined, dateFilter.endDate || undefined),
          surveillanceDataService.getOrdersForMetric('unmatchedOrders', selectedMonth, currentYear, dateFilter.startDate || undefined, dateFilter.endDate || undefined)
        ]);

        setRealData(prev => ({
          ...prev,
          [selectedMonth]: {
            ...prev[selectedMonth as keyof typeof prev],
            totalTrades: filteredTotalTrades.length,
            emailMatches: filteredEmailMatches.length,
            omsMatches: filteredOmsMatches.length,
            audioMatches: filteredAudioMatches.length,
            actualDiscrepancies: filteredActualDiscrepancies.length,
            reportingDiscrepancies: filteredReportingDiscrepancies.length,
            unmatchedOrders: filteredUnmatchedOrders.length
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
