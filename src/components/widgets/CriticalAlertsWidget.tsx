import React from 'react';
import { Card } from '../ui/Card';
import { AlertTriangle, CheckCircle, ArrowRight } from 'lucide-react';
import { Button } from '../ui/Button';

interface AlertItem {
  id: number;
  title: string; // or metric.name
  property_name: string;
  severity: string;
  created_at: Date;
}

interface CriticalAlertsWidgetProps {
  alerts: AlertItem[];
  loading?: boolean;
  onViewAll?: () => void;
  onResolve?: (id: number) => void;
}

export const CriticalAlertsWidget: React.FC<CriticalAlertsWidgetProps> = ({
  alerts,
  loading = false,
  onViewAll,
  onResolve
}) => {
  return (
    <Card className="h-full flex flex-col">
      <div className="p-5 border-b flex justify-between items-center">
        <h3 className="font-semibold text-gray-900 flex items-center gap-2">
          <AlertTriangle className="text-red-500" size={20} />
          Critical Risk Alerts
        </h3>
        {alerts.length > 0 && (
          <span className="bg-red-100 text-red-700 text-xs px-2 py-1 rounded-full font-medium">
            {alerts.length} Active
          </span>
        )}
      </div>
      
      <div className="flex-1 overflow-auto p-0">
        {loading ? (
           <div className="flex justify-center items-center h-40">
             <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-gray-400"></div>
           </div>
        ) : alerts.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-40 text-gray-500">
            <CheckCircle className="text-green-500 mb-2" size={32} />
            <p className="text-sm">No critical alerts</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-100">
            {alerts.slice(0, 5).map((alert) => (
              <div key={alert.id} className="p-4 hover:bg-gray-50 transition-colors">
                <div className="flex justify-between items-start mb-1">
                  <span className="font-medium text-sm text-gray-900 line-clamp-1">{alert.title}</span>
                  <span className="text-xs text-gray-400 whitespace-nowrap">
                    {new Date(alert.created_at).toLocaleDateString()}
                  </span>
                </div>
                <div className="text-xs text-blue-600 mb-2">{alert.property_name}</div>
                <div className="flex justify-between items-center">
                   <span className="text-xs font-semibold px-2 py-0.5 rounded bg-red-50 text-red-700 uppercase tracking-wide">
                     {alert.severity}
                   </span>
                   {onResolve && (
                     <Button 
                       variant="ghost" 
                       size="sm" 
                       className="h-6 text-xs"
                       onClick={(e) => {
                         e.stopPropagation();
                         onResolve(alert.id);
                       }}
                     >
                       Resolve
                     </Button>
                   )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="p-3 border-t bg-gray-50">
        <Button 
          variant="ghost" 
          className="w-full text-sm text-gray-600 justify-center hover:text-blue-600"
          onClick={onViewAll}
        >
          View All Risks <ArrowRight size={14} className="ml-1" />
        </Button>
      </div>
    </Card>
  );
};
