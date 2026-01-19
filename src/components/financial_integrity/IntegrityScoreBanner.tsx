import React from 'react';
import { 
  CheckCircle2, 
  AlertTriangle, 
  Clock, 
  Activity, 
  Check, 
  ArrowRight 
} from 'lucide-react';
import { getStatusForScore } from './constants';

interface IntegrityScoreBannerProps {
  score: number;
  matchCount: number;
  discrepancyCount: number;
  timingCount: number;
  activeRulesCount: number;
  lastValidated?: string;
  onViewExceptions: () => void;
}

export default function IntegrityScoreBanner({
  score,
  matchCount,
  discrepancyCount,
  timingCount,
  activeRulesCount,
  lastValidated,
  onViewExceptions
}: IntegrityScoreBannerProps) {
  const hasData = matchCount > 0 || discrepancyCount > 0;
  const status = hasData ? getStatusForScore(score) : { color: 'gray', label: 'No Data' };
  
  // Calculate circumference for circular progress
  const radius = 58;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = hasData ? circumference - (score / 100) * circumference : circumference;

  return (
    <div className="bg-white rounded-2xl shadow-md border border-gray-100 overflow-hidden relative">
      <div className={`absolute top-0 inset-x-0 h-1 bg-gradient-to-r ${
          !hasData ? 'from-gray-200 via-gray-300 to-gray-200' :
          status.color === 'green' ? 'from-green-500 via-emerald-400 to-green-500' :
          status.color === 'blue' ? 'from-blue-500 via-cyan-400 to-blue-500' :
          status.color === 'amber' ? 'from-amber-500 via-yellow-400 to-amber-500' :
          'from-red-500 via-orange-400 to-red-500'
      }`} />
      
      <div className="p-8">
        <div className="flex flex-col lg:flex-row items-center gap-12">
          
          {/* Main Score Gauge */}
          <div className="relative flex-shrink-0">
            <svg className="w-40 h-40 transform -rotate-90">
              <circle
                cx="80"
                cy="80"
                r={radius}
                className="text-gray-100"
                strokeWidth="12"
                fill="none"
              />
              <circle
                cx="80"
                cy="80"
                r={radius}
                className={`transition-all duration-1000 ease-out ${
                    !hasData ? 'text-gray-300' :
                    status.color === 'green' ? 'text-green-500' :
                    status.color === 'blue' ? 'text-blue-500' :
                    status.color === 'amber' ? 'text-amber-500' :
                    'text-red-500'
                }`}
                strokeWidth="12"
                strokeDasharray={circumference}
                strokeDashoffset={strokeDashoffset}
                strokeLinecap="round"
                fill="none"
              />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
              <span className={`text-4xl font-bold tracking-tighter ${
                  !hasData ? 'text-gray-400' :
                  status.color === 'green' ? 'text-green-600' :
                  status.color === 'blue' ? 'text-blue-600' :
                  status.color === 'amber' ? 'text-amber-600' :
                  'text-red-600'
              }`}>
                {hasData ? `${score}%` : 'N/A'}
              </span>
              <span className="text-xs font-semibold uppercase tracking-wider text-gray-400 mt-1">Integrity</span>
            </div>
            
            {/* Decorative glow */}
            {hasData && <div className={`absolute inset-0 bg-${status.color}-500/10 blur-3xl -z-10 rounded-full`} />}
          </div>

          {/* Metrics Grid */}
          <div className="flex-1 grid grid-cols-2 md:grid-cols-4 gap-6 w-full">
            <div className="p-4 rounded-xl bg-gray-50 border border-gray-100 hover:border-gray-200 transition-colors">
              <div className="flex items-center gap-2 mb-2 text-gray-500">
                <CheckCircle2 className="w-4 h-4 text-green-500" />
                <span className="text-sm font-medium">Perfect Matches</span>
              </div>
              <div className="text-2xl font-bold text-gray-900">{matchCount}</div>
              <div className="text-xs text-green-600 flex items-center mt-1">
                 <Activity className="w-3 h-3 mr-1" /> Verified
              </div>
            </div>

            <div 
                className="p-4 rounded-xl bg-amber-50/50 border border-amber-100 hover:border-amber-200 transition-colors cursor-pointer group"
                onClick={onViewExceptions}
            >
              <div className="flex items-center gap-2 mb-2 text-gray-500">
                <AlertTriangle className="w-4 h-4 text-amber-500" />
                <span className="text-sm font-medium text-amber-900">Needs Review</span>
              </div>
              <div className="text-2xl font-bold text-amber-700">{discrepancyCount}</div>
              <div className="text-xs text-amber-600 flex items-center mt-1 group-hover:underline">
                 View items <ArrowRight className="w-3 h-3 ml-1" />
              </div>
            </div>

            <div className="p-4 rounded-xl bg-blue-50/50 border border-blue-100 hover:border-blue-200 transition-colors">
              <div className="flex items-center gap-2 mb-2 text-gray-500">
                <Clock className="w-4 h-4 text-blue-500" />
                <span className="text-sm font-medium text-blue-900">Timing Diffs</span>
              </div>
              <div className="text-2xl font-bold text-blue-700">{timingCount}</div>
              <div className="text-xs text-blue-600 flex items-center mt-1">
                 Expected variance
              </div>
            </div>

            <div className="p-4 rounded-xl bg-gray-50 border border-gray-100">
               <div className="flex items-center gap-2 mb-2 text-gray-500">
                <Activity className="w-4 h-4 text-gray-400" />
                <span className="text-sm font-medium">Rules Active</span>
              </div>
              <div className="text-2xl font-bold text-gray-900">{activeRulesCount}</div>
              <div className="text-xs text-gray-500 flex items-center mt-1">
                 Calculated rules
              </div>
            </div>
          </div>
        </div>

        {/* Footer Status Message */}
        <div className="mt-8 pt-6 border-t border-gray-100 flex flex-col md:flex-row items-center justify-between text-sm text-gray-500">
          <div className="flex items-center gap-2">
            <span className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${
                status.color === 'green' ? 'bg-green-50 text-green-700 border-green-200' :
                status.color === 'blue' ? 'bg-blue-50 text-blue-700 border-blue-200' :
                status.color === 'amber' ? 'bg-amber-50 text-amber-700 border-amber-200' :
                'bg-red-50 text-red-700 border-red-200'
            }`}>
              {status.color === 'green' ? <Check className="w-3 h-3" /> : <AlertTriangle className="w-3 h-3" />}
              {status.label} Status
            </span>
            <span className="hidden md:inline text-gray-300">|</span>
            <span className="hidden md:inline">
                reconciliation complete. {discrepancyCount} items require specific attention.
            </span>
          </div>
          
          {lastValidated && (
            <div className="flex items-center gap-1.5 mt-2 md:mt-0">
               <Clock className="w-3.5 h-3.5 text-gray-400" />
               Last validated {new Date(lastValidated).toLocaleTimeString()}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
