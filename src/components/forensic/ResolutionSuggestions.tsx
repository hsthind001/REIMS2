/**
 * Resolution Suggestions Component
 * 
 * Shows suggested resolutions for matches and discrepancies
 */
import { Lightbulb, CheckCircle, ArrowRight } from 'lucide-react';
import { Card, Button } from '../design-system';
import type { ForensicMatch } from '../../lib/forensic_reconciliation';

interface ResolutionSuggestionsProps {
  match?: ForensicMatch | null;
  suggestions?: Array<{
    type: string;
    description: string;
    suggested_action: string;
    confidence?: number;
  }>;
  onApplySuggestion?: (suggestion: any) => void;
}

export default function ResolutionSuggestions({
  match,
  suggestions = [],
  onApplySuggestion
}: ResolutionSuggestionsProps) {
  // Generate suggestions if not provided
  const displaySuggestions = suggestions.length > 0 ? suggestions : [];

  if (displaySuggestions.length === 0 && match) {
    if (match.amount_difference && Math.abs(parseFloat(match.amount_difference.toString())) < 1) {
      displaySuggestions.push({
        type: 'rounding_adjustment',
        description: `Minor rounding difference of $${Math.abs(parseFloat(match.amount_difference.toString())).toFixed(2)}`,
        suggested_action: 'Accept as rounding difference',
        confidence: 95
      });
    }

    if (match.source_account_code !== match.target_account_code) {
      displaySuggestions.push({
        type: 'account_mapping',
        description: `Account code mismatch: ${match.source_account_code} vs ${match.target_account_code}`,
        suggested_action: `Map ${match.source_account_code} to ${match.target_account_code}`,
        confidence: parseFloat(match.confidence_score.toString())
      });
    }

    // Ignore small differences (< $10 but > $1)
    if (match.amount_difference && Math.abs(parseFloat(match.amount_difference.toString())) < 10 && Math.abs(parseFloat(match.amount_difference.toString())) >= 1) {
      displaySuggestions.push({
        type: 'ignore_variance',
        description: `Small variance of $${Math.abs(parseFloat(match.amount_difference.toString())).toFixed(2)}`,
        suggested_action: 'Ignore (Immaterial)',
        confidence: 90
      });
    }

    // Suggest Journal Entry for significant differences
    if (match.amount_difference && Math.abs(parseFloat(match.amount_difference.toString())) >= 10) {
       displaySuggestions.push({
        type: 'journal_entry',
        description: `Unresolved difference of $${Math.abs(parseFloat(match.amount_difference.toString())).toFixed(2)}`,
        suggested_action: 'Create Adjusting Journal Entry',
        confidence: 85
      });
    }

    if (match.exception_tier === 'tier_1_auto_suggest') {
      displaySuggestions.push({
        type: 'auto_suggest',
        description: 'Auto-suggested fix available',
        suggested_action: 'Apply suggested fix from auto-resolution rules',
        confidence: 90
      });
    }
  }

  return (
    <Card className="p-4 border-l-4 border-blue-500 bg-blue-50">
      <div className="flex items-center gap-2 mb-3">
        <Lightbulb className="w-5 h-5 text-blue-600" />
        <h3 className="text-sm font-semibold text-gray-900">What Would Resolve</h3>
      </div>
      {displaySuggestions.length > 0 ? (
        <div className="space-y-3">
          {displaySuggestions.slice(0, 3).map((suggestion, index) => (
            <div key={index} className="p-3 bg-white rounded border border-blue-200">
              <div className="flex items-start justify-between mb-2">
                <div className="flex-1">
                  <p className="text-sm font-medium text-gray-900">{suggestion.description}</p>
                  <p className="text-xs text-gray-600 mt-1">{suggestion.suggested_action}</p>
                </div>
                {suggestion.confidence !== undefined && (
                  <span className="text-xs px-2 py-1 rounded bg-blue-100 text-blue-700 font-medium">
                    {suggestion.confidence.toFixed(0)}%
                  </span>
                )}
              </div>
              {onApplySuggestion && (
                <Button
                  variant="secondary"
                  size="sm"
                  className="w-full mt-2"
                  onClick={() => onApplySuggestion(suggestion)}
                  icon={<CheckCircle className="w-3 h-3" />}
                >
                  Apply Suggestion
                </Button>
              )}
            </div>
          ))}
        </div>
      ) : (
        <p className="text-sm text-gray-500">No suggestions available. Review manually.</p>
      )}
    </Card>
  );
}

