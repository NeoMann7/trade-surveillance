import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { 
  AlertTriangle, 
  FileText, 
  Clock, 
  User, 
  Building,
  TrendingUp,
  X,
  Download,
  Flag,
  CheckCircle
} from 'lucide-react';
import { RealDiscrepancy } from '../../services/surveillanceDataService';

interface DiscrepancyDetailsProps {
  discrepancy: RealDiscrepancy;
  onClose: () => void;
  onAssign: (discrepancyId: string, assignee: string) => void;
  onResolve: (discrepancyId: string, resolution: string) => void;
  onDismiss: (discrepancyId: string, reason: string) => void;
}

export const DiscrepancyDetails: React.FC<DiscrepancyDetailsProps> = ({
  discrepancy,
  onClose,
  onAssign,
  onResolve,
  onDismiss
}) => {
  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'CRITICAL': return 'text-red-600 bg-red-50 border-red-200';
      case 'HIGH': return 'text-orange-600 bg-orange-50 border-orange-200';
      case 'MEDIUM': return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      case 'LOW': return 'text-blue-600 bg-blue-50 border-blue-200';
      default: return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'OPEN': return 'text-red-600 bg-red-50';
      case 'INVESTIGATING': return 'text-yellow-600 bg-yellow-50';
      case 'RESOLVED': return 'text-green-600 bg-green-50';
      case 'DISMISSED': return 'text-gray-600 bg-gray-50';
      default: return 'text-gray-600 bg-gray-50';
    }
  };

  const getActionColor = (action: string) => {
    switch (action) {
      case 'REVERSE': return 'text-red-600';
      case 'INVESTIGATE': return 'text-orange-600';
      case 'REVIEW': return 'text-yellow-600';
      case 'NONE': return 'text-green-600';
      default: return 'text-gray-600';
    }
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'PRICE_MISMATCH': return <TrendingUp className="h-4 w-4" />;
      case 'QUANTITY_MISMATCH': return <Building className="h-4 w-4" />;
      case 'SYMBOL_MISMATCH': return <FileText className="h-4 w-4" />;
      case 'TIMING_ISSUE': return <Clock className="h-4 w-4" />;
      case 'AUDIO_ISSUE': return <AlertTriangle className="h-4 w-4" />;
      case 'EMAIL_ISSUE': return <FileText className="h-4 w-4" />;
      default: return <AlertTriangle className="h-4 w-4" />;
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <Card className="w-full max-w-5xl max-h-[90vh] overflow-hidden">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-red-600" />
            Discrepancy Details - Order {discrepancy.orderId}
          </CardTitle>
          <Button variant="ghost" size="sm" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </CardHeader>
        
        <CardContent className="space-y-6 overflow-y-auto max-h-[calc(90vh-120px)]">
          {/* Header Information */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card className={`border-2 ${getSeverityColor(discrepancy.severity)}`}>
              <CardContent className="p-4">
                <div className="flex items-center gap-2">
                  {getTypeIcon(discrepancy.type)}
                  <div>
                    <div className="font-medium">{discrepancy.type.replace('_', ' ')}</div>
                    <div className="text-sm opacity-75">Severity: {discrepancy.severity}</div>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-4">
                <div className="flex items-center gap-2">
                  <Flag className="h-4 w-4" />
                  <div>
                    <div className="font-medium">Status</div>
                    <div className={`text-sm px-2 py-1 rounded-full inline-block ${getStatusColor(discrepancy.status)}`}>
                      {discrepancy.status}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-4">
                <div className="flex items-center gap-2">
                  <CheckCircle className="h-4 w-4" />
                  <div>
                    <div className="font-medium">Recommended Action</div>
                    <div className={`text-sm font-medium ${getActionColor(discrepancy.recommendedAction)}`}>
                      {discrepancy.recommendedAction}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Description and AI Observation */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Discrepancy Description</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm">{discrepancy.description}</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-sm">AI Observation</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="bg-blue-50 p-3 rounded-lg">
                  <p className="text-sm">{discrepancy.aiObservation}</p>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Evidence */}
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Evidence</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {discrepancy.evidence.audio && (
                <div className="border rounded-lg p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <AlertTriangle className="h-4 w-4 text-blue-600" />
                    <span className="font-medium">Audio Evidence</span>
                  </div>
                  <div className="text-sm space-y-1">
                    <div><strong>File:</strong> {discrepancy.evidence.audio.filename}</div>
                    <div><strong>Call Start:</strong> {discrepancy.evidence.audio.callStart}</div>
                    <div><strong>Call End:</strong> {discrepancy.evidence.audio.callEnd}</div>
                    <div className="bg-gray-50 p-2 rounded text-xs">
                      {discrepancy.evidence.audio.transcript}
                    </div>
                  </div>
                </div>
              )}

              {discrepancy.evidence.email && (
                <div className="border rounded-lg p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <FileText className="h-4 w-4 text-green-600" />
                    <span className="font-medium">Email Evidence</span>
                  </div>
                  <div className="text-sm space-y-1">
                    <div><strong>Subject:</strong> {discrepancy.evidence.email.subject}</div>
                    <div><strong>Date:</strong> {discrepancy.evidence.email.date}</div>
                    <div className="bg-gray-50 p-2 rounded text-xs">
                      {discrepancy.evidence.email.content}
                    </div>
                  </div>
                </div>
              )}

              {discrepancy.evidence.order && (
                <div className="border rounded-lg p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <Building className="h-4 w-4 text-purple-600" />
                    <span className="font-medium">Order Details</span>
                  </div>
                  <div className="text-sm space-y-1">
                    <div><strong>Timestamp:</strong> {discrepancy.evidence.order.timestamp}</div>
                    <div className="bg-gray-50 p-2 rounded text-xs">
                      {discrepancy.evidence.order.details}
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Resolution Section */}
          {discrepancy.status === 'RESOLVED' && discrepancy.resolution && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm flex items-center gap-2">
                  <CheckCircle className="h-4 w-4 text-green-600" />
                  Resolution
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="bg-green-50 p-3 rounded-lg">
                  <p className="text-sm">{discrepancy.resolution}</p>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Assignment Information */}
          {discrepancy.assignedTo && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm flex items-center gap-2">
                  <User className="h-4 w-4" />
                  Assignment
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-sm">
                  <strong>Assigned to:</strong> {discrepancy.assignedTo}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Timestamps */}
          <Card>
            <CardHeader>
              <CardTitle className="text-sm flex items-center gap-2">
                <Clock className="h-4 w-4" />
                Timeline
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-sm space-y-1">
                <div><strong>Created:</strong> {discrepancy.createdAt}</div>
                <div><strong>Last Updated:</strong> {discrepancy.updatedAt}</div>
              </div>
            </CardContent>
          </Card>

          {/* Action Buttons */}
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={onClose}>
              Close
            </Button>
            <Button variant="outline">
              <Download className="h-4 w-4 mr-2" />
              Export Report
            </Button>
            {discrepancy.status === 'OPEN' && (
              <>
                <Button 
                  variant="outline" 
                  onClick={() => onAssign(discrepancy.id, 'Current User')}
                >
                  Assign to Me
                </Button>
                <Button 
                  variant="outline" 
                  onClick={() => onDismiss(discrepancy.id, 'False positive')}
                >
                  Dismiss
                </Button>
                <Button 
                  onClick={() => onResolve(discrepancy.id, 'Resolved after investigation')}
                >
                  Mark Resolved
                </Button>
              </>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};
