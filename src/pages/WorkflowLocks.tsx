/**
 * Workflow Locks Page
 * 
 * Comprehensive interface for managing workflow locks, approvals, and operation checks
 */

import { useState, useEffect } from 'react';
import { 
  workflowLockService, 
  WorkflowLock, 
  LockReasonLabels, 
  LockScopeLabels, 
  LockStatusLabels,
  LockStatus,
  LockReason,
  LockScope,
  CreateLockRequest,
  ReleaseLockRequest,
  ApproveLockRequest,
  RejectLockRequest
} from '../lib/workflowLocks';
import { propertyService } from '../lib/property';
import type { Property } from '../types/api';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function WorkflowLocks() {
  const [locks, setLocks] = useState<WorkflowLock[]>([]);
  const [properties, setProperties] = useState<Property[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedProperty, setSelectedProperty] = useState<number | null>(null);
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [selectedLock, setSelectedLock] = useState<WorkflowLock | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showDetailModal, setShowDetailModal] = useState(false);
  const [showActionModal, setShowActionModal] = useState(false);
  const [actionType, setActionType] = useState<'release' | 'approve' | 'reject' | null>(null);
  const [actionNotes, setActionNotes] = useState('');
  const [actionReason, setActionReason] = useState('');
  const [statistics, setStatistics] = useState<any>(null);

  // Create lock form state
  const [newLock, setNewLock] = useState<Partial<CreateLockRequest>>({
    property_id: 0,
    lock_reason: LockReason.MANUAL_HOLD,
    lock_scope: LockScope.PROPERTY_ALL,
    title: '',
    description: '',
    locked_by: 1, // TODO: Get from auth context
  });

  useEffect(() => {
    loadProperties();
    loadStatistics();
  }, []);

  useEffect(() => {
    if (selectedProperty) {
      loadLocks();
    } else {
      loadPendingApprovals();
    }
  }, [selectedProperty, filterStatus]);

  const loadProperties = async () => {
    try {
      const data = await propertyService.getAllProperties();
      setProperties(data);
    } catch (error) {
      console.error('Failed to load properties:', error);
    }
  };

  const loadLocks = async () => {
    if (!selectedProperty) return;
    
    setLoading(true);
    try {
      const status = filterStatus !== 'all' ? filterStatus : undefined;
      const data = await workflowLockService.getPropertyLocks(selectedProperty, status);
      setLocks(data.locks || []);
    } catch (error) {
      console.error('Failed to load locks:', error);
      setLocks([]);
    } finally {
      setLoading(false);
    }
  };

  const loadPendingApprovals = async () => {
    setLoading(true);
    try {
      const data = await workflowLockService.getPendingApprovals();
      setLocks(data.locks || []);
    } catch (error) {
      console.error('Failed to load pending approvals:', error);
      setLocks([]);
    } finally {
      setLoading(false);
    }
  };

  const loadStatistics = async () => {
    try {
      const data = await workflowLockService.getStatistics();
      setStatistics(data.statistics);
    } catch (error) {
      console.error('Failed to load statistics:', error);
    }
  };

  const handleCreateLock = async () => {
    if (!newLock.property_id || !newLock.title || !newLock.description) {
      alert('Please fill in all required fields');
      return;
    }

    try {
      const result = await workflowLockService.createLock(newLock as CreateLockRequest);
      if (result.success) {
        alert('✅ Workflow lock created successfully');
        setShowCreateModal(false);
        setNewLock({
          property_id: 0,
          lock_reason: LockReason.MANUAL_HOLD,
          lock_scope: LockScope.PROPERTY_ALL,
          title: '',
          description: '',
          locked_by: 1,
        });
        loadLocks();
        loadStatistics();
      } else {
        alert(`Failed to create lock: ${result.error || 'Unknown error'}`);
      }
    } catch (error: any) {
      alert(`Failed to create lock: ${error.message || 'Unknown error'}`);
    }
  };

  const handleAction = async () => {
    if (!selectedLock) return;

    try {
      let result;
      const userId = 1; // TODO: Get from auth context

      if (actionType === 'release') {
        result = await workflowLockService.releaseLock(selectedLock.id, {
          unlocked_by: userId,
          resolution_notes: actionNotes,
        } as ReleaseLockRequest);
      } else if (actionType === 'approve') {
        if (!actionNotes.trim()) {
          alert('Resolution notes are required for approval');
          return;
        }
        result = await workflowLockService.approveLock(selectedLock.id, {
          approved_by: userId,
          resolution_notes: actionNotes,
        } as ApproveLockRequest);
      } else if (actionType === 'reject') {
        if (!actionReason.trim()) {
          alert('Rejection reason is required');
          return;
        }
        result = await workflowLockService.rejectLock(selectedLock.id, {
          rejected_by: userId,
          rejection_reason: actionReason,
        } as RejectLockRequest);
      }

      if (result?.success) {
        alert(`✅ Lock ${actionType}d successfully`);
        setShowActionModal(false);
        setActionNotes('');
        setActionReason('');
        setSelectedLock(null);
        setActionType(null);
        loadLocks();
        loadPendingApprovals();
        loadStatistics();
      } else {
        alert(`Failed to ${actionType} lock: ${result?.error || 'Unknown error'}`);
      }
    } catch (error: any) {
      alert(`Failed to ${actionType} lock: ${error.message || 'Unknown error'}`);
    }
  };

  const openActionModal = (lock: WorkflowLock, type: 'release' | 'approve' | 'reject') => {
    setSelectedLock(lock);
    setActionType(type);
    setActionNotes('');
    setActionReason('');
    setShowActionModal(true);
  };

  const getStatusBadgeClass = (status: string) => {
    switch (status?.toUpperCase()) {
      case 'ACTIVE':
        return 'badge-error';
      case 'PENDING_APPROVAL':
        return 'badge-warning';
      case 'APPROVED':
        return 'badge-success';
      case 'REJECTED':
        return 'badge-warning';
      case 'RELEASED':
        return 'badge-info';
      default:
        return 'badge-secondary';
    }
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleString();
  };

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Workflow Locks</h1>
          <p className="page-subtitle">Manage workflow locks, approvals, and operation controls</p>
        </div>
        <div className="header-actions">
          <button 
            className="btn-primary"
            onClick={() => setShowCreateModal(true)}
          >
            ➕ Create Lock
          </button>
          <button 
            className="btn-secondary"
            onClick={() => {
              loadLocks();
              loadPendingApprovals();
              loadStatistics();
            }}
          >
            🔄 Refresh
          </button>
        </div>
      </div>

      {/* Statistics */}
      {statistics && (
        <div className="card" style={{ marginBottom: '1.5rem' }}>
          <h3>Lock Statistics</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
            <div>
              <div style={{ fontSize: '0.875rem', color: '#6b7280', marginBottom: '0.25rem' }}>Total Locks</div>
              <div style={{ fontSize: '1.5rem', fontWeight: 'bold' }}>{statistics.total_locks || 0}</div>
            </div>
            <div>
              <div style={{ fontSize: '0.875rem', color: '#6b7280', marginBottom: '0.25rem' }}>Active Locks</div>
              <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#dc2626' }}>{statistics.active_locks || 0}</div>
            </div>
            <div>
              <div style={{ fontSize: '0.875rem', color: '#6b7280', marginBottom: '0.25rem' }}>Pending Approvals</div>
              <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#f59e0b' }}>{statistics.pending_approvals || 0}</div>
            </div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="card" style={{ marginBottom: '1.5rem' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
          <div className="form-group">
            <label>Property</label>
            <select
              value={selectedProperty || ''}
              onChange={(e) => setSelectedProperty(e.target.value ? parseInt(e.target.value) : null)}
              style={{ width: '100%', padding: '0.5rem', borderRadius: '0.375rem', border: '1px solid #d1d5db' }}
            >
              <option value="">All Properties (Pending Approvals)</option>
              {properties.map(p => (
                <option key={p.id} value={p.id}>{p.property_code} - {p.property_name}</option>
              ))}
            </select>
          </div>
          <div className="form-group">
            <label>Status Filter</label>
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              style={{ width: '100%', padding: '0.5rem', borderRadius: '0.375rem', border: '1px solid #d1d5db' }}
            >
              <option value="all">All Statuses</option>
              <option value="ACTIVE">Active</option>
              <option value="PENDING_APPROVAL">Pending Approval</option>
              <option value="APPROVED">Approved</option>
              <option value="REJECTED">Rejected</option>
              <option value="RELEASED">Released</option>
            </select>
          </div>
        </div>
      </div>

      {/* Locks Table */}
      <div className="card">
        <h3>
          {selectedProperty 
            ? `Locks for ${properties.find(p => p.id === selectedProperty)?.property_name || 'Property'}`
            : 'Pending Approvals'}
          ({locks.length})
        </h3>
        
        {loading ? (
          <div className="empty-state">
            <div className="spinner"></div>
            <p>Loading locks...</p>
          </div>
        ) : locks.length === 0 ? (
          <div className="empty-state">
            <p>
              {selectedProperty 
                ? '✅ No workflow locks for this property'
                : '✅ No pending approvals'}
            </p>
          </div>
        ) : (
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Property</th>
                  <th>Title</th>
                  <th>Reason</th>
                  <th>Scope</th>
                  <th>Status</th>
                  <th>Requires Approval</th>
                  <th>Locked At</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {locks.map((lock) => (
                  <tr key={lock.id}>
                    <td>{lock.id}</td>
                    <td>
                      {lock.property?.code || `Property ${lock.property_id}`}
                      {lock.property?.name && (
                        <div style={{ fontSize: '0.75rem', color: '#6b7280' }}>{lock.property.name}</div>
                      )}
                    </td>
                    <td>
                      <strong>{lock.title}</strong>
                      {lock.description && (
                        <div style={{ fontSize: '0.75rem', color: '#6b7280', marginTop: '0.25rem' }}>
                          {lock.description.substring(0, 60)}{lock.description.length > 60 ? '...' : ''}
                        </div>
                      )}
                    </td>
                    <td>{LockReasonLabels[lock.lock_reason] || lock.lock_reason}</td>
                    <td>{LockScopeLabels[lock.lock_scope] || lock.lock_scope}</td>
                    <td>
                      <span className={`badge ${getStatusBadgeClass(lock.status)}`}>
                        {LockStatusLabels[lock.status] || lock.status}
                      </span>
                    </td>
                    <td>{lock.requires_committee_approval ? '✓' : '✗'}</td>
                    <td>{formatDate(lock.locked_at)}</td>
                    <td>
                      <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                        <button
                          className="btn-sm btn-secondary"
                          onClick={() => {
                            setSelectedLock(lock);
                            setShowDetailModal(true);
                          }}
                        >
                          View
                        </button>
                        {lock.status === LockStatus.ACTIVE && (
                          <>
                            {lock.requires_committee_approval && (
                              <>
                                <button
                                  className="btn-sm btn-success"
                                  onClick={() => openActionModal(lock, 'approve')}
                                >
                                  Approve
                                </button>
                                <button
                                  className="btn-sm btn-warning"
                                  onClick={() => openActionModal(lock, 'reject')}
                                >
                                  Reject
                                </button>
                              </>
                            )}
                            <button
                              className="btn-sm btn-danger"
                              onClick={() => openActionModal(lock, 'release')}
                            >
                              Release
                            </button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Create Lock Modal */}
      {showCreateModal && (
        <div className="modal-overlay" onClick={() => setShowCreateModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Create Workflow Lock</h2>
              <button className="modal-close" onClick={() => setShowCreateModal(false)}>×</button>
            </div>
            <div className="modal-body">
              <div className="form-group">
                <label>Property *</label>
                <select
                  value={newLock.property_id || ''}
                  onChange={(e) => setNewLock({...newLock, property_id: parseInt(e.target.value)})}
                  style={{ width: '100%', padding: '0.5rem', borderRadius: '0.375rem', border: '1px solid #d1d5db' }}
                >
                  <option value="">Select Property</option>
                  {properties.map(p => (
                    <option key={p.id} value={p.id}>{p.property_code} - {p.property_name}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Lock Reason *</label>
                <select
                  value={newLock.lock_reason || ''}
                  onChange={(e) => setNewLock({...newLock, lock_reason: e.target.value})}
                  style={{ width: '100%', padding: '0.5rem', borderRadius: '0.375rem', border: '1px solid #d1d5db' }}
                >
                  {Object.entries(LockReasonLabels).map(([value, label]) => (
                    <option key={value} value={value}>{label}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Lock Scope *</label>
                <select
                  value={newLock.lock_scope || ''}
                  onChange={(e) => setNewLock({...newLock, lock_scope: e.target.value})}
                  style={{ width: '100%', padding: '0.5rem', borderRadius: '0.375rem', border: '1px solid #d1d5db' }}
                >
                  {Object.entries(LockScopeLabels).map(([value, label]) => (
                    <option key={value} value={value}>{label}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Title *</label>
                <input
                  type="text"
                  value={newLock.title || ''}
                  onChange={(e) => setNewLock({...newLock, title: e.target.value})}
                  style={{ width: '100%', padding: '0.5rem', borderRadius: '0.375rem', border: '1px solid #d1d5db' }}
                  placeholder="Enter lock title"
                />
              </div>
              <div className="form-group">
                <label>Description *</label>
                <textarea
                  value={newLock.description || ''}
                  onChange={(e) => setNewLock({...newLock, description: e.target.value})}
                  style={{ width: '100%', padding: '0.5rem', borderRadius: '0.375rem', border: '1px solid #d1d5db', minHeight: '100px' }}
                  placeholder="Enter lock description"
                />
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn-secondary" onClick={() => setShowCreateModal(false)}>Cancel</button>
              <button className="btn-primary" onClick={handleCreateLock}>Create Lock</button>
            </div>
          </div>
        </div>
      )}

      {/* Detail Modal */}
      {showDetailModal && selectedLock && (
        <div className="modal-overlay" onClick={() => setShowDetailModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '800px' }}>
            <div className="modal-header">
              <h2>Lock Details</h2>
              <button className="modal-close" onClick={() => setShowDetailModal(false)}>×</button>
            </div>
            <div className="modal-body">
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
                <div>
                  <strong>ID:</strong> {selectedLock.id}
                </div>
                <div>
                  <strong>Status:</strong>{' '}
                  <span className={`badge ${getStatusBadgeClass(selectedLock.status)}`}>
                    {LockStatusLabels[selectedLock.status] || selectedLock.status}
                  </span>
                </div>
                <div>
                  <strong>Property:</strong> {selectedLock.property?.code || `Property ${selectedLock.property_id}`}
                </div>
                <div>
                  <strong>Reason:</strong> {LockReasonLabels[selectedLock.lock_reason] || selectedLock.lock_reason}
                </div>
                <div>
                  <strong>Scope:</strong> {LockScopeLabels[selectedLock.lock_scope] || selectedLock.lock_scope}
                </div>
                <div>
                  <strong>Requires Approval:</strong> {selectedLock.requires_committee_approval ? 'Yes' : 'No'}
                </div>
                {selectedLock.approval_committee && (
                  <div>
                    <strong>Committee:</strong> {selectedLock.approval_committee}
                  </div>
                )}
                <div>
                  <strong>Locked At:</strong> {formatDate(selectedLock.locked_at)}
                </div>
                {selectedLock.unlocked_at && (
                  <div>
                    <strong>Unlocked At:</strong> {formatDate(selectedLock.unlocked_at)}
                  </div>
                )}
                {selectedLock.approved_at && (
                  <div>
                    <strong>Approved At:</strong> {formatDate(selectedLock.approved_at)}
                  </div>
                )}
                {selectedLock.rejected_at && (
                  <div>
                    <strong>Rejected At:</strong> {formatDate(selectedLock.rejected_at)}
                  </div>
                )}
              </div>
              <div style={{ marginBottom: '1rem' }}>
                <strong>Title:</strong>
                <div style={{ marginTop: '0.5rem' }}>{selectedLock.title}</div>
              </div>
              {selectedLock.description && (
                <div style={{ marginBottom: '1rem' }}>
                  <strong>Description:</strong>
                  <div style={{ marginTop: '0.5rem' }}>{selectedLock.description}</div>
                </div>
              )}
              {selectedLock.resolution_notes && (
                <div style={{ marginBottom: '1rem' }}>
                  <strong>Resolution Notes:</strong>
                  <div style={{ marginTop: '0.5rem' }}>{selectedLock.resolution_notes}</div>
                </div>
              )}
              {selectedLock.rejection_reason && (
                <div style={{ marginBottom: '1rem' }}>
                  <strong>Rejection Reason:</strong>
                  <div style={{ marginTop: '0.5rem', color: '#dc2626' }}>{selectedLock.rejection_reason}</div>
                </div>
              )}
            </div>
            <div className="modal-footer">
              <button className="btn-secondary" onClick={() => setShowDetailModal(false)}>Close</button>
            </div>
          </div>
        </div>
      )}

      {/* Action Modal */}
      {showActionModal && selectedLock && actionType && (
        <div className="modal-overlay" onClick={() => setShowActionModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>
                {actionType === 'release' && 'Release Lock'}
                {actionType === 'approve' && 'Approve Lock'}
                {actionType === 'reject' && 'Reject Lock'}
              </h2>
              <button className="modal-close" onClick={() => setShowActionModal(false)}>×</button>
            </div>
            <div className="modal-body">
              <div style={{ marginBottom: '1rem' }}>
                <strong>Lock:</strong> {selectedLock.title}
              </div>
              {actionType === 'reject' && (
                <div className="form-group">
                  <label>Rejection Reason *</label>
                  <textarea
                    value={actionReason}
                    onChange={(e) => setActionReason(e.target.value)}
                    style={{ width: '100%', padding: '0.5rem', borderRadius: '0.375rem', border: '1px solid #d1d5db', minHeight: '100px' }}
                    placeholder="Enter rejection reason"
                  />
                </div>
              )}
              {(actionType === 'release' || actionType === 'approve') && (
                <div className="form-group">
                  <label>Resolution Notes {actionType === 'approve' ? '*' : ''}</label>
                  <textarea
                    value={actionNotes}
                    onChange={(e) => setActionNotes(e.target.value)}
                    style={{ width: '100%', padding: '0.5rem', borderRadius: '0.375rem', border: '1px solid #d1d5db', minHeight: '100px' }}
                    placeholder="Enter resolution notes"
                  />
                </div>
              )}
            </div>
            <div className="modal-footer">
              <button className="btn-secondary" onClick={() => setShowActionModal(false)}>Cancel</button>
              <button 
                className={`btn-${actionType === 'reject' ? 'warning' : actionType === 'approve' ? 'success' : 'danger'}`}
                onClick={handleAction}
              >
                {actionType === 'release' && 'Release Lock'}
                {actionType === 'approve' && 'Approve Lock'}
                {actionType === 'reject' && 'Reject Lock'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

