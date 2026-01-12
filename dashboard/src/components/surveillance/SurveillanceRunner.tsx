import React, { useState, useEffect } from 'react';
import { API_CONFIG } from '../../config/api';
import { Card } from '../ui/card';
import { Button } from '../ui/button';
import { Progress } from '../ui/progress';
import { Badge } from '../ui/badge';
import { Alert, AlertDescription } from '../ui/alert';
import { Calendar, Play, CheckCircle, XCircle, Clock, RefreshCw } from 'lucide-react';

interface SurveillanceStep {
  id: number;
  name: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  startTime?: string;
  endTime?: string;
  duration?: number;
  error?: string;
  logs?: string[];
}

interface JobSummary {
  total_steps: number;
  completed_steps: number;
  failed_steps: number;
}

interface SurveillanceJob {
  id: string;
  date: string;
  status: 'running' | 'completed' | 'failed';
  completed_at?: string;
  duration?: number;
  summary?: JobSummary;
  excel_file_available?: boolean;
}

interface EmailProgress {
  total_emails: number;
  processed_emails: number;
  successful_emails: number;
  remaining_emails: number;
  progress_percent: number;
  timestamp: string;
}

interface SurveillanceResults {
  jobId: string;
  status: 'running' | 'completed' | 'failed';
  steps: SurveillanceStep[];
  summary: {
    totalSteps: number;
    completedSteps: number;
    failedSteps: number;
    totalDuration: number;
  };
  email_progress?: EmailProgress;
  metrics?: {
    totalTrades: number;
    emailMatches: number;
    omsMatches: number;
    audioMatches: number;
    unmatchedOrders: number;
    actualDiscrepancies: number;
    reportingDiscrepancies: number;
  };
}

interface SurveillanceRunnerProps {
  onComplete: (results: SurveillanceResults) => void;
  onCancel: () => void;
}

export const SurveillanceRunner: React.FC<SurveillanceRunnerProps> = ({
  onComplete,
  onCancel
}) => {
  const [selectedDate, setSelectedDate] = useState<string>(new Date().toISOString().split('T')[0]);
  const [isRunning, setIsRunning] = useState(false);
  const [currentJob, setCurrentJob] = useState<string | null>(null);
  const [steps, setSteps] = useState<SurveillanceStep[]>([]);
  const [logs, setLogs] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [currentStep, setCurrentStep] = useState<string>('');
  const [expandedStep, setExpandedStep] = useState<number | null>(null);
  const [jobHistory, setJobHistory] = useState<SurveillanceJob[]>([]);
  const [showCompletion, setShowCompletion] = useState(false);
  const [completionData, setCompletionData] = useState<any>(null);
  const [emailProgress, setEmailProgress] = useState<EmailProgress | null>(null);

  // Load job history on component mount
  useEffect(() => {
    loadJobHistory();
  }, []);

  const loadJobHistory = async () => {
    try {
      const apiUrl = API_CONFIG.baseUrl;
      const response = await fetch(`${apiUrl}/api/surveillance/jobs/history`);
      if (response.ok) {
        const data = await response.json();
        setJobHistory(data.jobs || []);
      }
    } catch (err) {
      console.error('Error loading job history:', err);
    }
  };

  const downloadReport = async (jobId: string) => {
    try {
      const apiUrl = API_CONFIG.baseUrl;
      const response = await fetch(`${apiUrl}/api/surveillance/download/${jobId}`);
      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `Trade_Surveillance_Report_${selectedDate.replace(/-/g, '')}.xlsx`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      } else {
        const error = await response.json();
        alert(`Download failed: ${error.error}`);
      }
    } catch (err) {
      console.error('Error downloading report:', err);
      alert('Download failed. Please try again.');
    }
  };

  const startSurveillance = async () => {
    try {
      setIsRunning(true);
      setError(null);
      setLogs([]);
      setSteps([]);

      const apiUrl = API_CONFIG.baseUrl;
      const response = await fetch(`${apiUrl}/api/surveillance/run`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          date: selectedDate  // This is already in YYYY-MM-DD format, backend will convert it
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to start surveillance');
      }

      const result = await response.json();
      setCurrentJob(result.jobId);
      
      // Start polling for updates
      pollJobStatus(result.jobId);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      setIsRunning(false);
    }
  };

  const pollJobStatus = async (jobId: string) => {
    const poll = async () => {
      try {
        const apiUrl = API_CONFIG.baseUrl;
        const response = await fetch(`${apiUrl}/api/surveillance/job/${jobId}`);
        if (!response.ok) return;

        const status = await response.json();
        
        // DEBUG: Log entire status to see what we're receiving
        console.log('🔍 Full job status:', status);
        console.log('🔍 Has email_progress?', 'email_progress' in status);
        console.log('🔍 email_progress value:', status.email_progress);
        
        if (status.steps) {
          setSteps(status.steps);
        }
        
        if (status.current_step) {
          setCurrentStep(status.current_step);
        }
        
        if (status.logs) {
          setLogs(status.logs);
        }
        
        // Update email progress if available
        if (status.email_progress) {
          console.log('✅ Setting email progress:', status.email_progress);
          setEmailProgress(status.email_progress);
        } else {
          console.log('⚠️ No email_progress in status');
          // Clear progress if email step is not running
          const emailStep = status.steps?.find((s: SurveillanceStep) => s.id === 2);
          if (emailStep && emailStep.status !== 'running') {
            setEmailProgress(null);
          }
        }

        if (status.status === 'completed' || status.status === 'failed') {
          setIsRunning(false);
          setShowCompletion(true);
          setCompletionData(status);
          
          // Reload job history to include the completed job
          loadJobHistory();
          
          if (status.status === 'completed' && onComplete) {
            onComplete(status);
          }
          return;
        }

        // Continue polling
        setTimeout(poll, 2000);
      } catch (err) {
        console.error('Error polling job status:', err);
        setIsRunning(false);
      }
    };

    poll();
  };

  const getStatusIcon = (status: SurveillanceStep['status']) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'failed':
        return <XCircle className="h-4 w-4 text-red-500" />;
      case 'running':
        return <Clock className="h-4 w-4 text-blue-500 animate-spin" />;
      default:
        return <Clock className="h-4 w-4 text-gray-400" />;
    }
  };

  const getStatusBadge = (status: SurveillanceStep['status']) => {
    const variants = {
      completed: 'bg-green-100 text-green-800',
      failed: 'bg-red-100 text-red-800',
      running: 'bg-blue-100 text-blue-800',
      pending: 'bg-gray-100 text-gray-800'
    };

    return (
      <Badge className={variants[status]}>
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </Badge>
    );
  };

  return (
    <div className="space-y-6">
      <Card className="p-6">
        <h2 className="text-2xl font-bold mb-4">Run Trade Surveillance</h2>
        
        <div className="space-y-4">
          <div>
            <label htmlFor="date-picker" className="block text-sm font-medium mb-2">
              Select Date
            </label>
            <div className="flex items-center gap-4">
              <Calendar className="h-5 w-5 text-gray-400" />
              <input
                id="date-picker"
                type="date"
                value={selectedDate}
                onChange={(e) => setSelectedDate(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                disabled={isRunning}
              />
            </div>
          </div>

          <div className="flex gap-4">
            <Button
              onClick={startSurveillance}
              disabled={isRunning}
              className="flex items-center gap-2"
            >
              <Play className="h-4 w-4" />
              {isRunning ? 'Running...' : 'Start Surveillance'}
            </Button>
            
            {isRunning && (
              <Button
                variant="outline"
                onClick={onCancel}
                className="flex items-center gap-2"
              >
                <XCircle className="h-4 w-4" />
                Cancel
              </Button>
            )}
          </div>
        </div>
      </Card>

      {error && (
        <Alert className="border-red-200 bg-red-50">
          <XCircle className="h-4 w-4 text-red-600" />
          <AlertDescription className="text-red-800">
            {error}
          </AlertDescription>
        </Alert>
      )}

      {steps.length > 0 && (
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4">Surveillance Progress</h3>
          <div className="space-y-3">
            {steps.map((step) => (
              <div key={step.id} className="border rounded-lg">
                <div 
                  className="flex items-center justify-between p-3 cursor-pointer hover:bg-gray-50"
                  onClick={() => setExpandedStep(expandedStep === step.id ? null : step.id)}
                >
                  <div className="flex items-center gap-3">
                    {getStatusIcon(step.status)}
                    <div>
                      <span className="font-medium">{step.name}</span>
                      {step.duration && (
                        <span className="text-sm text-gray-500 ml-2">
                          ({step.duration.toFixed(1)}s)
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {getStatusBadge(step.status)}
                    <span className="text-gray-400">
                      {expandedStep === step.id ? '▼' : '▶'}
                    </span>
                  </div>
                </div>
                
                {expandedStep === step.id && (
                  <div className="px-3 pb-3 border-t bg-gray-50">
                    {step.error && (
                      <div className="mt-2 p-2 bg-red-100 border border-red-200 rounded text-red-800 text-sm">
                        <strong>Error:</strong> {step.error}
                      </div>
                    )}
                    {step.logs && step.logs.length > 0 && (
                      <div className="mt-2">
                        <h4 className="text-sm font-medium text-gray-700 mb-1">Step Logs:</h4>
                        <div className="bg-white border rounded p-2 max-h-32 overflow-y-auto">
                          {step.logs.map((log, index) => (
                            <div key={index} className="text-xs text-gray-600 font-mono">
                              {log}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </Card>
      )}

      {isRunning && (
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4">Progress</h3>
          <div className="space-y-4">
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span>Overall Progress</span>
                <span>{steps.filter(s => s.status === 'completed').length} / {steps.length}</span>
              </div>
              <Progress 
                value={(steps.filter(s => s.status === 'completed').length / Math.max(steps.length, 1)) * 100} 
                className="h-2"
              />
            </div>
            
            {currentStep && (
              <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
                <div className="flex items-center gap-2">
                  <Clock className="h-4 w-4 text-blue-600 animate-spin" />
                  <span className="text-sm font-medium text-blue-800">Current Step:</span>
                </div>
                <p className="text-sm text-blue-700 mt-1">{currentStep}</p>
              </div>
            )}
            
            {/* DEBUG: Always show emailProgress state */}
            <div className="p-2 bg-gray-100 border border-gray-300 rounded text-xs">
              <strong>DEBUG:</strong> emailProgress = {emailProgress ? JSON.stringify(emailProgress) : 'null'}
            </div>
            
            {emailProgress ? (
              <div className="p-3 bg-green-50 border border-green-200 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-green-800">📧 Email Processing:</span>
                  </div>
                  <span className="text-sm font-bold text-green-700">
                    {emailProgress.processed_emails} / {emailProgress.total_emails}
                  </span>
                </div>
                <div className="space-y-1">
                  <div className="flex justify-between text-xs text-green-700">
                    <span>Processed: {emailProgress.processed_emails}</span>
                    <span>Remaining: {emailProgress.remaining_emails}</span>
                  </div>
                  <Progress 
                    value={emailProgress.progress_percent} 
                    className="h-2"
                  />
                  <div className="text-xs text-green-600 text-center">
                    {emailProgress.progress_percent}% Complete
                  </div>
                </div>
              </div>
            ) : (
              <div className="p-2 bg-yellow-50 border border-yellow-200 rounded text-xs text-yellow-800">
                ⚠️ Email progress not available yet
              </div>
            )}
            
            {logs.length > 0 && (
              <div className="space-y-2">
                <h4 className="text-sm font-medium text-gray-700">Recent Logs:</h4>
                <div className="bg-gray-50 border rounded p-3 max-h-40 overflow-y-auto">
                  {logs.slice(-10).map((log, index) => (
                    <div key={index} className="text-xs text-gray-600 font-mono mb-1">
                      {log}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </Card>
      )}

      {showCompletion && completionData && (
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4">Surveillance Completed</h3>
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              {completionData.status === 'completed' ? (
                <CheckCircle className="h-6 w-6 text-green-500" />
              ) : (
                <XCircle className="h-6 w-6 text-red-500" />
              )}
              <div>
                <h4 className="font-medium">
                  {completionData.status === 'completed' ? 'Surveillance Completed Successfully' : 'Surveillance Failed'}
                </h4>
                <p className="text-sm text-gray-600">
                  Date: {selectedDate} | Duration: {completionData.summary ? 
                    `${Math.round((completionData.summary.completed_steps / completionData.summary.total_steps) * 100)}% complete` : 
                    'Unknown'
                  }
                </p>
              </div>
            </div>
            
            {completionData.status === 'completed' && completionData.excel_file_path && (
              <div className="flex gap-3">
                <Button
                  onClick={() => downloadReport(currentJob!)}
                  className="flex items-center gap-2"
                >
                  <CheckCircle className="h-4 w-4" />
                  Download Report
                </Button>
                <Button
                  variant="outline"
                  onClick={() => {
                    setShowCompletion(false);
                    setCompletionData(null);
                    setSteps([]);
                    setLogs([]);
                    setCurrentStep('');
                  }}
                >
                  Run Again
                </Button>
              </div>
            )}
            
            {completionData.status === 'failed' && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                <p className="text-sm text-red-800">
                  <strong>Error:</strong> {completionData.error || 'Surveillance failed'}
                </p>
              </div>
            )}
          </div>
        </Card>
      )}

      {jobHistory.length > 0 && (
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4">Recent Surveillance Jobs</h3>
          <div className="space-y-3">
            {jobHistory.map((job) => (
              <div key={job.id} className="flex items-center justify-between p-3 border rounded-lg">
                <div className="flex items-center gap-3">
                  {job.status === 'completed' ? (
                    <CheckCircle className="h-4 w-4 text-green-500" />
                  ) : (
                    <XCircle className="h-4 w-4 text-red-500" />
                  )}
                  <div>
                    <span className="font-medium">{job.date}</span>
                    <p className="text-sm text-gray-600">
                      {job.completed_at ? new Date(job.completed_at).toLocaleString() : 'In progress'}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Badge className={job.status === 'completed' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}>
                    {job.status.charAt(0).toUpperCase() + job.status.slice(1)}
                  </Badge>
                  {job.status === 'completed' && job.excel_file_available && (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => downloadReport(job.id)}
                    >
                      Download
                    </Button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
};
