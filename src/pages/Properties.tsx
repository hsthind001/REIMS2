import { useState, useEffect } from 'react';
import { propertyService } from '../lib/property';
import type { Property, PropertyCreate } from '../types/api';

export default function Properties() {
  const [properties, setProperties] = useState<Property[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingProperty, setEditingProperty] = useState<Property | null>(null);

  useEffect(() => {
    loadProperties();
  }, []);

  const loadProperties = async () => {
    try {
      setLoading(true);
      setError('');
      const data = await propertyService.getAllProperties();
      setProperties(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load properties');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (property: Property) => {
    if (!confirm(`Delete property ${property.property_code}? This will delete all related data.`)) {
      return;
    }

    try {
      await propertyService.deleteProperty(property.id);
      await loadProperties();
    } catch (err: any) {
      alert(`Delete failed: ${err.message}`);
    }
  };

  return (
    <div className="page">
      <div className="page-header">
        <h1>Properties</h1>
        <button className="btn btn-primary" onClick={() => setShowCreateModal(true)}>
          + Add Property
        </button>
      </div>

      {error && <div className="alert alert-error">{error}</div>}
      
      <div className="page-content">
        {loading ? (
          <div className="loading">Loading properties...</div>
        ) : properties.length === 0 ? (
          <div className="placeholder-card">
            <span className="placeholder-icon">🏢</span>
            <p>No properties yet</p>
            <button className="btn btn-primary" onClick={() => setShowCreateModal(true)}>
              Create your first property
            </button>
          </div>
        ) : (
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Code</th>
                  <th>Name</th>
                  <th>Type</th>
                  <th>Location</th>
                  <th>Area (sqft)</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {properties.map((property) => (
                  <tr key={property.id}>
                    <td><strong>{property.property_code}</strong></td>
                    <td>{property.property_name}</td>
                    <td>{property.property_type || '-'}</td>
                    <td>{property.city && property.state ? `${property.city}, ${property.state}` : '-'}</td>
                    <td>{property.total_area_sqft?.toLocaleString() || '-'}</td>
                    <td>
                      <span className={`status-badge status-${property.status}`}>
                        {property.status}
                      </span>
                    </td>
                    <td>
                      <button 
                        className="btn btn-sm btn-secondary"
                        onClick={() => setEditingProperty(property)}
                      >
                        Edit
                      </button>
                      <button 
                        className="btn btn-sm btn-danger"
                        onClick={() => handleDelete(property)}
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {showCreateModal && (
        <PropertyFormModal
          onClose={() => setShowCreateModal(false)}
          onSuccess={() => {
            setShowCreateModal(false);
            loadProperties();
          }}
        />
      )}

      {editingProperty && (
        <PropertyFormModal
          property={editingProperty}
          onClose={() => setEditingProperty(null)}
          onSuccess={() => {
            setEditingProperty(null);
            loadProperties();
          }}
        />
      )}
    </div>
  );
}

// Property Form Modal Component
function PropertyFormModal({
  property,
  onClose,
  onSuccess,
}: {
  property?: Property;
  onClose: () => void;
  onSuccess: () => void;
}) {
  const isEditing = !!property;
  const [formData, setFormData] = useState<PropertyCreate>({
    property_code: property?.property_code || '',
    property_name: property?.property_name || '',
    property_type: property?.property_type || '',
    address: property?.address || '',
    city: property?.city || '',
    state: property?.state || '',
    zip_code: property?.zip_code || '',
    country: property?.country || 'USA',
    total_area_sqft: property?.total_area_sqft || undefined,
    acquisition_date: property?.acquisition_date || '',
    ownership_structure: property?.ownership_structure || '',
    status: property?.status || 'active',
    notes: property?.notes || '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      if (isEditing && property) {
        await propertyService.updateProperty(property.id, formData);
      } else {
        await propertyService.createProperty(formData);
      }
      onSuccess();
    } catch (err: any) {
      setError(err.message || 'Operation failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>{isEditing ? 'Edit Property' : 'Create Property'}</h2>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>

        {error && <div className="alert alert-error">{error}</div>}

        <form onSubmit={handleSubmit}>
          <div className="form-row">
            <div className="form-group">
              <label>Property Code *</label>
              <input
                type="text"
                value={formData.property_code}
                onChange={(e) => setFormData({ ...formData, property_code: e.target.value })}
                required
                disabled={isEditing}
                pattern="[A-Z]{2,5}\\d{3}"
                title="Format: LETTERS+3 digits (e.g., ESP001)"
              />
              <small>e.g., ESP001, WEND001</small>
            </div>

            <div className="form-group">
              <label>Property Name *</label>
              <input
                type="text"
                value={formData.property_name}
                onChange={(e) => setFormData({ ...formData, property_name: e.target.value })}
                required
              />
            </div>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label>Property Type</label>
              <select
                value={formData.property_type}
                onChange={(e) => setFormData({ ...formData, property_type: e.target.value })}
              >
                <option value="">Select type...</option>
                <option value="Retail">Retail</option>
                <option value="Office">Office</option>
                <option value="Industrial">Industrial</option>
                <option value="Mixed Use">Mixed Use</option>
                <option value="Multifamily">Multifamily</option>
              </select>
            </div>

            <div className="form-group">
              <label>Total Area (sqft)</label>
              <input
                type="number"
                value={formData.total_area_sqft || ''}
                onChange={(e) => setFormData({ ...formData, total_area_sqft: e.target.value ? Number(e.target.value) : undefined })}
                min="0"
              />
            </div>
          </div>

          <div className="form-group">
            <label>Address</label>
            <input
              type="text"
              value={formData.address}
              onChange={(e) => setFormData({ ...formData, address: e.target.value })}
            />
          </div>

          <div className="form-row">
            <div className="form-group">
              <label>City</label>
              <input
                type="text"
                value={formData.city}
                onChange={(e) => setFormData({ ...formData, city: e.target.value })}
              />
            </div>

            <div className="form-group">
              <label>State</label>
              <input
                type="text"
                value={formData.state}
                onChange={(e) => setFormData({ ...formData, state: e.target.value })}
                maxLength={2}
                placeholder="NC"
              />
            </div>

            <div className="form-group">
              <label>ZIP Code</label>
              <input
                type="text"
                value={formData.zip_code}
                onChange={(e) => setFormData({ ...formData, zip_code: e.target.value })}
              />
            </div>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label>Acquisition Date</label>
              <input
                type="date"
                value={formData.acquisition_date}
                onChange={(e) => setFormData({ ...formData, acquisition_date: e.target.value })}
              />
            </div>

            <div className="form-group">
              <label>Status</label>
              <select
                value={formData.status}
                onChange={(e) => setFormData({ ...formData, status: e.target.value })}
              >
                <option value="active">Active</option>
                <option value="sold">Sold</option>
                <option value="under_contract">Under Contract</option>
              </select>
            </div>
          </div>

          <div className="form-group">
            <label>Ownership Structure</label>
            <input
              type="text"
              value={formData.ownership_structure}
              onChange={(e) => setFormData({ ...formData, ownership_structure: e.target.value })}
              placeholder="LLC, Partnership, etc."
            />
          </div>

          <div className="form-group">
            <label>Notes</label>
            <textarea
              value={formData.notes}
              onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
              rows={3}
              style={{ width: '100%', padding: '0.75rem', borderRadius: '4px', border: '1px solid var(--border-color)' }}
            />
          </div>

          <div className="modal-actions">
            <button type="button" className="btn btn-secondary" onClick={onClose} disabled={loading}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? 'Saving...' : isEditing ? 'Update' : 'Create'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
