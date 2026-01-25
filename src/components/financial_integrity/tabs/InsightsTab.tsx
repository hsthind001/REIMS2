import React from 'react';
import { 
  Lightbulb, 
  TrendingUp, 
  ArrowRight,
  Target,
  Zap,
  CheckCircle2
} from 'lucide-react';

export default function InsightsTab() {
  
  // Mock Insights Data
  const insights = [
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
            <Lightbulb className="w-4 h-4" /> AI Analysis
          </div>
          <h2 className="text-2xl font-bold mb-3">Reconciliation Efficiency up 12%</h2>
          <p className="text-blue-100 max-w-xl leading-relaxed mb-6">
            Based on recent activity, the automated rules for "Bank Statements" are performing exceptionally well. 
            However, "Rent Roll" reconciliations require manual review 35% of the time, often due to unit mapping issues.
          </p>
          <button className="bg-white text-blue-600 px-5 py-2.5 rounded-lg font-bold text-sm hover:bg-blue-50 transition-colors shadow-sm">
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
