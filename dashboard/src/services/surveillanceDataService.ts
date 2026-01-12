// Data service to read real surveillance data from Excel and JSON files
// This will be implemented to read from your actual surveillance output files

import { API_CONFIG } from '../config/api';

export interface RealOrder {
  id: string;
  orderId: string;
  clientId: string;
  clientName: string;
  symbol: string;
  quantity: number;
  price: number;
  buySell: 'BUY' | 'SELL';
  status: 'Complete' | 'Cancelled' | 'Rejected';
  orderDate: string;
  audioFile?: string;
  emailContent?: string;
  discrepancy?: string;
  aiObservation?: string;
  hasAudio: boolean;
  hasEmail: boolean;
  hasDiscrepancy: boolean;
  // Real data fields from your surveillance system
  audioMapped?: string;
  emailMatchStatus?: string;
  emailConfidenceScore?: number;
  emailDiscrepancyDetails?: string;
  callExtract?: string;
  observation?: string;
  mobileNumber?: string;
  callReceivedFromRegisteredNumber?: string;
  orderExecuted?: string;
}

export interface RealAudioEvidence {
  filename: string;
  duration: string;
  transcript: string;
  speakers: {
    client: string[];
    dealer: string[];
  };
  callStart: string;
  callEnd: string;
  mobileNumber: string;
  clientId: string;
  callExtract: string;
}

export interface RealEmailEvidence {
  subject: string;
  sender: string;
  recipient: string;
  date: string;
  content: string;
  attachments?: string[];
  clientCode: string;
  symbol: string;
  quantity: number;
  price: string;
  action: string;
  confidenceScore: number;
  discrepancyDetails?: string;
}

export interface RealDiscrepancy {
  id: string;
  orderId: string;
  type: 'PRICE_MISMATCH' | 'QUANTITY_MISMATCH' | 'SYMBOL_MISMATCH' | 'TIMING_ISSUE' | 'AUDIO_ISSUE' | 'EMAIL_ISSUE';
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  description: string;
  aiObservation: string;
  recommendedAction: 'REVIEW' | 'INVESTIGATE' | 'REVERSE' | 'NONE';
  evidence: {
    audio?: RealAudioEvidence;
    email?: RealEmailEvidence;
    order?: {
      details: string;
      timestamp: string;
    };
  };
  status: 'OPEN' | 'INVESTIGATING' | 'RESOLVED' | 'DISMISSED';
  createdAt: string;
  updatedAt: string;
  assignedTo?: string;
  resolution?: string;
}

class SurveillanceDataService {
  private baseUrl = API_CONFIG.baseUrl;
  private apiBase = API_CONFIG.apiBase;
  
  constructor() {
    // Debug: Log the API URL being used
    console.log('🔧 SurveillanceDataService initialized with API URL:', this.baseUrl);
    console.log('🔧 Environment variable REACT_APP_API_URL:', process.env.REACT_APP_API_URL);
  }

  // Get real orders for a specific metric type and date
  async getOrdersForMetric(metricType: string, month: string, year: number, startDate?: string, endDate?: string): Promise<RealOrder[]> {
    let url = `${this.apiBase}/orders/${year}/${month}/${metricType}`;
    
    // Add date filtering parameters if provided
    const params = new URLSearchParams();
    if (startDate) params.append('startDate', startDate);
    if (endDate) params.append('endDate', endDate);
    if (params.toString()) {
      url += `?${params.toString()}`;
    }
    
    try {
      console.log(`Fetching orders from: ${url}`);
      // This will call your backend API to read from actual Excel files
      // Add cache-busting and ensure fresh data
      const response = await fetch(url, {
        cache: 'no-store',
        headers: {
          'Cache-Control': 'no-cache',
          'Pragma': 'no-cache'
        }
      });
      console.log('Response status:', response.status);
      if (!response.ok) {
        throw new Error(`Failed to fetch orders: ${response.statusText}`);
      }
      const data = await response.json();
      console.log(`Received ${data.length} orders from backend`);
      return data;
    } catch (error) {
      console.error('Error fetching orders:', error);
      console.error('API URL attempted:', url);
      console.error('Full error details:', error);
      // Don't fallback to mock data - return empty array so user knows there's an issue
      // This will help debug why API calls are failing
      throw error; // Re-throw so caller knows the request failed
    }
  }

  // Get available dates for a month
  async getAvailableDates(year: number, month: string): Promise<{value: string, label: string, day: number, month: number, year: number}[]> {
    try {
      const response = await fetch(`${this.apiBase}/available-dates/${year}/${month}`);
      if (!response.ok) {
        throw new Error(`Failed to fetch available dates: ${response.statusText}`);
      }
      return await response.json();
    } catch (error) {
      console.error('Error fetching available dates:', error);
      return [];
    }
  }

  // Get real audio evidence for an order
  async getAudioEvidence(orderId: string, date: string): Promise<RealAudioEvidence | null> {
    try {
      const response = await fetch(`${this.apiBase}/audio/${orderId}/${date}`);
      if (!response.ok) {
        return null;
      }
      return await response.json();
    } catch (error) {
      console.error('Error fetching audio evidence:', error);
      return null;
    }
  }

  // Get real email evidence for an order
  async getEmailEvidence(orderId: string, date: string): Promise<RealEmailEvidence | null> {
    try {
      const response = await fetch(`${this.apiBase}/email/${orderId}/${date}`);
      if (!response.ok) {
        return null;
      }
      return await response.json();
    } catch (error) {
      console.error('Error fetching email evidence:', error);
      return null;
    }
  }

  // Get real discrepancy details for an order
  async getDiscrepancyDetails(orderId: string, date: string): Promise<RealDiscrepancy | null> {
    try {
      const response = await fetch(`${this.apiBase}/discrepancy/${orderId}/${date}`);
      if (!response.ok) {
        return null;
      }
      return await response.json();
    } catch (error) {
      console.error('Error fetching discrepancy details:', error);
      return null;
    }
  }

  // Mock data fallback for development
  private getMockOrdersForMetric(metricType: string): RealOrder[] {
    const mockOrders: RealOrder[] = [];
    const orderCount = this.getOrderCountForMetric(metricType);
    
    for (let i = 0; i < orderCount; i++) {
      const order: RealOrder = {
        id: `order-${i + 1}`,
        orderId: `ORD${String(i + 1).padStart(6, '0')}`,
        clientId: `CLIENT${String(i + 1).padStart(4, '0')}`,
        clientName: `Client ${i + 1}`,
        symbol: ['RELIANCE', 'TCS', 'INFY', 'HDFC', 'ICICIBANK'][i % 5],
        quantity: Math.floor(Math.random() * 1000) + 100,
        price: Math.floor(Math.random() * 1000) + 100,
        buySell: Math.random() > 0.5 ? 'BUY' : 'SELL',
        status: this.getStatusForMetric(metricType),
        orderDate: `2025-08-${String(Math.floor(Math.random() * 28) + 1).padStart(2, '0')}`,
        hasAudio: metricType === 'audioMatches' || Math.random() > 0.7,
        hasEmail: metricType === 'emailMatches' || Math.random() > 0.8,
        hasDiscrepancy: metricType === 'discrepancies' || Math.random() > 0.9,
        audioMapped: metricType === 'audioMatches' ? 'yes' : 'no',
        emailMatchStatus: metricType === 'emailMatches' ? 'Matched' : 'No Email Match',
        emailConfidenceScore: metricType === 'emailMatches' ? Math.floor(Math.random() * 40) + 60 : 0,
        callExtract: metricType === 'audioMatches' ? `Call transcript for order ${i + 1}` : undefined,
        observation: `AI observation for order ${i + 1}`,
        mobileNumber: `+91-987654${String(i + 1).padStart(4, '0')}`,
        callReceivedFromRegisteredNumber: 'Y',
        orderExecuted: 'Y'
      };
      mockOrders.push(order);
    }
    
    return mockOrders;
  }

  private getOrderCountForMetric(metric: string): number {
    switch (metric) {
      case 'totalTrades': return 283;
      case 'emailMatches': return 31;
      case 'omsMatches': return 17;
      case 'audioMatches': return 185;
      case 'unmatchedOrders': return 67;
      case 'discrepancies': return 81;
      case 'cancelledOrders': return 57;
      case 'rejectedOrders': return 59;
      default: return 0;
    }
  }

  private getStatusForMetric(metric: string): 'Complete' | 'Cancelled' | 'Rejected' {
    switch (metric) {
      case 'cancelledOrders': return 'Cancelled';
      case 'rejectedOrders': return 'Rejected';
      default: return 'Complete';
    }
  }
}

export const surveillanceDataService = new SurveillanceDataService();
