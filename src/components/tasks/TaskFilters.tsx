/**
 * TaskFilters Component
 * 
 * Provides filtering and search functionality for tasks
 */

import { Card, Button } from '../design-system'
import { Filter, X, Search } from 'lucide-react'
import type { Task } from '../../types/tasks'

interface TaskFiltersProps {
  filter: {
    type: string;
    status: string;
    property: string;
    search: string;
    dateFrom: string;
    dateTo: string;
  };
  onFilterChange: (filter: any) => void;
  onClear: () => void;
  availableProperties?: string[];
}

export function TaskFilters({ filter, onFilterChange, onClear, availableProperties = [] }: TaskFiltersProps) {
  const taskTypes = [
    { value: 'all', label: 'All Types' },
    { value: 'document_extraction', label: 'Document Extraction' },
    { value: 'anomaly_detection', label: 'Anomaly Detection' },
    { value: 'recovery', label: 'Recovery' },
    { value: 'email', label: 'Email' },
    { value: 'batch_processing', label: 'Batch Processing' },
    { value: 'other', label: 'Other' }
  ];

  const statuses = [
    { value: 'all', label: 'All Statuses' },
    { value: 'PENDING', label: 'Pending' },
    { value: 'PROCESSING', label: 'Processing' },
    { value: 'SUCCESS', label: 'Success' },
    { value: 'FAILURE', label: 'Failed' },
    { value: 'REVOKED', label: 'Cancelled' }
  ];

  const hasActiveFilters = filter.type !== 'all' || 
    filter.status !== 'all' || 
    filter.property !== 'all' || 
    filter.search !== '' || 
    filter.dateFrom !== '' || 
    filter.dateTo !== '';

  return (
    <Card className="p-4">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Filter className="w-5 h-5 text-text-secondary" />
          <h3 className="font-semibold">Filters & Search</h3>
        </div>
        {hasActiveFilters && (
          <Button
            variant="default"
            size="sm"
            icon={<X className="w-4 h-4" />}
            onClick={onClear}
          >
            Clear Filters
          </Button>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {/* Search */}
        <div>
          <label className="block text-sm font-medium mb-1">Search</label>
          <div className="relative">
            <Search className="absolute left-2 top-1/2 transform -translate-y-1/2 w-4 h-4 text-text-secondary" />
            <input
              type="text"
              placeholder="Task ID, document name..."
              value={filter.search}
              onChange={(e) => onFilterChange({ ...filter, search: e.target.value })}
              className="w-full pl-8 pr-3 py-2 border border-border rounded bg-surface text-text-primary"
            />
          </div>
        </div>

        {/* Task Type */}
        <div>
          <label className="block text-sm font-medium mb-1">Task Type</label>
          <select
            value={filter.type}
            onChange={(e) => onFilterChange({ ...filter, type: e.target.value })}
            className="w-full px-3 py-2 border border-border rounded bg-surface text-text-primary"
          >
            {taskTypes.map((type) => (
              <option key={type.value} value={type.value}>
                {type.label}
              </option>
            ))}
          </select>
        </div>

        {/* Status */}
        <div>
          <label className="block text-sm font-medium mb-1">Status</label>
          <select
            value={filter.status}
            onChange={(e) => onFilterChange({ ...filter, status: e.target.value })}
            className="w-full px-3 py-2 border border-border rounded bg-surface text-text-primary"
          >
            {statuses.map((status) => (
              <option key={status.value} value={status.value}>
                {status.label}
              </option>
            ))}
          </select>
        </div>

        {/* Property */}
        {availableProperties.length > 0 && (
          <div>
            <label className="block text-sm font-medium mb-1">Property</label>
            <select
              value={filter.property}
              onChange={(e) => onFilterChange({ ...filter, property: e.target.value })}
              className="w-full px-3 py-2 border border-border rounded bg-surface text-text-primary"
            >
              <option value="all">All Properties</option>
              {availableProperties.map((prop) => (
                <option key={prop} value={prop}>
                  {prop}
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Date From */}
        <div>
          <label className="block text-sm font-medium mb-1">Date From</label>
          <input
            type="date"
            value={filter.dateFrom}
            onChange={(e) => onFilterChange({ ...filter, dateFrom: e.target.value })}
            className="w-full px-3 py-2 border border-border rounded bg-surface text-text-primary"
          />
        </div>

        {/* Date To */}
        <div>
          <label className="block text-sm font-medium mb-1">Date To</label>
          <input
            type="date"
            value={filter.dateTo}
            onChange={(e) => onFilterChange({ ...filter, dateTo: e.target.value })}
            className="w-full px-3 py-2 border border-border rounded bg-surface text-text-primary"
          />
        </div>
      </div>
    </Card>
  );
}

