import React from 'react';
import { MetricCard } from './MetricCard';
import { ChartLine, Mail, Mic, AlertTriangle, FileX } from 'lucide-react';
import { MailOpen } from 'lucide-react';

interface MonthSummaryProps {
  month: string;
  year: number;
  totalTrades: number;
  emailMatches: number;
  // OMS matches are displayed as a separate metric
  omsMatches?: number;
  audioMatches: number;
  unmatchedOrders: number;
  actualDiscrepancies: number;
  reportingDiscrepancies: number;
  cancelledOrders?: number;
  rejectedOrders?: number;
  onMetricClick: (metric: string) => void;
}

export const MonthSummary: React.FC<MonthSummaryProps> = ({
  month,
  year,
  totalTrades,
  emailMatches,
  omsMatches = 0,
  audioMatches,
  unmatchedOrders,
  actualDiscrepancies,
  reportingDiscrepancies,
  cancelledOrders = 0,
  rejectedOrders = 0,
  onMetricClick
}) => {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold text-foreground">{month} {year}</h2>
          <p className="text-muted-foreground">Trade surveillance overview</p>
        </div>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        <MetricCard
          title="Complete Orders"
          value={totalTrades}
          change={12.5}
          changeType="increase"
          icon={<ChartLine className="h-5 w-5" />}
          description="Completed orders requiring surveillance"
          onClick={() => onMetricClick('totalTrades')}
        />
        
        <MetricCard
          title="Email Matches"
          value={emailMatches}
          change={8.3}
          changeType="increase"
          icon={<Mail className="h-5 w-5" />}
          description="Complete orders with email evidence"
          onClick={() => onMetricClick('emailMatches')}
        />
        
        <MetricCard
          title="OMS Matches"
          value={omsMatches}
          change={4.7}
          changeType="increase"
          icon={<MailOpen className="h-5 w-5" />}
          description="Complete orders matched via OMS alerts"
          onClick={() => onMetricClick('omsMatches')}
        />

        <MetricCard
          title="Audio Matches"
          value={audioMatches}
          change={15.2}
          changeType="increase"
          icon={<Mic className="h-5 w-5" />}
          description="Complete orders with audio evidence"
          onClick={() => onMetricClick('audioMatches')}
        />
        
        <MetricCard
          title="Unmatched Orders"
          value={unmatchedOrders}
          change={-5.1}
          changeType="decrease"
          icon={<FileX className="h-5 w-5" />}
          description="Complete orders without evidence"
          onClick={() => onMetricClick('unmatchedOrders')}
          isCritical={true}
        />
        
        <MetricCard
          title="Actual Discrepancies"
          value={actualDiscrepancies}
          change={2.3}
          changeType="increase"
          icon={<AlertTriangle className="h-5 w-5" />}
          description="Complete orders with compliance issues"
          onClick={() => onMetricClick('discrepancies')}
          isCritical={true}
        />
        
        <MetricCard
          title="Reporting Discrepancies"
          value={reportingDiscrepancies}
          change={1.2}
          changeType="increase"
          icon={<AlertTriangle className="h-5 w-5" />}
          description="Dealer training issues"
          onClick={() => onMetricClick('reportingDiscrepancies')}
          isCritical={false}
        />
        
      </div>

      {/* Additional Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-card p-6 rounded-lg border">
          <h3 className="text-lg font-semibold text-foreground mb-2">Coverage Analysis</h3>
          <div className="space-y-2">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Email Coverage:</span>
              <span className="font-medium">{Math.round((emailMatches / totalTrades) * 100)}%</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Audio Coverage:</span>
              <span className="font-medium">{Math.round((audioMatches / totalTrades) * 100)}%</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">OMS Coverage:</span>
              <span className="font-medium">{Math.round((omsMatches / totalTrades) * 100)}%</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Total Coverage:</span>
              <span className="font-medium">{Math.round(((emailMatches + audioMatches + omsMatches) / totalTrades) * 100)}%</span>
            </div>
          </div>
        </div>

        <div className="bg-card p-6 rounded-lg border">
          <h3 className="text-lg font-semibold text-foreground mb-2">Risk Assessment</h3>
          <div className="space-y-2">
            <div className="flex justify-between">
              <span className="text-muted-foreground">High Risk:</span>
              <span className="font-medium text-red-600">{actualDiscrepancies}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Medium Risk:</span>
              <span className="font-medium text-yellow-600">{unmatchedOrders}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Training Issues:</span>
              <span className="font-medium text-orange-600">{reportingDiscrepancies}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Low Risk:</span>
              <span className="font-medium text-green-600">{totalTrades - unmatchedOrders - actualDiscrepancies - reportingDiscrepancies}</span>
            </div>
          </div>
        </div>

        <div className="bg-card p-6 rounded-lg border">
          <h3 className="text-lg font-semibold text-foreground mb-2">Quick Actions</h3>
          <div className="space-y-2">
            <button className="w-full text-left p-2 rounded hover:bg-accent text-sm">
              View All Orders
            </button>
            <button className="w-full text-left p-2 rounded hover:bg-accent text-sm">
              Export Report
            </button>
            <button className="w-full text-left p-2 rounded hover:bg-accent text-sm">
              Run New Surveillance
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
