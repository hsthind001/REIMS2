/**
 * Reconciliation Health Gauge Component
 * 
 * Visual health score indicator with breakdown by document type
 */

import { Card } from '../design-system';
import { TrendingUp, TrendingDown, AlertCircle } from 'lucide-react';

interface ReconciliationHealthGaugeProps {
  healthScore: number;
}

export default function ReconciliationHealthGauge({ healthScore = 0 }: ReconciliationHealthGaugeProps) {
  const getHealthColor = (score: number) => {
    if (score >= 80) return 'text-green-600';
    if (score >= 60) return 'text-amber-600';
    return 'text-red-600';
  };

  const getHealthBgColor = (score: number) => {
    if (score >= 80) return 'bg-green-50 border-green-200';
    if (score >= 60) return 'bg-amber-50 border-amber-200';
    return 'bg-red-50 border-red-200';
  };

  const getHealthLabel = (score: number) => {
    if (score >= 80) return 'Excellent';
    if (score >= 60) return 'Good';
    if (score >= 40) return 'Fair';
    return 'Poor';
  };

  // Calculate gauge angle (0-180 degrees for semicircle)
  const gaugeAngle = (healthScore / 100) * 180;

  return (
    <Card className={`p-8 border-2 shadow-sm ${getHealthBgColor(healthScore)}`}>
      <div className="text-center space-y-4">
        <h3 className="text-xl font-semibold text-gray-900">Reconciliation Health Score</h3>
        
        {/* Gauge Visualization */}
        <div className="relative w-80 h-40 mx-auto">
          {/* Background semicircle */}
          <svg className="w-full h-full" viewBox="0 0 200 100">
            {/* Background arc */}
            <path
              d="M 20 80 A 80 80 0 0 1 180 80"
              fill="none"
              stroke="#e5e7eb"
              strokeWidth="20"
              strokeLinecap="round"
            />
            {/* Health score arc */}
            <path
              d={`M 20 80 A 80 80 0 ${gaugeAngle > 90 ? 1 : 0} 1 ${180 - (180 - gaugeAngle) * 2} ${80 - Math.sin((gaugeAngle * Math.PI) / 180) * 80}`}
              fill="none"
              stroke={healthScore >= 80 ? '#10b981' : healthScore >= 60 ? '#f59e0b' : '#ef4444'}
              strokeWidth="20"
              strokeLinecap="round"
            />
          </svg>
          
          {/* Score text */}
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center">
              <div className={`text-6xl font-bold ${getHealthColor(healthScore)}`}>
                {healthScore.toFixed(0)}
              </div>
              <div className="text-base text-gray-600 mt-1">{getHealthLabel(healthScore)}</div>
            </div>
          </div>
        </div>

        {/* Health Indicators */}
        <div className="grid grid-cols-3 gap-6 pt-2">
          <div className="text-center space-y-1">
            <div className="flex items-center justify-center gap-1 text-green-600 mb-1">
              <TrendingUp className="w-4 h-4" />
              <span className="text-sm font-medium">High Confidence</span>
            </div>
            <p className="text-xs text-gray-600">Matches with ≥90% confidence</p>
          </div>
          
          <div className="text-center space-y-1">
            <div className="flex items-center justify-center gap-1 text-amber-600 mb-1">
              <AlertCircle className="w-4 h-4" />
              <span className="text-sm font-medium">Review Needed</span>
            </div>
            <p className="text-xs text-gray-600">Matches requiring auditor review</p>
          </div>
          
          <div className="text-center space-y-1">
            <div className="flex items-center justify-center gap-1 text-red-600 mb-1">
              <TrendingDown className="w-4 h-4" />
              <span className="text-sm font-medium">Discrepancies</span>
            </div>
            <p className="text-xs text-gray-600">Issues requiring resolution</p>
          </div>
        </div>
      </div>
    </Card>
  );
}
