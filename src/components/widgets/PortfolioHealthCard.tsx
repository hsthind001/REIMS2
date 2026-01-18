import React from 'react';
import { Card } from '../ui/Card';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

interface PortfolioHealthCardProps {
  score: number | null;
  status: 'excellent' | 'good' | 'fair' | 'poor' | 'loading';
  totalProperties: number;
  avgOccupancy: number;
  criticalAlerts: number;
  loading?: boolean;
}

export const PortfolioHealthCard: React.FC<PortfolioHealthCardProps> = ({
  score,
  status,
  totalProperties,
  avgOccupancy,
  criticalAlerts,
  loading = false
}) => {
  if (loading) {
    return (
      <Card className="h-full p-6 flex flex-col justify-center items-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500"></div>
        <span className="mt-2 text-sm text-gray-500">Loading health score...</span>
      </Card>
    );
  }

  const getStatusColor = (s: string) => {
    switch (s) {
      case 'excellent': return 'text-green-600 bg-green-50';
      case 'good': return 'text-blue-600 bg-blue-50';
      case 'fair': return 'text-yellow-600 bg-yellow-50';
      case 'poor': return 'text-red-600 bg-red-50';
      default: return 'text-gray-600 bg-gray-50';
    }
  };

  const getColorHex = (s: string) => {
    switch (s) {
      case 'excellent': return '#16a34a'; // green-600
      case 'good': return '#2563eb'; // blue-600
      case 'fair': return '#ca8a04'; // yellow-600
      case 'poor': return '#dc2626'; // red-600
      default: return '#4b5563';
    }
  };

  return (
    <Card className="h-full p-6">
      <div className="flex justify-between items-start mb-4">
        <div>
          <h3 className="text-gray-500 font-medium text-sm uppercase tracking-wider">Portfolio Health</h3>
          <div className="flex items-baseline mt-1">
             <span className="text-3xl font-bold text-gray-900">{score !== null ? score : '-'}</span>
             <span className="text-gray-400 text-sm ml-1">/100</span>
          </div>
        </div>
        <div className={`px-3 py-1 rounded-full text-sm font-medium capitalize ${getStatusColor(status)}`}>
          {status}
        </div>
      </div>

      <div className="w-full bg-gray-200 rounded-full h-2.5 mb-6">
        <div 
          className="h-2.5 rounded-full transition-all duration-500" 
          style={{ width: `${score || 0}%`, backgroundColor: getColorHex(status) }}
        ></div>
      </div>

      <div className="grid grid-cols-2 gap-4 border-t pt-4">
        <div>
          <div className="text-gray-500 text-xs">Occupancy</div>
          <div className="font-semibold">{avgOccupancy.toFixed(1)}%</div>
        </div>
        <div>
          <div className="text-gray-500 text-xs">Properties</div>
          <div className="font-semibold">{totalProperties}</div>
        </div>
        <div>
          <div className="text-gray-500 text-xs">Critical Alerts</div>
          <div className={`font-semibold ${criticalAlerts > 0 ? 'text-red-600' : 'text-gray-900'}`}>{criticalAlerts}</div>
        </div>
      </div>
    </Card>
  );
};
