import React, { useMemo } from 'react';
import { 
  AlertTriangle, 
  Clock, 
  ArrowRight,
  Filter,
  FileText,
  Calculator
} from 'lucide-react';

interface ExceptionsTabProps {
  discrepancies: any[]; // Forensic discrepancies from matching
  ruleViolations?: any[]; // Rule variances from validation
}

export default function ExceptionsTab({ discrepancies, ruleViolations = [] }: ExceptionsTabProps) {
  // Combine discrepancies and rule violations into unified exception list
  const allExceptions = useMemo(() => {
    const exceptions: any[] = [];
    
    // Add forensic discrepancies
    discrepancies.forEach(d => {
      exceptions.push({
        id: `disc-${d.id}`,
        type: 'discrepancy',
        severity: d.severity || 'medium',
        status: d.status || 'open',
        description: d.description || 'Discrepancy Detected',
        source: d.source_item || 'Cross-Document Match',
        created_at: d.created_at || 'Recently',
        amount_difference: d.difference || d.amount_difference,
        source_value: d.source_value,
        target_value: d.target_value,
        notes: d.notes || d.suggested_resolution,
        originalData: d
      });
    });
    
    // Add rule violations (variances)
    ruleViolations.forEach(rule => {
      // Map rule variance to exception format
      const severity = getSeverityFromRule(rule);
      
      exceptions.push({
        id: `rule-${rule.rule_id}`,
        type: 'rule_violation',
        severity: severity,
        status: 'open',
        description: `${rule.rule_name} (${rule.rule_id})`,
        source: rule.description || 'Validation Rule',
        created_at: 'Current Period',
        amount_difference: rule.actual_value && rule.expected_value 
          ? Math.abs(parseFloat(rule.actual_value) - parseFloat(rule.expected_value))
          : null,
        source_value: rule.expected_value,
        target_value: rule.actual_value,
        notes: rule.formula || 'Rule validation failed',
        originalData: rule
      });
    });
    
    // Sort by severity (critical > high > medium > low)
    const severityOrder = { critical: 0, high: 1, medium: 2, low: 3 };
    exceptions.sort((a, b) => {
      const orderA = severityOrder[a.severity as keyof typeof severityOrder] ?? 4;
      const orderB = severityOrder[b.severity as keyof typeof severityOrder] ?? 4;
      return orderA - orderB;
    });
    
    return exceptions;
  }, [discrepancies, ruleViolations]);
  
  // Determine severity based on rule type and variance magnitude
  const getSeverityFromRule = (rule: any): string => {
    const ruleId = rule.rule_id?.toUpperCase() || '';
    const variance = rule.actual_value && rule.expected_value
      ? Math.abs(parseFloat(rule.actual_value) - parseFloat(rule.expected_value))
      : 0;
    
    // Critical: Fundamental accounting equations
    if (ruleId.includes('BS-1') || ruleId.includes('IS-1') || ruleId.includes('ACCOUNTING')) {
      return 'critical';
    }
    
    // High: Significant financial ratios and liquidity
    if (ruleId.includes('RATIO') || ruleId.includes('LIQUIDITY') || ruleId.includes('WORKING')) {
      return variance > 100000 ? 'high' : 'medium';
    }
    
    // High: Large variances
    if (variance > 500000) {
      return 'high';
    }
    
    // Medium: Moderate variances
    if (variance > 100000) {
      return 'medium';
    }
    
    // Low: Small variances
    return 'low';
  };
  
  // Calculate statistics
  const stats = {
    critical: allExceptions.filter(e => e.severity === 'critical').length,
    high: allExceptions.filter(e => e.severity === 'high').length,
    medium: allExceptions.filter(e => e.severity === 'medium').length,
    low: allExceptions.filter(e => e.severity === 'low').length,
    inProgress: allExceptions.filter(e => e.status === 'investigating' || e.status === 'in_progress').length,
    resolvedToday: 0 // TODO: Calculate based on resolved_at timestamp
  };
  return (
    <div className="space-y-6">
        {/* Header Stats */}
        <div className="grid grid-cols-4 gap-4">
            <div className="bg-red-50 border border-red-100 p-4 rounded-xl">
                <div className="text-red-600 font-medium text-sm mb-1">Critical Issues</div>
                <div className="text-2xl font-bold text-red-700">{stats.critical + stats.high}</div>
                <div className="text-xs text-red-500 mt-1">
                  {stats.critical > 0 && `${stats.critical} Critical`}
                  {stats.critical > 0 && stats.high > 0 && ' • '}
                  {stats.high > 0 && `${stats.high} High`}
                </div>
            </div>
            <div className="bg-amber-50 border border-amber-100 p-4 rounded-xl">
                <div className="text-amber-600 font-medium text-sm mb-1">Warnings</div>
                <div className="text-2xl font-bold text-amber-700">{stats.medium}</div>
                <div className="text-xs text-amber-500 mt-1">Medium severity</div>
            </div>
            <div className="bg-blue-50 border border-blue-100 p-4 rounded-xl">
                <div className="text-blue-600 font-medium text-sm mb-1">In Progress</div>
                <div className="text-2xl font-bold text-blue-700">{stats.inProgress}</div>
                <div className="text-xs text-blue-500 mt-1">Being investigated</div>
            </div>
            <div className="bg-gray-50 border border-gray-100 p-4 rounded-xl">
                <div className="text-gray-600 font-medium text-sm mb-1">Low Priority</div>
                <div className="text-2xl font-bold text-gray-700">{stats.low}</div>
                <div className="text-xs text-gray-500 mt-1">Minor issues</div>
            </div>
        </div>

        {/* List Header */}
        <div className="flex justify-between items-center">
            <h3 className="font-bold text-gray-900">Active Exceptions</h3>
            <div className="flex gap-2">
                <button className="px-3 py-1.5 border border-gray-200 rounded-lg text-sm text-gray-600 flex items-center gap-2 hover:bg-gray-50">
                    <Filter className="w-4 h-4" /> Filter
                </button>
            </div>
        </div>

        {/* Exceptions List */}
        <div className="bg-white border border-gray-100 rounded-xl shadow-sm divide-y divide-gray-50">
            {allExceptions.length > 0 ? allExceptions.map(item => (
                <div key={item.id} className="p-5 hover:bg-gray-50 transition-colors group">
                    <div className="flex justify-between items-start">
                        <div className="flex gap-4">
                            <div className={`mt-1 p-2 rounded-lg ${
                                item.severity === 'critical' ? 'bg-red-100 text-red-600' :
                                item.severity === 'high' ? 'bg-red-100 text-red-600' :
                                item.severity === 'medium' ? 'bg-amber-100 text-amber-600' :
                                'bg-gray-100 text-gray-600'
                            }`}>
                                {item.type === 'rule_violation' ? (
                                    <Calculator className="w-5 h-5" />
                                ) : (
                                    <AlertTriangle className="w-5 h-5" />
                                )}
                            </div>
                            
                            <div>
                                <div className="flex items-center gap-2 mb-1 flex-wrap">
                                    <h4 className="font-bold text-gray-900">{item.description}</h4>
                                    <span className={`text-[10px] uppercase font-bold px-1.5 py-0.5 rounded ${
                                        item.severity === 'critical' ? 'bg-red-100 text-red-700' :
                                        item.severity === 'high' ? 'bg-red-100 text-red-700' :
                                        item.severity === 'medium' ? 'bg-amber-100 text-amber-700' :
                                        'bg-gray-100 text-gray-700'
                                    }`}>
                                        {item.severity}
                                    </span>
                                    <span className={`text-[10px] uppercase font-bold px-1.5 py-0.5 rounded ${
                                        item.type === 'rule_violation' ? 'bg-blue-100 text-blue-700' : 'bg-purple-100 text-purple-700'
                                    }`}>
                                        {item.type === 'rule_violation' ? 'RULE' : 'MATCH'}
                                    </span>
                                </div>
                                <p className="text-sm text-gray-600 mb-2">{item.notes}</p>
                                
                                {/* Show expected vs actual for rule violations */}
                                {item.type === 'rule_violation' && item.source_value && item.target_value && (
                                    <div className="flex items-center gap-3 mb-2 text-xs">
                                        <span className="text-gray-500">Expected:</span>
                                        <span className="font-mono font-medium text-gray-700">{item.source_value}</span>
                                        <span className="text-gray-400">→</span>
                                        <span className="text-gray-500">Actual:</span>
                                        <span className="font-mono font-medium text-amber-700">{item.target_value}</span>
                                    </div>
                                )}
                                
                                <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
                                    <div className="flex items-center gap-1">
                                        <FileText className="w-3 h-3" /> {item.source}
                                    </div>
                                    <div className="flex items-center gap-1">
                                        <Clock className="w-3 h-3" /> {item.created_at}
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div className="text-right shrink-0 ml-4">
                            {item.amount_difference && (
                                <>
                                    <div className="font-bold text-gray-900">
                                        ${typeof item.amount_difference === 'number' 
                                            ? item.amount_difference.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
                                            : item.amount_difference}
                                    </div>
                                    <div className="text-xs text-gray-500 uppercase font-medium mt-0.5">Variance</div>
                                </>
                            )}
                            
                            <button 
                                onClick={() => {
                                    // Navigate to rule configuration if it's a rule violation
                                    if (item.type === 'rule_violation' && item.originalData?.rule_id) {
                                        window.location.hash = `rule-configuration/${item.originalData.rule_id}`;
                                    }
                                }}
                                className="mt-3 text-sm font-medium text-blue-600 hover:text-blue-800 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-end gap-1 w-full"
                            >
                                {item.type === 'rule_violation' ? 'Review Rule' : 'Investigate'} <ArrowRight className="w-4 h-4" />
                            </button>
                        </div>
                    </div>
                </div>
            )) : (
                 <div className="p-8 text-center text-gray-500">
                    <div className="text-gray-400 mb-2">✅ No active exceptions found</div>
                    <div className="text-sm text-gray-500">All validations passing!</div>
                 </div>
            )}
        </div>
    </div>
  );
}
