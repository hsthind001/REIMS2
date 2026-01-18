import { useState } from 'react';
// Note: We are using hash routing in App.tsx not react-router, so we'll just use window.location
import { Button, Card, Input, Select } from '../components/ui';
import { propertyService } from '../lib/property';
import type { PropertyCreate } from '../types/api';
import { ArrowLeft } from 'lucide-react';

export default function AddProperty() {
  const [formData, setFormData] = useState<PropertyCreate>({
    property_code: '',
    property_name: '',
    property_type: '',
    address: '',
    city: '',
    state: '',
    zip_code: '',
    country: 'USA',
    total_area_sqft: undefined,
    acquisition_date: '',
    ownership_structure: '',
    status: 'active',
    notes: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Helper to handle navigation since we use hash routing
  const navigate = (path: string) => {
    window.location.hash = path;
  };

  const formatErrorMessage = (error: any): string => {
    if (typeof error === 'string') return error;
    if (error instanceof Error) return error.message;
    if (error?.detail) {
      if (typeof error.detail === 'string') return error.detail;
      if (Array.isArray(error.detail)) return error.detail.map((e: any) => e.msg).join('; ');
    }
    return 'Unknown error';
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      // Ensure property_code is uppercase and matches format
      const normalizedCode = formData.property_code.toUpperCase().trim();
      const codePattern = /^[A-Z]{2,5}\d{3}$/;
      
      if (!codePattern.test(normalizedCode)) {
        setError('Property code must be 2-5 uppercase letters followed by 3 digits (e.g., ESP001, TES121)');
        setLoading(false);
        return;
      }

      const submitData = {
        ...formData,
        property_code: normalizedCode
      };

      await propertyService.createProperty(submitData);
      // Navigate back to properties list on success
      navigate(''); // Opens specific property or just list? Usually properties list.
      // Actually we probably want to go to the new property details or just the list.
      // Let's go to properties list for now.
      window.location.hash = 'properties'; 
    } catch (err: any) {
      setError(formatErrorMessage(err) || 'Operation failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="flex items-center gap-4 mb-6">
        <Button variant="ghost" onClick={() => navigate('properties')}>
          <ArrowLeft className="w-5 h-5 mr-2" />
          Back to Properties
        </Button>
        <h1 className="text-3xl font-bold text-text-primary">Add New Property</h1>
      </div>

      <Card className="p-8">
        {error && (
          <div className="mb-6 p-4 bg-danger-light text-danger rounded-lg border border-danger/20">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            <div>
              <Input
                label="Property Code *"
                required
                value={formData.property_code}
                onChange={(e) => {
                  const value = e.target.value.toUpperCase().replace(/\s/g, '');
                  setFormData({ ...formData, property_code: value });
                }}
                placeholder="ESP001"
                helperText="Format: 2-5 uppercase letters followed by 3 digits"
                fullWidth
              />
            </div>

            <div>
              <Input
                label="Property Name *"
                required
                value={formData.property_name}
                onChange={(e) => setFormData({ ...formData, property_name: e.target.value })}
                placeholder="e.g. Sunset Apartments"
                fullWidth
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            <div>
              <Select
                label="Property Type"
                value={formData.property_type}
                onChange={(val) => setFormData({ ...formData, property_type: val })}
                options={[
                  { value: 'Retail', label: 'Retail' },
                  { value: 'Office', label: 'Office' },
                  { value: 'Industrial', label: 'Industrial' },
                  { value: 'Mixed Use', label: 'Mixed Use' },
                  { value: 'Multifamily', label: 'Multifamily' },
                  { value: 'Commercial', label: 'Commercial' },
                ]}
                placeholder="Select type..."
              />
            </div>

            <div>
              <Input
                label="Total Area (sqft)"
                type="number"
                value={formData.total_area_sqft || ''}
                onChange={(e) => setFormData({ ...formData, total_area_sqft: e.target.value ? Number(e.target.value) : undefined })}
                min={0}
                placeholder="e.g. 50000"
                fullWidth
              />
            </div>
          </div>

          <div className="mb-6">
            <Input
              label="Address"
              value={formData.address}
              onChange={(e) => setFormData({ ...formData, address: e.target.value })}
              placeholder="e.g. 123 Main St"
              fullWidth
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-6">
            <div>
              <Input
                label="City"
                value={formData.city}
                onChange={(e) => setFormData({ ...formData, city: e.target.value })}
                placeholder="e.g. New York"
                fullWidth
              />
            </div>

            <div>
              <Input
                label="State"
                value={formData.state}
                onChange={(e) => setFormData({ ...formData, state: e.target.value })}
                maxLength={2}
                placeholder="e.g. NY"
                fullWidth
              />
            </div>

            <div>
              <Input
                label="ZIP Code"
                value={formData.zip_code}
                onChange={(e) => setFormData({ ...formData, zip_code: e.target.value })}
                placeholder="e.g. 10001"
                fullWidth
              />
            </div>

            <div>
              <Input
                label="Country"
                value={formData.country}
                onChange={(e) => setFormData({ ...formData, country: e.target.value })}
                placeholder="e.g. USA"
                fullWidth
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            <div>
              <Input
                label="Acquisition Date"
                type="date"
                value={formData.acquisition_date}
                onChange={(e) => setFormData({ ...formData, acquisition_date: e.target.value })}
                fullWidth
              />
            </div>

            <div>
              <Select
                label="Status"
                value={formData.status}
                onChange={(val) => setFormData({ ...formData, status: val })}
                options={[
                  { value: 'active', label: 'Active' },
                  { value: 'sold', label: 'Sold' },
                  { value: 'under_contract', label: 'Under Contract' },
                ]}
              />
            </div>
          </div>

          <div className="mb-6">
            <Input
              label="Ownership Structure"
              value={formData.ownership_structure}
              onChange={(e) => setFormData({ ...formData, ownership_structure: e.target.value })}
              placeholder="e.g. LLC, Partnership, etc."
              fullWidth
            />
          </div>

          <div className="mb-6">
            <label className="block text-sm font-medium mb-2 text-text-primary">Notes</label>
            <textarea
              value={formData.notes}
              onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
              rows={4}
              className="w-full px-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-info bg-surface"
              placeholder="Any additional notes..."
            />
          </div>

          <div className="flex gap-4 justify-end pt-4 border-t border-border">
            <Button className="bg-surface hover:bg-surface-hover border border-border text-text-primary" onClick={() => navigate('properties')} disabled={loading} type="button">
              Cancel
            </Button>
            <Button variant="primary" type="submit" disabled={loading} loading={loading} className="min-w-[120px]">
              {loading ? 'Creating...' : 'Create Property'}
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}
