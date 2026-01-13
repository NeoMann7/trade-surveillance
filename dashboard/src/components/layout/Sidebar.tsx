import React from 'react';
import { Card } from '../ui/card';
import { Button } from '../ui/button';
import { Calendar, Play, Upload, Monitor } from 'lucide-react';

interface MonthData {
  month: string;
  year: number;
  totalTrades: number;
  emailMatches: number;
  audioMatches: number;
  unmatchedOrders: number;
  discrepancies: number;
  lastUpdated: Date;
  hasRecentRun: boolean;
  runStatus?: 'completed' | 'running' | 'failed' | 'pending';
}

interface SidebarProps {
  selectedMonth: string;
  onMonthSelect: (month: string) => void;
  onRunSurveillance: () => void;
  onUploadFiles: () => void;
  onMonitorProcess: () => void;
}

const mockMonths: MonthData[] = [
  {
    month: 'January',
    year: 2026,
    totalTrades: 0,
    emailMatches: 0,
    audioMatches: 0,
    unmatchedOrders: 0,
    discrepancies: 0,
    lastUpdated: new Date('2026-01-01'),
    hasRecentRun: false,
    runStatus: 'pending'
  },
  {
    month: 'December',
    year: 2025,
    totalTrades: 0,
    emailMatches: 0,
    audioMatches: 0,
    unmatchedOrders: 0,
    discrepancies: 0,
    lastUpdated: new Date('2025-12-01'),
    hasRecentRun: false,
    runStatus: 'pending'
  },
  {
    month: 'November',
    year: 2025,
    totalTrades: 0,
    emailMatches: 0,
    audioMatches: 0,
    unmatchedOrders: 0,
    discrepancies: 0,
    lastUpdated: new Date('2025-11-01'),
    hasRecentRun: false,
    runStatus: 'pending'
  },
  {
    month: 'October',
    year: 2025,
    totalTrades: 0,
    emailMatches: 0,
    audioMatches: 0,
    unmatchedOrders: 0,
    discrepancies: 0,
    lastUpdated: new Date('2025-10-01'),
    hasRecentRun: false,
    runStatus: 'pending'
  },
  {
    month: 'September',
    year: 2025,
    totalTrades: 324,
    emailMatches: 6,
    audioMatches: 5,
    unmatchedOrders: 313,
    discrepancies: 5,
    lastUpdated: new Date('2025-09-19'),
    hasRecentRun: true,
    runStatus: 'completed'
  },
  {
    month: 'August',
    year: 2025,
    totalTrades: 283,
    emailMatches: 31,
    audioMatches: 185,
    unmatchedOrders: 67,
    discrepancies: 81,
    lastUpdated: new Date('2025-08-29'),
    hasRecentRun: true,
    runStatus: 'completed'
  },
  {
    month: 'July',
    year: 2025,
    totalTrades: 0,
    emailMatches: 0,
    audioMatches: 0,
    unmatchedOrders: 0,
    discrepancies: 0,
    lastUpdated: new Date('2025-07-31'),
    hasRecentRun: false,
    runStatus: 'pending'
  },
  {
    month: 'June',
    year: 2025,
    totalTrades: 0,
    emailMatches: 0,
    audioMatches: 0,
    unmatchedOrders: 0,
    discrepancies: 0,
    lastUpdated: new Date('2025-06-30'),
    hasRecentRun: false,
    runStatus: 'pending'
  }
];

export const Sidebar: React.FC<SidebarProps> = ({
  selectedMonth,
  onMonthSelect,
  onRunSurveillance,
  onUploadFiles,
  onMonitorProcess
}) => {
  return (
    <div className="w-80 bg-card border-r border-border h-full flex flex-col">
      {/* Header */}
      <div className="p-6 border-b border-border">
        <h2 className="text-lg font-semibold text-foreground">Trade Surveillance</h2>
        <p className="text-sm text-muted-foreground">Compliance Dashboard</p>
      </div>

      {/* Actions Section */}
      <div className="p-4 border-b border-border">
        <h3 className="text-sm font-medium text-foreground mb-3 flex items-center gap-2">
          <Play className="h-4 w-4" />
          Actions
        </h3>
        <div className="space-y-2">
          <Button 
            onClick={onRunSurveillance}
            className="w-full justify-start"
            variant="default"
          >
            <Play className="h-4 w-4 mr-2" />
            Run New Surveillance
          </Button>
          <Button 
            onClick={onUploadFiles}
            className="w-full justify-start"
            variant="outline"
          >
            <Upload className="h-4 w-4 mr-2" />
            Upload Files
          </Button>
          <Button 
            onClick={onMonitorProcess}
            className="w-full justify-start"
            variant="outline"
          >
            <Monitor className="h-4 w-4 mr-2" />
            Monitor Process
          </Button>
        </div>
      </div>

      {/* Months Section */}
      <div className="flex-1 p-4">
        <h3 className="text-sm font-medium text-foreground mb-3 flex items-center gap-2">
          <Calendar className="h-4 w-4" />
          Months
        </h3>
        <div className="space-y-2">
          {mockMonths.map((month) => (
            <Card 
              key={month.month}
              className={`cursor-pointer transition-colors hover:bg-accent ${
                selectedMonth === month.month ? 'bg-accent border-primary' : ''
              }`}
              onClick={() => onMonthSelect(month.month)}
            >
              <div className="p-4">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="font-medium text-foreground">{month.month} {month.year}</h4>
                  <div className={`w-2 h-2 rounded-full ${
                    month.runStatus === 'completed' ? 'bg-green-500' :
                    month.runStatus === 'running' ? 'bg-yellow-500' :
                    month.runStatus === 'failed' ? 'bg-red-500' : 'bg-gray-400'
                  }`} />
                </div>
                <div className="grid grid-cols-2 gap-2 text-xs text-muted-foreground">
                  <div>Trades: {month.totalTrades}</div>
                  <div>Email: {month.emailMatches}</div>
                  <div>Audio: {month.audioMatches}</div>
                  <div>Unmatched: {month.unmatchedOrders}</div>
                </div>
                <div className="mt-2 text-xs text-muted-foreground">
                  Updated: {month.lastUpdated.toLocaleDateString()}
                </div>
              </div>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
};
