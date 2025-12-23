/**
 * Why Flagged Card Component
 * 
 * Displays top 3 reasons why a match or discrepancy was flagged
 */
import { AlertTriangle } from 'lucide-react';
import { Card } from '../design-system';

interface WhyFlaggedCardProps {
  reasons: string[];
  matchType?: string;
  confidence?: number;
  amountDifference?: number;
}

export default function WhyFlaggedCard({
  reasons,
  matchType,
  confidence,
  amountDifference
}: WhyFlaggedCardProps) {
  // If no reasons provided, generate from match data
  const displayReasons = reasons.length > 0 ? reasons : [];

  if (displayReasons.length === 0) {
    if (confidence !== undefined && confidence < 70) {
      displayReasons.push(`Low confidence score (${confidence.toFixed(0)}%)`);
    }
    if (amountDifference !== undefined && Math.abs(amountDifference) > 1000) {
      displayReasons.push(`Large amount difference ($${Math.abs(amountDifference).toLocaleString()})`);
    }
    if (matchType === 'fuzzy') {
      displayReasons.push('Fuzzy match requires verification');
    }
  }

  return (
    <Card className="p-4 border-l-4 border-yellow-500 bg-yellow-50">
      <div className="flex items-center gap-2 mb-3">
        <AlertTriangle className="w-5 h-5 text-yellow-600" />
        <h3 className="text-sm font-semibold text-gray-900">Why Flagged</h3>
      </div>
      {displayReasons.length > 0 ? (
        <ul className="space-y-2">
          {displayReasons.slice(0, 3).map((reason, index) => (
            <li key={index} className="text-sm text-gray-700 flex items-start gap-2">
              <span className="text-yellow-600 mt-1">•</span>
              <span>{reason}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-gray-500">Standard review required</p>
      )}
    </Card>
  );
}

