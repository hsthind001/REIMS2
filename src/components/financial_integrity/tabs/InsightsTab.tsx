import React, { useMemo } from 'react';
import { 
  Lightbulb, 
  TrendingUp, 
  ArrowRight,
  Target,
  Zap,
  CheckCircle2,
  FileText
} from 'lucide-react';

interface InsightsTabProps {
  calculatedRules?: any[];
  matches?: any[];
  discrepancies?: any[];
}

export default function InsightsTab({ calculatedRules = [], matches = [], discrepancies = [] }: InsightsTabProps) {
  
  // Calculate Reconciliation Efficiency
  const efficiency = useMemo(() => {
    if (!calculatedRules || calculatedRules.length === 0) {
      return { rate: 0, change: 0, trend: 'neutral' as const };
    }

    const totalRules = calculatedRules.length;
    const passedRules = calculatedRules.filter(r => r.status === 'PASS').length;
    const currentRate = (passedRules / totalRules) * 100;

    // Mock historical comparison for trend (in real app, would compare with prior period)
    // Assuming average baseline of 82% efficiency
    const baselineRate = 82;
    const change = currentRate - baselineRate;

    return {
      rate: Math.round(currentRate * 10) / 10, // Round to 1 decimal
      change: Math.round(change * 10) / 10,
      trend: change > 0 ? 'up' as const : change < 0 ? 'down' as const : 'neutral' as const
    };
  }, [calculatedRules]);

  // Analyze document types for insights
  const documentInsights = useMemo(() => {
    const docTypes: Record<string, { passed: number, failed: number, total: number }> = {};

    calculatedRules.forEach(rule => {
      const ruleId = rule.rule_id || '';
      let docType = 'Unknown';
      
      if (ruleId.startsWith('BS-')) docType = 'Balance Sheet';
      else if (ruleId.startsWith('IS-')) docType = 'Income Statement';
      else if (ruleId.startsWith('CF-')) docType = 'Cash Flow';
      else if (ruleId.startsWith('RR-')) docType = 'Rent Roll';
      else if (ruleId.startsWith('MST-')) docType = 'Mortgage Statement';

      if (!docTypes[docType]) {
        docTypes[docType] = { passed: 0, failed: 0, total: 0 };
      }

      docTypes[docType].total++;
      if (rule.status === 'PASS') {
        docTypes[docType].passed++;
      } else {
        docTypes[docType].failed++;
      }
    });

    // Find best and worst performing
    const entries = Object.entries(docTypes);
    const best = entries.reduce((max, [type, stats]) => {
      const rate = stats.total > 0 ? (stats.passed / stats.total) * 100 : 0;
      const maxRate = max.stats.total > 0 ? (max.stats.passed / max.stats.total) * 100 : 0;
      return rate > maxRate ? { type, stats } : max;
    }, { type: '', stats: { passed: 0, failed: 0, total: 0 } });

    const worst = entries.reduce((min, [type, stats]) => {
      const rate = stats.total > 0 ? (stats.passed / stats.total) * 100 : 100;
      const minRate = min.stats.total > 0 ? (min.stats.passed / min.stats.total) * 100 : 100;
      return rate < minRate && stats.total > 0 ? { type, stats } : min;
    }, { type: '', stats: { passed: 0, failed: 0, total: 0 } });

    return { best, worst, docTypes };
  }, [calculatedRules]);

  // Generate dynamic insights
  const generateInsights = () => {
    const insights = [];

    // Best performing document
    if (documentInsights.best.type && documentInsights.best.stats.total > 0) {
      const rate = Math.round((documentInsights.best.stats.passed / documentInsights.best.stats.total) * 100);
      insights.push({
        id: 'INS-BEST',
        title: `${documentInsights.best.type} Performing Excellently`,
        type: 'success',
        description: `${documentInsights.best.type} rules are passing at ${rate}% (${documentInsights.best.stats.passed}/${documentInsights.best.stats.total}). The automated validation is working exceptionally well for this document type.`,
        impact: 'Low',
        action: 'View Rules',
        icon: CheckCircle2,
        color: 'bg-green-100 text-green-600'
      });
    }

    // Worst performing document (if significant issues)
    if (documentInsights.worst.type && documentInsights.worst.stats.total > 0) {
      const rate = Math.round((documentInsights.worst.stats.passed / documentInsights.worst.stats.total) * 100);
      if (rate < 85) {
        insights.push({
          id: 'INS-WORST',
          title: `${documentInsights.worst.type} Needs Attention`,
          type: 'pattern',
          description: `${documentInsights.worst.type} has a ${rate}% pass rate (${documentInsights.worst.stats.passed}/${documentInsights.worst.stats.total}). ${documentInsights.worst.stats.failed} rules require manual review. Consider reviewing validation logic or data quality.`,
          impact: rate < 70 ? 'High' : 'Medium',
          action: 'Review Rules',
          icon: Target,
          color: 'bg-purple-100 text-purple-600'
        });
      }
    }

    // Discrepancies insight
    if (discrepancies && discrepancies.length > 0) {
      const highSeverity = discrepancies.filter((d: any) => d.severity === 'high' || d.severity === 'critical').length;
      if (highSeverity > 0) {
        insights.push({
          id: 'INS-DISCREPANCY',
          title: `${highSeverity} Critical Discrepancies Found`,
          type: 'optimization',
          description: `There are ${highSeverity} high-severity discrepancies requiring immediate attention. Review these items to ensure data accuracy and completeness.`,
          impact: 'High',
          action: 'View Exceptions',
          icon: Zap,
          color: 'bg-blue-100 text-blue-600'
        });
      }
    }

    // If no dynamic insights, add a default success message
    if (insights.length === 0) {
      insights.push({
        id: 'INS-DEFAULT',
        title: 'System Operating Normally',
        type: 'success',
        description: 'All validation rules are executing as expected. No significant issues detected in the current period.',
        impact: 'Low',
        action: 'View Details',
        icon: CheckCircle2,
        color: 'bg-green-100 text-green-600'
      });
    }

    return insights;
  };

  const insights = generateInsights();
  
  // Handler for optimization report
  const handleViewOptimizationReport = () => {
    // Generate report data
    const reportData = {
      efficiency: efficiency.rate,
      trend: efficiency.change,
      totalRules: calculatedRules.length,
      passedRules: calculatedRules.filter(r => r.status === 'PASS').length,
      failedRules: calculatedRules.filter(r => r.status !== 'PASS').length,
      documentPerformance: documentInsights.docTypes,
      criticalIssues: discrepancies.filter((d: any) => d.severity === 'high' || d.severity === 'critical').length,
      totalMatches: matches.length,
      totalDiscrepancies: discrepancies.length
    };

    // Create a detailed report view
    const reportWindow = window.open('', '_blank');
    if (reportWindow) {
      reportWindow.document.write(`
        <!DOCTYPE html>
        <html>
        <head>
          <title>Reconciliation Optimization Report</title>
          <style>
            body {
              font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
              max-width: 900px;
              margin: 40px auto;
              padding: 20px;
              background: #f5f5f5;
            }
            .header {
              background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
              color: white;
              padding: 30px;
              border-radius: 12px;
              margin-bottom: 30px;
            }
            .header h1 {
              margin: 0 0 10px 0;
              font-size: 32px;
            }
            .header p {
              margin: 0;
              opacity: 0.9;
            }
            .metric-card {
              background: white;
              padding: 24px;
              border-radius: 12px;
              margin-bottom: 20px;
              box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }
            .metric-card h2 {
              margin: 0 0 16px 0;
              font-size: 18px;
              color: #333;
            }
            .metric-value {
              font-size: 48px;
              font-weight: bold;
              color: #667eea;
              margin: 10px 0;
            }
            .metric-label {
              color: #666;
              font-size: 14px;
            }
            .doc-table {
              width: 100%;
              border-collapse: collapse;
              margin-top: 16px;
            }
            .doc-table th, .doc-table td {
              padding: 12px;
              text-align: left;
              border-bottom: 1px solid #eee;
            }
            .doc-table th {
              background: #f8f9fa;
              font-weight: 600;
              color: #333;
            }
            .success { color: #10b981; }
            .warning { color: #f59e0b; }
            .error { color: #ef4444; }
            @media print {
              body { background: white; }
              .no-print { display: none; }
            }
          </style>
        </head>
        <body>
          <div class="header">
            <h1>📊 Reconciliation Optimization Report</h1>
            <p>Generated: ${new Date().toLocaleString()}</p>
          </div>

          <div class="metric-card">
            <h2>Overall Efficiency</h2>
            <div class="metric-value">${efficiency.rate}%</div>
            <div class="metric-label">
              ${efficiency.change > 0 ? '↗' : efficiency.change < 0 ? '↘' : '→'} 
              ${Math.abs(efficiency.change)}% vs baseline
            </div>
          </div>

          <div class="metric-card">
            <h2>Rule Validation Summary</h2>
            <table class="doc-table">
              <tr>
                <td><strong>Total Rules:</strong></td>
                <td>${reportData.totalRules}</td>
              </tr>
              <tr>
                <td><strong>Passed:</strong></td>
                <td class="success">${reportData.passedRules}</td>
              </tr>
              <tr>
                <td><strong>Failed/Warnings:</strong></td>
                <td class="warning">${reportData.failedRules}</td>
              </tr>
              <tr>
                <td><strong>Pass Rate:</strong></td>
                <td>${reportData.totalRules > 0 ? Math.round((reportData.passedRules / reportData.totalRules) * 100) : 0}%</td>
              </tr>
            </table>
          </div>

          <div class="metric-card">
            <h2>Document Performance Breakdown</h2>
            <table class="doc-table">
              <thead>
                <tr>
                  <th>Document Type</th>
                  <th>Total Rules</th>
                  <th>Passed</th>
                  <th>Failed</th>
                  <th>Pass Rate</th>
                </tr>
              </thead>
              <tbody>
                ${Object.entries(reportData.documentPerformance).map(([type, stats]: [string, any]) => {
                  const rate = stats.total > 0 ? Math.round((stats.passed / stats.total) * 100) : 0;
                  const statusClass = rate >= 90 ? 'success' : rate >= 70 ? 'warning' : 'error';
                  return `
                    <tr>
                      <td><strong>${type}</strong></td>
                      <td>${stats.total}</td>
                      <td class="success">${stats.passed}</td>
                      <td class="${stats.failed > 0 ? 'warning' : ''}">${stats.failed}</td>
                      <td class="${statusClass}">${rate}%</td>
                    </tr>
                  `;
                }).join('')}
              </tbody>
            </table>
          </div>

          <div class="metric-card">
            <h2>Reconciliation Results</h2>
            <table class="doc-table">
              <tr>
                <td><strong>Successful Matches:</strong></td>
                <td class="success">${reportData.totalMatches}</td>
              </tr>
              <tr>
                <td><strong>Discrepancies:</strong></td>
                <td class="warning">${reportData.totalDiscrepancies}</td>
              </tr>
              <tr>
                <td><strong>Critical Issues:</strong></td>
                <td class="error">${reportData.criticalIssues}</td>
              </tr>
            </table>
          </div>

          <div class="metric-card no-print">
            <button onclick="window.print()" style="
              background: #667eea;
              color: white;
              border: none;
              padding: 12px 24px;
              border-radius: 6px;
              font-weight: bold;
              cursor: pointer;
              font-size: 14px;
            ">Print Report</button>
          </div>
        </body>
        </html>
      `);
      reportWindow.document.close();
    }
  };

  // Mock Insights Data (kept as fallback)
  const fallbackInsights = [
    {
      id: 'INS-001',
      title: 'Recurring Variance in Rent Roll',
      type: 'pattern',
      description: 'Unit 304 consistently shows a $50 variance in the last 3 periods. This suggests a potential lease abstraction error or recurring mismatch in charge codes.',
      impact: 'High',
      action: 'Review Lease Terms',
      icon: Target,
      color: 'bg-purple-100 text-purple-600'
    },
    {
      id: 'INS-002',
      title: 'Mortgage Payment Timing Optimization',
      type: 'optimization',
      description: 'Mortgage payments are consistently recognized 2 days later in the GL compared to the Bank Statement. Adjusting the GL recognition logic could improve automated reconciliation rates by 15%.',
      impact: 'Medium',
      action: 'Adjust GL Logic',
      icon: Zap,
      color: 'bg-blue-100 text-blue-600'
    },
    {
      id: 'INS-003',
      title: 'Depreciation Accuracy',
      type: 'success',
      description: 'Fixed Asset depreciation calculations have matched 100% for the last 6 months. No manual intervention required.',
      impact: 'Low',
      action: 'View History',
      icon: CheckCircle2,
      color: 'bg-green-100 text-green-600'
    }
  ];

  return (
    <div className="space-y-6">
      {/* Hero Insight */}
      <div className="bg-gradient-to-r from-blue-600 to-indigo-700 rounded-2xl p-6 text-white shadow-lg relative overflow-hidden">
        <div className="absolute top-0 right-0 p-8 opacity-10">
          <Lightbulb className="w-32 h-32" />
        </div>
        <div className="relative z-10">
          <div className="flex items-center gap-2 mb-2 text-blue-100 font-medium text-sm uppercase tracking-wide">
            <Lightbulb className="w-4 h-4" /> {calculatedRules.length > 0 ? 'AI Analysis' : 'System Status'}
          </div>
          <h2 className="text-2xl font-bold mb-3">
            {calculatedRules.length > 0 ? (
              <>
                Reconciliation Efficiency {efficiency.trend === 'up' ? 'up' : efficiency.trend === 'down' ? 'down' : 'at'} {Math.abs(efficiency.change)}%
              </>
            ) : (
              'Ready to Analyze Reconciliation Data'
            )}
          </h2>
          <p className="text-blue-100 max-w-xl leading-relaxed mb-6">
            {calculatedRules.length > 0 ? (
              <>
                Current system efficiency is at <strong>{efficiency.rate}%</strong> with {calculatedRules.filter(r => r.status === 'PASS').length} out of {calculatedRules.length} rules passing. 
                {documentInsights.best.type && ` ${documentInsights.best.type} is performing exceptionally well.`}
                {documentInsights.worst.type && documentInsights.worst.stats.failed > 0 && ` ${documentInsights.worst.type} may need attention.`}
              </>
            ) : (
              'Run validation and reconciliation to generate insights and optimization recommendations based on your financial data.'
            )}
          </p>
          <button 
            onClick={handleViewOptimizationReport}
            disabled={calculatedRules.length === 0}
            className="bg-white text-blue-600 px-5 py-2.5 rounded-lg font-bold text-sm hover:bg-blue-50 transition-colors shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <FileText className="w-4 h-4 inline-block mr-2" />
            View Optimization Report
          </button>
        </div>
      </div>

      {/* Recommended Actions */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-gray-900 flex items-center gap-2">
              <Zap className="w-5 h-5 text-amber-500" /> Key Insights
            </h3>
          </div>

          <div className="space-y-4">
            {insights.map(insight => (
              <div key={insight.id} className="bg-white border border-gray-100 rounded-xl p-5 shadow-sm hover:shadow-md transition-shadow group">
                <div className="flex gap-4">
                  <div className={`mt-1 p-3 rounded-xl h-fit ${insight.color}`}>
                    <insight.icon className="w-6 h-6" />
                  </div>
                  <div className="flex-1">
                    <div className="flex justify-between items-start mb-1">
                      <h4 className="font-bold text-gray-900 text-lg">{insight.title}</h4>
                      <span className={`text-xs font-bold px-2 py-0.5 rounded uppercase ${
                        insight.impact === 'High' ? 'bg-red-50 text-red-600' : 
                        insight.impact === 'Medium' ? 'bg-amber-50 text-amber-600' : 'bg-green-50 text-green-600'
                      }`}>
                        {insight.impact}
                      </span>
                    </div>
                    
                    <p className="text-gray-600 text-sm leading-relaxed mb-4">
                      {insight.description}
                    </p>

                    <button className="text-sm font-bold text-blue-600 group-hover:text-blue-800 flex items-center gap-1 transition-colors">
                      {insight.action} <ArrowRight className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Trends Chart Mockup */}
        <div className="space-y-4">
          <h3 className="font-bold text-gray-900 flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-blue-600" /> Efficiency Trends
          </h3>
          
          <div className="bg-white border border-gray-100 rounded-xl p-6 shadow-sm h-full max-h-[500px] flex flex-col">
             <div className="flex items-end justify-between mb-8">
                <div>
                   <div className="text-3xl font-bold text-gray-900">94.2%</div>
                   <div className="text-sm text-gray-500">Average Accuracy Score</div>
                </div>
                <div className="flex items-center gap-1 text-green-600 bg-green-50 px-2 py-1 rounded text-sm font-medium">
                   <TrendingUp className="w-4 h-4" /> +2.4%
                </div>
             </div>

             {/* Mock Bar Chart */}
             <div className="flex-1 flex items-end justify-between gap-2 px-2 min-h-[280px]">
                {[45, 60, 55, 70, 65, 80, 75, 85, 90, 88, 92, 94].map((h, i) => (
                   <div key={i} className="w-full relative group">
                      <div 
                        className="bg-blue-500 hover:bg-blue-600 transition-colors rounded-t-md w-full relative group-hover:shadow-lg"
                        style={{ height: `${h}%` }}
                      ></div>
                      {/* Tooltip */}
                      <div className="opacity-0 group-hover:opacity-100 absolute -top-10 left-1/2 -translate-x-1/2 bg-gray-900 text-white text-xs py-1 px-2 rounded whitespace-nowrap z-10 transition-opacity pointer-events-none">
                         {h}% Accuracy
                      </div>
                   </div>
                ))}
             </div>
             <div className="flex justify-between mt-3 text-xs text-gray-400 font-medium border-t border-gray-100 pt-3">
                <span>Jan</span>
                <span>Feb</span>
                <span>Mar</span>
                <span>Apr</span>
                <span>May</span>
                <span>Jun</span>
                <span>Jul</span>
                <span>Aug</span>
                <span>Sep</span>
                <span>Oct</span>
                <span>Nov</span>
                <span>Dec</span>
             </div>
          </div>
        </div>
      </div>
    </div>
  );
}
