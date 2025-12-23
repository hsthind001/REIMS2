/**
 * Explainability Panel Component
 * 
 * Shows "Why Flagged", "What Would Resolve", and "What Changed" for matches and discrepancies
 */
import { AlertTriangle, Lightbulb, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { Card } from '../design-system';
import type { ForensicMatch, ForensicDiscrepancy } from '../../lib/forensic_reconciliation';

interface ExplainabilityPanelProps {
  match?: ForensicMatch | null;
  discrepancy?: ForensicDiscrepancy | null;
  whyFlagged?: string[];
  whatWouldResolve?: string[];
  trend?: {
    priorPeriod?: number;
    currentPeriod?: number;
    change?: number;
    changePercent?: number;
  };
}

export default function ExplainabilityPanel({
  match,
  discrepancy,
  whyFlagged = [],
  whatWouldResolve = [],
  trend
}: ExplainabilityPanelProps) {
  // Auto-generate why flagged if not provided
  if (!whyFlagged.length && match) {
    const reasons: string[] = [];
    const confidence = parseFloat(match.confidence_score.toString());
    
    if (confidence < 70) {
      reasons.push(`Low confidence score (${confidence.toFixed(0)}%)`);
    }
    
    if (match.amount_difference) {
      const diff = Math.abs(parseFloat(match.amount_difference.toString()));
      if (diff > 1000) {
        reasons.push(`Large amount difference ($${diff.toLocaleString()})`);
      }
    }
    
    if (match.exception_tier === 'tier_3_escalate') {
      reasons.push('Critical account or low confidence match');
    }
    
    if (match.source_account_code !== match.target_account_code) {
      reasons.push('Account code mismatch');
    }
    
    whyFlagged = reasons.length > 0 ? reasons : ['Standard review required'];
  }

  // Auto-generate what would resolve if not provided
  if (!whatWouldResolve.length && match) {
    const suggestions: string[] = [];
    
    if (match.amount_difference && Math.abs(parseFloat(match.amount_difference.toString())) < 1) {
      suggestions.push('Accept as rounding difference');
    }
    
    if (match.source_account_code !== match.target_account_code) {
      suggestions.push(`Map ${match.source_account_code} to ${match.target_account_code}`);
    }
    
    if (match.exception_tier === 'tier_1_auto_suggest') {
      suggestions.push('Apply suggested fix from auto-resolution rules');
    }
    
    whatWouldResolve = suggestions.length > 0 ? suggestions : ['Review and approve if correct'];
  }

  return (
    <div className="space-y-4">
      {/* Why Flagged Card */}
      <Card className="p-4 border-l-4 border-yellow-500">
        <div className="flex items-center gap-2 mb-3">
          <AlertTriangle className="w-5 h-5 text-yellow-600" />
          <h3 className="text-sm font-semibold text-gray-900">Why Flagged</h3>
        </div>
        {whyFlagged.length > 0 ? (
          <ul className="space-y-2">
            {whyFlagged.slice(0, 3).map((reason, index) => (
              <li key={index} className="text-sm text-gray-700 flex items-start gap-2">
                <span className="text-yellow-600 mt-1">•</span>
                <span>{reason}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-gray-500">No specific reasons identified</p>
        )}
      </Card>

      {/* What Would Resolve Card */}
      <Card className="p-4 border-l-4 border-blue-500">
        <div className="flex items-center gap-2 mb-3">
          <Lightbulb className="w-5 h-5 text-blue-600" />
          <h3 className="text-sm font-semibold text-gray-900">What Would Resolve</h3>
        </div>
        {whatWouldResolve.length > 0 ? (
          <ul className="space-y-2">
            {whatWouldResolve.slice(0, 3).map((suggestion, index) => (
              <li key={index} className="text-sm text-gray-700 flex items-start gap-2">
                <span className="text-blue-600 mt-1">•</span>
                <span>{suggestion}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-gray-500">No suggestions available</p>
        )}
      </Card>

      {/* What Changed Card */}
      {trend && (trend.priorPeriod !== undefined || trend.currentPeriod !== undefined) && (
        <Card className="p-4 border-l-4 border-green-500">
          <div className="flex items-center gap-2 mb-3">
            {trend.change && trend.change > 0 ? (
              <TrendingUp className="w-5 h-5 text-green-600" />
            ) : trend.change && trend.change < 0 ? (
              <TrendingDown className="w-5 h-5 text-red-600" />
            ) : (
              <Minus className="w-5 h-5 text-gray-600" />
            )}
            <h3 className="text-sm font-semibold text-gray-900">What Changed</h3>
          </div>
          <div className="space-y-2">
            {trend.priorPeriod !== undefined && (
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Prior Period:</span>
                <span className="font-medium">${trend.priorPeriod.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
              </div>
            )}
            {trend.currentPeriod !== undefined && (
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Current Period:</span>
                <span className="font-medium">${trend.currentPeriod.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
              </div>
            )}
            {trend.change !== undefined && (
              <div className={`flex justify-between text-sm pt-2 border-t ${
                trend.change > 0 ? 'text-green-700' : trend.change < 0 ? 'text-red-700' : 'text-gray-700'
              }`}>
                <span>Change:</span>
                <span className="font-semibold">
                  {trend.change > 0 ? '+' : ''}${trend.change.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  {trend.changePercent !== undefined && ` (${trend.changePercent > 0 ? '+' : ''}${trend.changePercent.toFixed(1)}%)`}
                </span>
              </div>
            )}
          </div>
        </Card>
      )}
    </div>
  );
}

