/**
 * Reconciliation Filters Component
 * 
 * Left rail filters for the reconciliation cockpit
 */
import { useState } from 'react';
import { Filter, X } from 'lucide-react';
import { Card, Button } from '../design-system';

interface ReconciliationFiltersProps {
  properties: any[];
  periods: any[];
  selectedPropertyId: number | null;
  selectedPeriodId: number | null;
  onPropertyChange: (propertyId: number | null) => void;
  onPeriodChange: (periodId: number | null) => void;
  onSeverityFilter: (severity: string) => void;
  onTierFilter: (tier: string) => void;
  onNeedsMeFilter: (needsMe: boolean) => void;
  onCommitteeFilter: (committeeId: number | null) => void;
  onSLAFilter: (slaDue: boolean) => void;
  severityFilter: string;
  tierFilter: string;
  needsMe: boolean;
  committeeId: number | null;
  slaDue: boolean;
}

export default function ReconciliationFilters({
  properties,
  periods,
  selectedPropertyId,
  selectedPeriodId,
  onPropertyChange,
  onPeriodChange,
  onSeverityFilter,
  onTierFilter,
  onNeedsMeFilter,
  onCommitteeFilter,
  onSLAFilter,
  severityFilter,
  tierFilter,
  needsMe,
  committeeId,
  slaDue
}: ReconciliationFiltersProps) {
  const [isExpanded, setIsExpanded] = useState(true);

  const clearFilters = () => {
    onSeverityFilter('all');
    onTierFilter('all');
    onNeedsMeFilter(false);
    onCommitteeFilter(null);
    onSLAFilter(false);
  };

  const hasActiveFilters = severityFilter !== 'all' || tierFilter !== 'all' || needsMe || committeeId !== null || slaDue;

  return (
    <Card className="p-4">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Filter className="w-5 h-5 text-gray-600" />
          <h3 className="text-lg font-semibold text-gray-900">Filters</h3>
        </div>
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="text-gray-600 hover:text-gray-900"
        >
          {isExpanded ? '−' : '+'}
        </button>
      </div>

      {isExpanded && (
        <div className="space-y-4">
          {/* Property Filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Property
            </label>
            <select
              value={selectedPropertyId || ''}
              onChange={(e) => onPropertyChange(e.target.value ? parseInt(e.target.value) : null)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
            >
              <option value="">All Properties</option>
              {properties.map(prop => (
                <option key={prop.id} value={prop.id}>
                  {prop.name || `Property ${prop.id}`}
                </option>
              ))}
            </select>
          </div>

          {/* Period Filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Period
            </label>
            <select
              value={selectedPeriodId || ''}
              onChange={(e) => onPeriodChange(e.target.value ? parseInt(e.target.value) : null)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
              disabled={!selectedPropertyId}
            >
              <option value="">All Periods</option>
              {periods.map(period => (
                <option key={period.id} value={period.id}>
                  {period.period_month}/{period.period_year}
                </option>
              ))}
            </select>
          </div>

          {/* Severity Filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Severity
            </label>
            <select
              value={severityFilter}
              onChange={(e) => onSeverityFilter(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
            >
              <option value="all">All Severities</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
          </div>

          {/* Tier Filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Exception Tier
            </label>
            <select
              value={tierFilter}
              onChange={(e) => onTierFilter(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
            >
              <option value="all">All Tiers</option>
              <option value="tier_0_auto_close">Tier 0: Auto-Close</option>
              <option value="tier_1_auto_suggest">Tier 1: Auto-Suggest</option>
              <option value="tier_2_route">Tier 2: Route</option>
              <option value="tier_3_escalate">Tier 3: Escalate</option>
            </select>
          </div>

          {/* Needs Me Filter */}
          <div>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={needsMe}
                onChange={(e) => onNeedsMeFilter(e.target.checked)}
                className="rounded border-gray-300"
              />
              <span className="text-sm font-medium text-gray-700">Needs My Review</span>
            </label>
          </div>

          {/* SLA Due Filter */}
          <div>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={slaDue}
                onChange={(e) => onSLAFilter(e.target.checked)}
                className="rounded border-gray-300"
              />
              <span className="text-sm font-medium text-gray-700">SLA Due</span>
            </label>
          </div>

          {/* Clear Filters */}
          {hasActiveFilters && (
            <Button
              variant="secondary"
              size="sm"
              onClick={clearFilters}
              className="w-full"
              icon={<X className="w-4 h-4" />}
            >
              Clear Filters
            </Button>
          )}
        </div>
      )}
    </Card>
  );
}

