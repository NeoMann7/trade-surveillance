import React, { useState, useEffect } from 'react';
import { OrderTable } from './OrderTable';
import { EvidenceViewer } from './EvidenceViewer';
import { DiscrepancyDetails } from './DiscrepancyDetails';
import { Button } from '../ui/button';
import { ArrowLeft, Download } from 'lucide-react';
import { surveillanceDataService, RealOrder, RealAudioEvidence, RealEmailEvidence, RealDiscrepancy } from '../../services/surveillanceDataService';

// Use the RealOrder interface from the service
type Order = RealOrder;

interface DrillDownViewProps {
  metricType: string;
  month: string;
  year: number;
  onBack: () => void;
  dateFilter?: {
    startDate: string | null;
    endDate: string | null;
  };
}

export const DrillDownView: React.FC<DrillDownViewProps> = ({
  metricType,
  month,
  year,
  onBack,
  dateFilter
}) => {
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedEvidence, setSelectedEvidence] = useState<{
    orderId: string;
    type: 'audio' | 'email';
    evidence: RealAudioEvidence | RealEmailEvidence;
  } | null>(null);
  const [selectedDiscrepancy, setSelectedDiscrepancy] = useState<RealDiscrepancy | null>(null);

  // Load real surveillance data
  useEffect(() => {
    const loadRealData = async () => {
      setLoading(true);
      try {
        const realOrders = await surveillanceDataService.getOrdersForMetric(
          metricType, 
          month, 
          year, 
          dateFilter?.startDate || undefined, 
          dateFilter?.endDate || undefined
        );
        setOrders(realOrders);
      } catch (error) {
        console.error('Error loading real data:', error);
        // Fallback to mock data if real data fails
        const mockOrders = await surveillanceDataService.getOrdersForMetric(metricType, month, year);
        setOrders(mockOrders);
      } finally {
        setLoading(false);
      }
    };

    loadRealData();
  }, [metricType, month, year, dateFilter?.startDate, dateFilter?.endDate]);

  // Removed unused functions - data now comes from real API

  const getTitleForMetric = (metric: string): string => {
    switch (metric) {
      case 'totalTrades': return 'All Completed Orders';
      case 'emailMatches': return 'Orders with Email Evidence';
      case 'audioMatches': return 'Orders with Audio Evidence';
      case 'unmatchedOrders': return 'Orders without Evidence';
      case 'discrepancies': return 'Orders with Compliance Issues';
      case 'cancelledOrders': return 'Cancelled Orders';
      case 'rejectedOrders': return 'Rejected Orders';
      default: return 'Order Details';
    }
  };

  const handleViewEvidence = async (orderId: string, type: 'audio' | 'email') => {
    const order = orders.find(o => o.id === orderId);
    if (!order) return;

    try {
      if (type === 'audio') {
        // Extract the actual order ID (remove "order-" prefix)
        const actualOrderId = orderId.replace('order-', '');
        
        // Convert date to the format expected by backend (DDMMYYYY)
        const dateObj = new Date(order.orderDate);
        const day = String(dateObj.getDate()).padStart(2, '0');
        const month = String(dateObj.getMonth() + 1).padStart(2, '0');
        const year = dateObj.getFullYear();
        const backendDate = `${day}${month}${year}`;
        
        const audioEvidence = await surveillanceDataService.getAudioEvidence(actualOrderId, backendDate);
        if (audioEvidence) {
          setSelectedEvidence({
            orderId,
            type: 'audio',
            evidence: audioEvidence
          });
        } else {
          console.warn('No audio evidence found for order:', orderId);
        }
      } else if (type === 'email') {
        // Extract the actual order ID (remove "order-" prefix)
        const actualOrderId = orderId.replace('order-', '');
        
        // Convert date to the format expected by backend (DDMMYYYY)
        const dateObj = new Date(order.orderDate);
        const day = String(dateObj.getDate()).padStart(2, '0');
        const month = String(dateObj.getMonth() + 1).padStart(2, '0');
        const year = dateObj.getFullYear();
        const backendDate = `${day}${month}${year}`;
        
        const emailEvidence = await surveillanceDataService.getEmailEvidence(actualOrderId, backendDate);
        if (emailEvidence) {
          setSelectedEvidence({
            orderId,
            type: 'email',
            evidence: emailEvidence
          });
        } else {
          console.warn('No email evidence found for order:', orderId);
        }
      }
    } catch (error) {
      console.error('Error loading evidence:', error);
    }
  };

  const handleViewDiscrepancy = async (orderId: string) => {
    const order = orders.find(o => o.id === orderId);
    if (!order) return;

    try {
      // Extract the actual order ID (remove "order-" prefix)
      const actualOrderId = orderId.replace('order-', '');
      
      // Convert date to the format expected by backend (DDMMYYYY)
      const dateObj = new Date(order.orderDate);
      const day = String(dateObj.getDate()).padStart(2, '0');
      const month = String(dateObj.getMonth() + 1).padStart(2, '0');
      const year = dateObj.getFullYear();
      const backendDate = `${day}${month}${year}`;
      
      const discrepancyDetails = await surveillanceDataService.getDiscrepancyDetails(actualOrderId, backendDate);
      if (discrepancyDetails) {
        setSelectedDiscrepancy(discrepancyDetails);
      } else {
        console.warn('No discrepancy details found for order:', orderId);
      }
    } catch (error) {
      console.error('Error loading discrepancy details:', error);
    }
  };

  const handleExport = async () => {
    try {
      console.log('Exporting orders for metric:', metricType);
      
      // Build query parameters
      const params = new URLSearchParams({
        year: year.toString(),
        month: month,
      });
      
      if (dateFilter?.startDate) {
        params.append('start_date', dateFilter.startDate);
      }
      if (dateFilter?.endDate) {
        params.append('end_date', dateFilter.endDate);
      }
      
      // Make request to export endpoint
      const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:5001';
      const response = await fetch(`${apiUrl}/api/surveillance/export/${metricType}?${params}`);
      
      if (!response.ok) {
        throw new Error(`Export failed: ${response.statusText}`);
      }
      
      // Get filename from response headers or generate one
      const contentDisposition = response.headers.get('content-disposition');
      let filename = `${metricType}_Orders_${month}_${year}.xlsx`;
      
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="(.+)"/);
        if (filenameMatch) {
          filename = filenameMatch[1];
        }
      }
      
      // Create blob and download
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      
      console.log('Export completed successfully');
    } catch (error) {
      console.error('Export failed:', error);
      alert('Export failed. Please try again.');
    }
  };

  const handleAssign = (discrepancyId: string, assignee: string) => {
    console.log('Assigning discrepancy:', discrepancyId, 'to:', assignee);
  };

  const handleResolve = (discrepancyId: string, resolution: string) => {
    console.log('Resolving discrepancy:', discrepancyId, 'with resolution:', resolution);
    setSelectedDiscrepancy(null);
  };

  const handleDismiss = (discrepancyId: string, reason: string) => {
    console.log('Dismissing discrepancy:', discrepancyId, 'with reason:', reason);
    setSelectedDiscrepancy(null);
  };

  if (loading) {
    return (
      <div className="p-6">
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
            <p className="text-muted-foreground">Loading order details...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <Button variant="outline" onClick={onBack}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Dashboard
          </Button>
          <div>
            <h1 className="text-2xl font-bold">{getTitleForMetric(metricType)}</h1>
            <p className="text-muted-foreground">{month} {year} • {orders.length} orders</p>
          </div>
        </div>
        
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={handleExport}>
            <Download className="h-4 w-4 mr-2" />
            Export All
          </Button>
        </div>
      </div>

      {/* Order Table */}
      <OrderTable
        title={getTitleForMetric(metricType)}
        orders={orders}
        onViewEvidence={handleViewEvidence}
        onViewDiscrepancy={handleViewDiscrepancy}
        onExport={handleExport}
      />

      {/* Evidence Viewer Modal */}
      {selectedEvidence && (
        <EvidenceViewer
          type={selectedEvidence.type}
          evidence={selectedEvidence.evidence}
          orderId={selectedEvidence.orderId}
          orderDetails={selectedEvidence.type === 'audio' ? {
            symbol: orders.find(o => o.id === selectedEvidence.orderId)?.symbol || '',
            quantity: orders.find(o => o.id === selectedEvidence.orderId)?.quantity || 0,
            price: orders.find(o => o.id === selectedEvidence.orderId)?.price || 0,
            buySell: orders.find(o => o.id === selectedEvidence.orderId)?.buySell || 'BUY',
            clientId: orders.find(o => o.id === selectedEvidence.orderId)?.clientId || '',
            clientName: orders.find(o => o.id === selectedEvidence.orderId)?.clientName || '',
            orderDate: orders.find(o => o.id === selectedEvidence.orderId)?.orderDate || ''
          } : undefined}
          onClose={() => setSelectedEvidence(null)}
        />
      )}

      {/* Discrepancy Details Modal */}
      {selectedDiscrepancy && (
        <DiscrepancyDetails
          discrepancy={selectedDiscrepancy}
          onClose={() => setSelectedDiscrepancy(null)}
          onAssign={handleAssign}
          onResolve={handleResolve}
          onDismiss={handleDismiss}
        />
      )}
    </div>
  );
};
