import { 
  AlertTriangle, 
  ArrowRight,
  Calculator,
  AlertCircle,
  HelpCircle,
  CheckCircle,
  XCircle,
  ExternalLink,
  FileText
} from 'lucide-react';
import { Card, Button } from '../design-system';
import type { ForensicDiscrepancy } from '../../lib/forensic_reconciliation';

interface RuleFailureDetailProps {
  discrepancy: ForensicDiscrepancy & { rule_code?: string; source_document?: string; target_document?: string };
  onViewSource?: (docType?: string) => void;
}

export default function RuleFailureDetail({ discrepancy, onViewSource }: RuleFailureDetailProps) {
  // E8-S1: Show rule, evidence, numbers, source link
  const ruleCode = (discrepancy as any).rule_code || discrepancy.description?.match(/Rule\s+([A-Z0-9_-]+)/i)?.[1];
  const title = discrepancy.description || 'Rule Validation Failure';
  const sourceDoc = (discrepancy as any).source_document;
  const targetDoc = (discrepancy as any).target_document;
  
  const formatValue = (val?: number | string | null) => {
    if (val === null || val === undefined) return 'N/A';
    const num = typeof val === 'string' ? parseFloat(val) : val;
    return num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  };

  const getSeverityColor = (severity: string) => {
    switch (severity.toLowerCase()) {
      case 'critical': return 'text-red-700 bg-red-50 border-red-200';
      case 'high': return 'text-orange-700 bg-orange-50 border-orange-200';
      case 'medium': return 'text-yellow-700 bg-yellow-50 border-yellow-200';
      default: return 'text-blue-700 bg-blue-50 border-blue-200';
    }
  };

  const severityClass = getSeverityColor(discrepancy.severity);

  return (
    <div className="space-y-4">
      {/* Header Card */}
      <Card className={`p-4 border-2 ${severityClass}`}>
        <div className="flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="font-semibold text-lg leading-tight mb-1">{title}</h3>
            <p className="text-sm opacity-90">
              Discrepancy ID: #{discrepancy.id} • Type: {discrepancy.discrepancy_type.replace('_', ' ').toUpperCase()}
            </p>
          </div>
        </div>
      </Card>

      {/* Comparison Details */}
      <Card className="p-0 overflow-hidden text-sm">
        <div className="bg-gray-50 px-4 py-2 border-b flex items-center justify-between">
          <span className="font-medium text-gray-700 flex items-center gap-2">
            <Calculator className="w-4 h-4" />
            Validation Results
          </span>
          <span className="text-xs text-gray-500">
            {ruleCode ? `Rule: ${ruleCode}` : 'Rule Source: Calculated Engine'}
          </span>
        </div>
        
        <div className="p-4 grid grid-cols-2 gap-x-8 gap-y-4">
            {/* Expected Value */}
            <div className="space-y-1">
              <span className="text-xs text-gray-500 font-medium uppercase tracking-wider">Expected Value</span>
              <div className="p-3 bg-green-50 rounded border border-green-100 flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-green-600" />
                <span className="font-mono font-semibold text-green-900">
                  {formatValue(discrepancy.expected_value)}
                </span>
              </div>
            </div>

            {/* Actual Value */}
            <div className="space-y-1">
              <span className="text-xs text-gray-500 font-medium uppercase tracking-wider">Actual Value</span>
              <div className="p-3 bg-red-50 rounded border border-red-100 flex items-center gap-2">
                <XCircle className="w-4 h-4 text-red-600" />
                <span className="font-mono font-semibold text-red-900">
                  {formatValue(discrepancy.actual_value)}
                </span>
              </div>
            </div>

            {/* Difference */}
            <div className="col-span-2 mt-2">
              <div className="relative">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-gray-200"></div>
                </div>
                <div className="relative flex justify-center text-xs">
                  <span className="px-2 bg-white text-gray-500 font-medium">VARIANCE ANALYSIS</span>
                </div>
              </div>
            </div>

            <div className="col-span-2 grid grid-cols-2 gap-8">
              <div>
                <span className="text-xs text-gray-500">Absolute Difference</span>
                <p className="text-lg font-bold text-gray-900 mt-1">
                  {formatValue(discrepancy.difference)}
                </p>
              </div>
              <div>
                 <span className="text-xs text-gray-500">Percentage Variance</span>
                 <p className="text-lg font-bold text-gray-900 mt-1">
                   {formatValue(discrepancy.difference_percent)}%
                 </p>
              </div>
            </div>
        </div>
      </Card>

      {/* Suggestion / Context */}
      <Card className="p-4 bg-gray-50">
        <div className="flex items-start gap-3">
          <HelpCircle className="w-5 h-5 text-gray-400 mt-0.5" />
          <div className="space-y-1">
            <h4 className="text-sm font-semibold text-gray-900">Recommendation</h4>
            {discrepancy.difference && parseFloat(discrepancy.difference.toString()) < 10.0 ? (
               <p className="text-sm text-gray-600">
                 The variance is immaterial (less than $10). You may choose to <b>Ignore</b> this discrepancy.
               </p>
            ) : (
               <p className="text-sm text-gray-600">
                 This variance exceeds the tolerance threshold. Please investigate the source documents or create an adjusting journal entry.
               </p>
            )}
          </div>
        </div>
      </Card>
      
      {/* E8-S1: Source document links */}
      {(sourceDoc || targetDoc || onViewSource) && (
        <Card className="p-4">
          <h4 className="text-sm font-semibold text-gray-900 mb-2 flex items-center gap-2">
            <FileText className="w-4 h-4" />
            Source Documents
          </h4>
          <div className="flex flex-wrap gap-2">
            {sourceDoc && (
              <span className="text-sm text-gray-600 px-2 py-1 bg-gray-100 rounded">
                Source: {sourceDoc}
              </span>
            )}
            {targetDoc && (
              <span className="text-sm text-gray-600 px-2 py-1 bg-gray-100 rounded">
                Target: {targetDoc}
              </span>
            )}
            {onViewSource && (
              <Button
                variant="secondary"
                size="sm"
                icon={<ExternalLink className="w-4 h-4" />}
                onClick={() => onViewSource()}
              >
                View Source PDF
              </Button>
            )}
          </div>
        </Card>
      )}

      {/* Action Buttons Placeholder - could be expanded */}
      <div className="grid grid-cols-2 gap-3">
         <Button variant="secondary" className="w-full justify-center">
            Ignore Rule
         </Button>
         <Button variant="primary" className="w-full justify-center">
            Create Task
         </Button>
      </div>
    </div>
  );
}
