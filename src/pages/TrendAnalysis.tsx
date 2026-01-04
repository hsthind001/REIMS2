/**
 * Trend Analysis Page
 * 
 * Comprehensive financial trend visualization dashboard
 */

import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import TrendAnalysisDashboard from '../components/charts/TrendAnalysisDashboard';
import { propertyService } from '../lib/property';
import { Card, Button } from '../components/design-system';
import { ArrowLeft } from 'lucide-react';
import type { Property } from '../types/api';

export default function TrendAnalysis() {
  const { propertyId } = useParams<{ propertyId?: string }>();
  const [properties, setProperties] = useState<Property[]>([]);
  const [selectedPropertyId, setSelectedPropertyId] = useState<number | undefined>(
    propertyId ? parseInt(propertyId) : undefined
  );
  const [months, setMonths] = useState<number>(12);
  const [selectedMetrics, setSelectedMetrics] = useState<('noi' | 'dscr' | 'occupancy' | 'revenue' | 'expenses')[]>([
    'noi',
    'dscr',
    'occupancy',
    'revenue'
  ]);

  useEffect(() => {
    loadProperties();
  }, []);

  const loadProperties = async () => {
    try {
      const data = await propertyService.getAllProperties();
      setProperties(data);
    } catch (error) {
      console.error('Failed to load properties:', error);
    }
  };

  return (
    <div className="min-h-screen bg-background p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => window.history.back()}
            className="mb-4 flex items-center gap-2"
          >
            <ArrowLeft className="w-4 h-4" />
            Back
          </Button>
          <h1 className="text-3xl font-bold mb-2">Financial Trend Analysis</h1>
          <p className="text-gray-600">
            Analyze trends over time for key financial metrics including NOI, DSCR, occupancy, and revenue
          </p>
        </div>

        {/* Filters */}
        <Card className="p-4 mb-6">
          <div className="flex flex-wrap gap-4 items-end">
            <div className="flex-1 min-w-[200px]">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Property
              </label>
              <select
                value={selectedPropertyId || ''}
                onChange={(e) => setSelectedPropertyId(e.target.value ? parseInt(e.target.value) : undefined)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">All Properties (Portfolio View)</option>
                {properties.map((prop) => (
                  <option key={prop.id} value={prop.id}>
                    {prop.property_name} ({prop.property_code})
                  </option>
                ))}
              </select>
            </div>

            <div className="min-w-[150px]">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Time Period
              </label>
              <select
                value={months}
                onChange={(e) => setMonths(parseInt(e.target.value))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value={6}>Last 6 months</option>
                <option value={12}>Last 12 months</option>
                <option value={24}>Last 24 months</option>
                <option value={36}>Last 36 months</option>
              </select>
            </div>

            <div className="flex-1 min-w-[300px]">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Metrics to Display
              </label>
              <div className="flex flex-wrap gap-2">
                {(['noi', 'dscr', 'occupancy', 'revenue', 'expenses'] as const).map((metric) => (
                  <label key={metric} className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={selectedMetrics.includes(metric)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedMetrics([...selectedMetrics, metric]);
                        } else {
                          setSelectedMetrics(selectedMetrics.filter(m => m !== metric));
                        }
                      }}
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <span className="text-sm capitalize">{metric}</span>
                  </label>
                ))}
              </div>
            </div>
          </div>
        </Card>

        {/* Trend Charts */}
        <TrendAnalysisDashboard
          propertyId={selectedPropertyId}
          months={months}
          metrics={selectedMetrics}
        />
      </div>
    </div>
  );
}
