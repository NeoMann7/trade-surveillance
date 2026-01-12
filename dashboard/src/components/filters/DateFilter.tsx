import React, { useState, useEffect } from 'react';
import { Button } from '../ui/button';
import { Calendar, Filter, X } from 'lucide-react';
import { getApiUrl } from '../../config/api';

export interface DateOption {
  value: string;  // DDMMYYYY format
  label: string;  // DD/MM/YYYY format
  day: number;
  month: number;
  year: number;
}

export interface DateFilterProps {
  month: string;
  year: number;
  onDateRangeChange: (startDate: string | null, endDate: string | null) => void;
  className?: string;
}

export const DateFilter: React.FC<DateFilterProps> = ({
  month,
  year,
  onDateRangeChange,
  className = ''
}) => {
  const [availableDates, setAvailableDates] = useState<DateOption[]>([]);
  const [startDate, setStartDate] = useState<string | null>(null);
  const [endDate, setEndDate] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  // Load available dates for the month
  useEffect(() => {
    const loadAvailableDates = async () => {
      setIsLoading(true);
      try {
        const url = getApiUrl(`/api/surveillance/available-dates/${year}/${month}`);
        console.log(`📅 Loading available dates for ${month} ${year}: ${url}`);
        
        // Add cache-busting to prevent stale data
        const response = await fetch(url, {
          cache: 'no-cache',
          headers: {
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
          }
        });
        
        if (response.ok) {
          const dates = await response.json();
          console.log(`✅ Loaded ${dates.length} dates for ${month} ${year}`);
          console.log(`   First date: ${dates[0]?.label}, Last date: ${dates[dates.length - 1]?.label}`);
          setAvailableDates(dates);
        } else {
          console.error(`❌ Failed to load available dates: ${response.status} ${response.statusText}`);
        }
      } catch (error) {
        console.error('Error loading available dates:', error);
      } finally {
        setIsLoading(false);
      }
    };

    loadAvailableDates();
  }, [month, year]);

  // Reset filters when month changes
  useEffect(() => {
    setStartDate(null);
    setEndDate(null);
    onDateRangeChange(null, null);
  }, [month, year]);

  const handleApplyFilter = () => {
    onDateRangeChange(startDate, endDate);
  };

  const handleClearFilter = () => {
    setStartDate(null);
    setEndDate(null);
    onDateRangeChange(null, null);
  };

  const handleQuickFilter = (days: number) => {
    if (availableDates.length === 0) return;
    
    const sortedDates = [...availableDates].sort((a, b) => a.value.localeCompare(b.value));
    const lastDate = sortedDates[sortedDates.length - 1];
    const startIndex = Math.max(0, sortedDates.length - days);
    const firstDate = sortedDates[startIndex];
    
    setStartDate(firstDate.value);
    setEndDate(lastDate.value);
  };

  const isFilterActive = startDate !== null || endDate !== null;

  return (
    <div className={`bg-white border rounded-lg p-4 shadow-sm ${className}`}>
      <div className="flex items-center gap-4 flex-wrap">
        {/* Filter Icon and Title */}
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-gray-600" />
          <span className="text-sm font-medium text-gray-700">Date Filter:</span>
        </div>

        {/* Start Date Dropdown */}
        <div className="flex items-center gap-2">
          <label className="text-xs text-gray-600">From:</label>
          <select
            value={startDate || ''}
            onChange={(e) => setStartDate(e.target.value || null)}
            className="px-3 py-1 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={isLoading}
          >
            <option value="">All Dates</option>
            {availableDates.map((date) => (
              <option key={date.value} value={date.value}>
                {date.label}
              </option>
            ))}
          </select>
        </div>

        {/* End Date Dropdown */}
        <div className="flex items-center gap-2">
          <label className="text-xs text-gray-600">To:</label>
          <select
            value={endDate || ''}
            onChange={(e) => setEndDate(e.target.value || null)}
            className="px-3 py-1 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={isLoading}
          >
            <option value="">All Dates</option>
            {availableDates.map((date) => (
              <option key={date.value} value={date.value}>
                {date.label}
              </option>
            ))}
          </select>
        </div>

        {/* Quick Filter Buttons */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-600">Quick:</span>
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleQuickFilter(7)}
            disabled={isLoading}
            className="text-xs px-2 py-1 h-6"
          >
            Last 7 Days
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleQuickFilter(3)}
            disabled={isLoading}
            className="text-xs px-2 py-1 h-6"
          >
            Last 3 Days
          </Button>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2">
          <Button
            onClick={handleApplyFilter}
            disabled={isLoading || (!startDate && !endDate)}
            size="sm"
            className="text-xs px-3 py-1 h-6"
          >
            Apply
          </Button>
          {isFilterActive && (
            <Button
              onClick={handleClearFilter}
              variant="outline"
              size="sm"
              className="text-xs px-2 py-1 h-6"
            >
              <X className="h-3 w-3" />
            </Button>
          )}
        </div>

        {/* Filter Status */}
        {isFilterActive && (
          <div className="text-xs text-blue-600 bg-blue-50 px-2 py-1 rounded">
            {startDate && endDate 
              ? `Filtered: ${availableDates.find(d => d.value === startDate)?.label} - ${availableDates.find(d => d.value === endDate)?.label}`
              : startDate 
                ? `From: ${availableDates.find(d => d.value === startDate)?.label}`
                : `To: ${availableDates.find(d => d.value === endDate)?.label}`
            }
          </div>
        )}
      </div>
    </div>
  );
};
