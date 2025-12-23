/**
 * Saved Views Component
 * 
 * Allows users to save, default, and share filter views
 */

import { useState, useEffect } from 'react';
import { Save, Star, Share2, Trash2, Plus, X } from 'lucide-react';

const API_BASE_URL = import.meta.env.VITE_API_URL ? `${import.meta.env.VITE_API_URL}/api/v1` : 'http://localhost:8000/api/v1';

export interface SavedView {
  id: number;
  name: string;
  description?: string;
  filters: Record<string, any>;
  is_default: boolean;
  is_shared: boolean;
  created_by: number;
  created_at: string;
  updated_at: string;
}

interface SavedViewsProps {
  currentFilters: Record<string, any>;
  onApplyView?: (filters: Record<string, any>) => void;
  onSaveView?: (name: string, description: string, isDefault: boolean, isShared: boolean) => void;
}

export default function SavedViews({
  currentFilters,
  onApplyView,
  onSaveView,
}: SavedViewsProps) {
  const [views, setViews] = useState<SavedView[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [showSaveDialog, setShowSaveDialog] = useState<boolean>(false);
  const [viewName, setViewName] = useState<string>('');
  const [viewDescription, setViewDescription] = useState<string>('');
  const [isDefault, setIsDefault] = useState<boolean>(false);
  const [isShared, setIsShared] = useState<boolean>(false);

  useEffect(() => {
    loadViews();
  }, []);

  const loadViews = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_BASE_URL}/saved-views`, {
        headers: { 'Content-Type': 'application/json' },
      });
      
      if (response.ok) {
        const data = await response.json();
        setViews(data.views || []);
      }
    } catch (err) {
      console.error('Error loading saved views:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveView = async () => {
    if (!viewName.trim()) {
      alert('Please enter a view name');
      return;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/saved-views`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: viewName,
          description: viewDescription,
          filters: currentFilters,
          is_default: isDefault,
          is_shared: isShared,
        }),
      });

      if (response.ok) {
        await loadViews();
        setShowSaveDialog(false);
        setViewName('');
        setViewDescription('');
        setIsDefault(false);
        setIsShared(false);
        onSaveView?.(viewName, viewDescription, isDefault, isShared);
      } else {
        alert('Failed to save view');
      }
    } catch (err) {
      console.error('Error saving view:', err);
      alert('Failed to save view');
    }
  };

  const handleApplyView = (view: SavedView) => {
    onApplyView?.(view.filters);
  };

  const handleSetDefault = async (viewId: number) => {
    try {
      const response = await fetch(`${API_BASE_URL}/saved-views/${viewId}/set-default`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });

      if (response.ok) {
        await loadViews();
      }
    } catch (err) {
      console.error('Error setting default view:', err);
    }
  };

  const handleDeleteView = async (viewId: number) => {
    if (!confirm('Are you sure you want to delete this view?')) {
      return;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/saved-views/${viewId}`, {
        method: 'DELETE',
      });

      if (response.ok) {
        await loadViews();
      }
    } catch (err) {
      console.error('Error deleting view:', err);
    }
  };

  const handleShareView = async (viewId: number) => {
    try {
      const response = await fetch(`${API_BASE_URL}/saved-views/${viewId}/share`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });

      if (response.ok) {
        await loadViews();
      }
    } catch (err) {
      console.error('Error sharing view:', err);
    }
  };

  if (loading) {
    return (
      <div style={{ padding: '1rem', textAlign: 'center' }}>
        <div className="spinner"></div>
        <p>Loading saved views...</p>
      </div>
    );
  }

  return (
    <div style={{
      padding: '1rem',
      backgroundColor: '#fff',
      borderRadius: '8px',
      border: '1px solid #dee2e6',
    }}>
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '1rem',
      }}>
        <h4 style={{ fontSize: '1rem', fontWeight: 600, margin: 0 }}>
          Saved Views
        </h4>
        <button
          onClick={() => setShowSaveDialog(true)}
          style={{
            padding: '0.5rem 1rem',
            borderRadius: '4px',
            border: '1px solid #0dcaf0',
            backgroundColor: '#0dcaf0',
            color: '#fff',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            fontSize: '0.875rem',
          }}
        >
          <Plus size={16} />
          Save Current View
        </button>
      </div>

      {/* Save Dialog */}
      {showSaveDialog && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
        }}>
          <div style={{
            backgroundColor: '#fff',
            borderRadius: '8px',
            padding: '1.5rem',
            width: '90%',
            maxWidth: '500px',
            boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
          }}>
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: '1rem',
            }}>
              <h3 style={{ fontSize: '1.25rem', fontWeight: 600, margin: 0 }}>
                Save View
              </h3>
              <button
                onClick={() => setShowSaveDialog(false)}
                style={{
                  padding: '0.5rem',
                  border: 'none',
                  backgroundColor: 'transparent',
                  cursor: 'pointer',
                }}
              >
                <X size={20} />
              </button>
            </div>

            <div style={{ marginBottom: '1rem' }}>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 600 }}>
                View Name *
              </label>
              <input
                type="text"
                value={viewName}
                onChange={(e) => setViewName(e.target.value)}
                placeholder="e.g., My Properties"
                style={{
                  width: '100%',
                  padding: '0.5rem',
                  borderRadius: '4px',
                  border: '1px solid #dee2e6',
                }}
              />
            </div>

            <div style={{ marginBottom: '1rem' }}>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 600 }}>
                Description
              </label>
              <textarea
                value={viewDescription}
                onChange={(e) => setViewDescription(e.target.value)}
                placeholder="Optional description..."
                style={{
                  width: '100%',
                  padding: '0.5rem',
                  borderRadius: '4px',
                  border: '1px solid #dee2e6',
                  minHeight: '80px',
                }}
              />
            </div>

            <div style={{ marginBottom: '1rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={isDefault}
                  onChange={(e) => setIsDefault(e.target.checked)}
                />
                <span>Set as default view</span>
              </label>
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={isShared}
                  onChange={(e) => setIsShared(e.target.checked)}
                />
                <span>Share with team</span>
              </label>
            </div>

            <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
              <button
                onClick={() => setShowSaveDialog(false)}
                style={{
                  padding: '0.5rem 1rem',
                  borderRadius: '4px',
                  border: '1px solid #dee2e6',
                  backgroundColor: '#fff',
                  cursor: 'pointer',
                }}
              >
                Cancel
              </button>
              <button
                onClick={handleSaveView}
                style={{
                  padding: '0.5rem 1rem',
                  borderRadius: '4px',
                  border: 'none',
                  backgroundColor: '#0dcaf0',
                  color: '#fff',
                  cursor: 'pointer',
                }}
              >
                Save
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Views List */}
      {views.length === 0 ? (
        <div style={{ padding: '2rem', textAlign: 'center', color: '#6c757d' }}>
          <p>No saved views yet. Save your current filters to create one.</p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          {views.map(view => (
            <div
              key={view.id}
              style={{
                padding: '0.75rem',
                border: '1px solid #dee2e6',
                borderRadius: '4px',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                backgroundColor: view.is_default ? '#fff3cd' : '#fff',
              }}
            >
              <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
                  <strong>{view.name}</strong>
                  {view.is_default && (
                    <Star size={16} style={{ color: '#ffc107', fill: '#ffc107' }} />
                  )}
                  {view.is_shared && (
                    <Share2 size={16} style={{ color: '#0dcaf0' }} />
                  )}
                </div>
                {view.description && (
                  <div style={{ fontSize: '0.875rem', color: '#6c757d' }}>
                    {view.description}
                  </div>
                )}
              </div>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <button
                  onClick={() => handleApplyView(view)}
                  style={{
                    padding: '0.5rem',
                    borderRadius: '4px',
                    border: '1px solid #0dcaf0',
                    backgroundColor: '#fff',
                    color: '#0dcaf0',
                    cursor: 'pointer',
                    fontSize: '0.875rem',
                  }}
                >
                  Apply
                </button>
                {!view.is_default && (
                  <button
                    onClick={() => handleSetDefault(view.id)}
                    style={{
                      padding: '0.5rem',
                      borderRadius: '4px',
                      border: 'none',
                      backgroundColor: 'transparent',
                      cursor: 'pointer',
                    }}
                    title="Set as default"
                  >
                    <Star size={16} style={{ color: '#6c757d' }} />
                  </button>
                )}
                {!view.is_shared && (
                  <button
                    onClick={() => handleShareView(view.id)}
                    style={{
                      padding: '0.5rem',
                      borderRadius: '4px',
                      border: 'none',
                      backgroundColor: 'transparent',
                      cursor: 'pointer',
                    }}
                    title="Share with team"
                  >
                    <Share2 size={16} style={{ color: '#6c757d' }} />
                  </button>
                )}
                <button
                  onClick={() => handleDeleteView(view.id)}
                  style={{
                    padding: '0.5rem',
                    borderRadius: '4px',
                    border: 'none',
                    backgroundColor: 'transparent',
                    cursor: 'pointer',
                  }}
                  title="Delete view"
                >
                  <Trash2 size={16} style={{ color: '#dc3545' }} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
