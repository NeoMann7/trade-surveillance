import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { 
  Search, 
  Download, 
  Eye, 
  Play, 
  Mail, 
  AlertTriangle,
  FileText
} from 'lucide-react';

interface Order {
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
}

interface OrderTableProps {
  title: string;
  orders: Order[];
  onViewEvidence: (orderId: string, type: 'audio' | 'email') => void;
  onViewDiscrepancy: (orderId: string) => void;
  onExport: () => void;
}

export const OrderTable: React.FC<OrderTableProps> = ({
  title,
  orders,
  onViewEvidence,
  onViewDiscrepancy,
  onExport
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [sortBy, setSortBy] = useState<keyof Order>('orderDate');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');

  // Filter and sort orders
  const filteredOrders = orders
    .filter(order => {
      const matchesSearch = 
        order.orderId.toLowerCase().includes(searchTerm.toLowerCase()) ||
        order.clientId.toLowerCase().includes(searchTerm.toLowerCase()) ||
        order.symbol.toLowerCase().includes(searchTerm.toLowerCase());
      
      const matchesFilter = filterStatus === 'all' || order.status === filterStatus;
      
      return matchesSearch && matchesFilter;
    })
    .sort((a, b) => {
      const aVal = a[sortBy];
      const bVal = b[sortBy];
      
      // Handle undefined values
      if (aVal === undefined && bVal === undefined) return 0;
      if (aVal === undefined) return 1;
      if (bVal === undefined) return -1;
      
      if (sortOrder === 'asc') {
        return aVal > bVal ? 1 : -1;
      } else {
        return aVal < bVal ? 1 : -1;
      }
    });

  const handleSort = (column: keyof Order) => {
    if (sortBy === column) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(column);
      setSortOrder('asc');
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'Complete': return 'text-green-600 bg-green-50';
      case 'Cancelled': return 'text-yellow-600 bg-yellow-50';
      case 'Rejected': return 'text-red-600 bg-red-50';
      default: return 'text-gray-600 bg-gray-50';
    }
  };

  const getBuySellColor = (buySell: string) => {
    return buySell === 'BUY' ? 'text-green-600' : 'text-red-600';
  };

  return (
    <Card className="w-full">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            {title} ({filteredOrders.length} orders)
          </CardTitle>
          <Button onClick={onExport} variant="outline" size="sm">
            <Download className="h-4 w-4 mr-2" />
            Export
          </Button>
        </div>
      </CardHeader>
      
      <CardContent>
        {/* Search and Filter Controls */}
        <div className="flex gap-4 mb-6">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search orders, clients, symbols..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>
          
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
          >
            <option value="all">All Status</option>
            <option value="Complete">Complete</option>
            <option value="Cancelled">Cancelled</option>
            <option value="Rejected">Rejected</option>
          </select>
        </div>

        {/* Orders Table */}
        <div className="overflow-x-auto">
          <table className="w-full border-collapse">
            <thead>
              <tr className="border-b">
                <th 
                  className="text-left p-3 cursor-pointer hover:bg-gray-50"
                  onClick={() => handleSort('orderId')}
                >
                  Order ID {sortBy === 'orderId' && (sortOrder === 'asc' ? '↑' : '↓')}
                </th>
                <th 
                  className="text-left p-3 cursor-pointer hover:bg-gray-50"
                  onClick={() => handleSort('clientId')}
                >
                  Client {sortBy === 'clientId' && (sortOrder === 'asc' ? '↑' : '↓')}
                </th>
                <th 
                  className="text-left p-3 cursor-pointer hover:bg-gray-50"
                  onClick={() => handleSort('symbol')}
                >
                  Symbol {sortBy === 'symbol' && (sortOrder === 'asc' ? '↑' : '↓')}
                </th>
                <th 
                  className="text-left p-3 cursor-pointer hover:bg-gray-50"
                  onClick={() => handleSort('quantity')}
                >
                  Quantity {sortBy === 'quantity' && (sortOrder === 'asc' ? '↑' : '↓')}
                </th>
                <th 
                  className="text-left p-3 cursor-pointer hover:bg-gray-50"
                  onClick={() => handleSort('price')}
                >
                  Price {sortBy === 'price' && (sortOrder === 'asc' ? '↑' : '↓')}
                </th>
                <th 
                  className="text-left p-3 cursor-pointer hover:bg-gray-50"
                  onClick={() => handleSort('buySell')}
                >
                  Buy/Sell {sortBy === 'buySell' && (sortOrder === 'asc' ? '↑' : '↓')}
                </th>
                <th 
                  className="text-left p-3 cursor-pointer hover:bg-gray-50"
                  onClick={() => handleSort('status')}
                >
                  Status {sortBy === 'status' && (sortOrder === 'asc' ? '↑' : '↓')}
                </th>
                <th 
                  className="text-left p-3 cursor-pointer hover:bg-gray-50"
                  onClick={() => handleSort('orderDate')}
                >
                  Date {sortBy === 'orderDate' && (sortOrder === 'asc' ? '↑' : '↓')}
                </th>
                <th className="text-left p-3">Evidence</th>
                <th className="text-left p-3">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredOrders.map((order) => (
                <tr key={order.id} className="border-b hover:bg-gray-50">
                  <td className="p-3 font-mono text-sm">{order.orderId}</td>
                  <td className="p-3">
                    <div>
                      <div className="font-medium">{order.clientId}</div>
                      <div className="text-sm text-muted-foreground">{order.clientName}</div>
                    </div>
                  </td>
                  <td className="p-3 font-medium">{order.symbol}</td>
                  <td className="p-3">{order.quantity.toLocaleString()}</td>
                  <td className="p-3">₹{order.price.toFixed(2)}</td>
                  <td className={`p-3 font-medium ${getBuySellColor(order.buySell)}`}>
                    {order.buySell}
                  </td>
                  <td className="p-3">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(order.status)}`}>
                      {order.status}
                    </span>
                  </td>
                  <td className="p-3 text-sm">{order.orderDate}</td>
                  <td className="p-3">
                    <div className="flex gap-2">
                      {order.hasAudio && (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => onViewEvidence(order.id, 'audio')}
                          className="h-8 w-8 p-0"
                        >
                          <Play className="h-3 w-3" />
                        </Button>
                      )}
                      {order.hasEmail && (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => onViewEvidence(order.id, 'email')}
                          className="h-8 w-8 p-0"
                        >
                          <Mail className="h-3 w-3" />
                        </Button>
                      )}
                      {order.hasDiscrepancy && (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => onViewDiscrepancy(order.id)}
                          className="h-8 w-8 p-0 text-red-600"
                        >
                          <AlertTriangle className="h-3 w-3" />
                        </Button>
                      )}
                    </div>
                  </td>
                  <td className="p-3">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => onViewEvidence(order.id, 'audio')}
                    >
                      <Eye className="h-3 w-3 mr-1" />
                      View
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {filteredOrders.length === 0 && (
          <div className="text-center py-8 text-muted-foreground">
            No orders found matching your criteria.
          </div>
        )}
      </CardContent>
    </Card>
  );
};
