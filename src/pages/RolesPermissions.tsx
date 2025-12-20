import { useState, useEffect } from 'react';

const API_BASE_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000') + '/api/v1';

interface Role {
  id: number;
  name: string;
  description: string;
  user_count: number;
  is_system_role: boolean;
}

interface Permission {
  module: string;
  can_view: boolean;
  can_create: boolean;
  can_edit: boolean;
  can_delete: boolean;
}

interface RoleDetails extends Role {
  permissions: Permission[];
  special_permissions: string[];
}

interface AuditLog {
  timestamp: string;
  user_name: string;
  action: string;
  details: string;
}

export default function RolesPermissions() {
  const [roles, setRoles] = useState<Role[]>([]);
  const [selectedRole, setSelectedRole] = useState<RoleDetails | null>(null);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);

  const [newRole, setNewRole] = useState({
    name: '',
    description: '',
  });

  useEffect(() => {
    loadRoles();
    loadAuditLogs();
  }, []);

  const loadRoles = async () => {
    try {
      setLoading(true);
      setError('');
      const response = await fetch(`${API_BASE_URL}/rbac/roles`, {
        credentials: 'include'
      });

      if (!response.ok) throw new Error('Failed to load roles');

      const data = await response.json();
      setRoles(data.roles || []);
    } catch (err) {
      console.error('Failed to load roles:', err);
      setError('Failed to load roles');
    } finally {
      setLoading(false);
    }
  };

  const loadRoleDetails = async (roleId: number) => {
    try {
      const response = await fetch(`${API_BASE_URL}/rbac/roles/${roleId}`, {
        credentials: 'include'
      });

      if (!response.ok) throw new Error('Failed to load role details');

      const data = await response.json();
      setSelectedRole(data);
    } catch (err) {
      console.error('Failed to load role details:', err);
      setError('Failed to load role details');
    }
  };

  const loadAuditLogs = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/rbac/audit`, {
        credentials: 'include'
      });

      if (response.ok) {
        const data = await response.json();
        setAuditLogs(data.logs || []);
      }
    } catch (err) {
      console.error('Failed to load audit logs:', err);
    }
  };

  const handleCreateRole = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      setError('');
      const response = await fetch(`${API_BASE_URL}/rbac/roles`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(newRole)
      });

      if (!response.ok) throw new Error('Failed to create role');

      setShowCreateModal(false);
      setNewRole({ name: '', description: '' });
      loadRoles();
    } catch (err) {
      console.error('Failed to create role:', err);
      setError('Failed to create role');
    }
  };

  const handleUpdatePermissions = async () => {
    if (!selectedRole) return;

    try {
      setError('');
      const response = await fetch(`${API_BASE_URL}/rbac/roles/${selectedRole.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          permissions: selectedRole.permissions,
          special_permissions: selectedRole.special_permissions
        })
      });

      if (!response.ok) throw new Error('Failed to update permissions');

      alert('Permissions updated successfully');
      loadAuditLogs();
    } catch (err) {
      console.error('Failed to update permissions:', err);
      setError('Failed to update permissions');
    }
  };

  const handleDeleteRole = async (roleId: number) => {
    if (!confirm('Are you sure you want to delete this role?')) return;

    try {
      setError('');
      const response = await fetch(`${API_BASE_URL}/rbac/roles/${roleId}`, {
        method: 'DELETE',
        credentials: 'include'
      });

      if (!response.ok) throw new Error('Failed to delete role');

      setSelectedRole(null);
      loadRoles();
    } catch (err) {
      console.error('Failed to delete role:', err);
      setError('Failed to delete role');
    }
  };

  const togglePermission = (module: string, permission: 'can_view' | 'can_create' | 'can_edit' | 'can_delete') => {
    if (!selectedRole) return;

    const updatedPermissions = selectedRole.permissions.map(perm => {
      if (perm.module === module) {
        return { ...perm, [permission]: !perm[permission] };
      }
      return perm;
    });

    setSelectedRole({ ...selectedRole, permissions: updatedPermissions });
  };

  const getRoleIcon = (roleName: string) => {
    if (roleName.includes('CEO')) return '👑';
    if (roleName.includes('CFO')) return '💼';
    if (roleName.includes('Manager')) return '📊';
    if (roleName.includes('Analyst')) return '📈';
    return '👤';
  };

  if (loading) {
    return (
      <div className="page">
        <div className="loading">Loading roles and permissions...</div>
      </div>
    );
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1>Role-Based Access Control</h1>
        <p className="page-subtitle">Manage roles, permissions, and user access</p>
      </div>

      {error && <div className="error-message">{error}</div>}

      <div className="page-content">
        {/* Predefined Roles */}
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h3>Predefined Roles ({roles.length})</h3>
            <button className="btn btn-primary" onClick={() => setShowCreateModal(true)}>
              + Create Custom Role
            </button>
          </div>

          <div style={{ display: 'grid', gap: '1rem' }}>
            {roles.map(role => (
              <div
                key={role.id}
                style={{
                  border: '1px solid var(--border-color)',
                  borderRadius: '0.5rem',
                  padding: '1rem',
                  cursor: 'pointer',
                  background: selectedRole?.id === role.id ? 'var(--primary-light)' : 'white',
                }}
                onClick={() => loadRoleDetails(role.id)}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <div style={{ fontSize: '1.2rem', fontWeight: 'bold', marginBottom: '0.25rem' }}>
                      {getRoleIcon(role.name)} {role.name}
                    </div>
                    <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
                      Users: {role.user_count} | {role.description}
                    </div>
                  </div>
                  <div>
                    <button className="btn btn-secondary" style={{ marginRight: '0.5rem' }}>
                      View Details
                    </button>
                    {!role.is_system_role && (
                      <button className="btn btn-secondary">Edit Permissions</button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Permissions Matrix */}
        {selectedRole && (
          <div className="card">
            <h3>Permissions Matrix - {selectedRole.name}</h3>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '1rem' }}>
              {selectedRole.is_system_role
                ? '⚠️ System role - Permissions are read-only'
                : 'Configure permissions for this role'
              }
            </p>

            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Module</th>
                    <th style={{ textAlign: 'center' }}>View</th>
                    <th style={{ textAlign: 'center' }}>Create</th>
                    <th style={{ textAlign: 'center' }}>Edit</th>
                    <th style={{ textAlign: 'center' }}>Delete</th>
                  </tr>
                </thead>
                <tbody>
                  {selectedRole.permissions.map((perm, idx) => (
                    <tr key={idx}>
                      <td><strong>{perm.module}</strong></td>
                      <td style={{ textAlign: 'center' }}>
                        <input
                          type="checkbox"
                          checked={perm.can_view}
                          onChange={() => togglePermission(perm.module, 'can_view')}
                          disabled={selectedRole.is_system_role}
                        />
                      </td>
                      <td style={{ textAlign: 'center' }}>
                        <input
                          type="checkbox"
                          checked={perm.can_create}
                          onChange={() => togglePermission(perm.module, 'can_create')}
                          disabled={selectedRole.is_system_role}
                        />
                      </td>
                      <td style={{ textAlign: 'center' }}>
                        <input
                          type="checkbox"
                          checked={perm.can_edit}
                          onChange={() => togglePermission(perm.module, 'can_edit')}
                          disabled={selectedRole.is_system_role}
                        />
                      </td>
                      <td style={{ textAlign: 'center' }}>
                        <input
                          type="checkbox"
                          checked={perm.can_delete}
                          onChange={() => togglePermission(perm.module, 'can_delete')}
                          disabled={selectedRole.is_system_role}
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Special Permissions */}
            <div style={{ marginTop: '1.5rem' }}>
              <h4>Special Permissions</h4>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))', gap: '0.5rem', marginTop: '0.5rem' }}>
                {selectedRole.special_permissions.map((perm, idx) => (
                  <label key={idx} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <input type="checkbox" defaultChecked disabled={selectedRole.is_system_role} />
                    <span>{perm}</span>
                  </label>
                ))}
              </div>
            </div>

            {!selectedRole.is_system_role && (
              <div style={{ marginTop: '1.5rem', display: 'flex', gap: '0.5rem' }}>
                <button className="btn btn-primary" onClick={handleUpdatePermissions}>
                  Save Changes
                </button>
                <button className="btn btn-secondary" onClick={() => loadRoleDetails(selectedRole.id)}>
                  Cancel
                </button>
                <button className="btn btn-secondary">Reset to Default</button>
                <button
                  className="btn"
                  style={{ background: 'var(--error-color)', color: 'white', marginLeft: 'auto' }}
                  onClick={() => handleDeleteRole(selectedRole.id)}
                >
                  Delete Role
                </button>
              </div>
            )}
          </div>
        )}

        {/* Permission Inheritance */}
        <div className="card">
          <h3>Permission Inheritance</h3>
          <div style={{ padding: '1rem', background: 'var(--background-light)', borderRadius: '0.5rem' }}>
            <div style={{ fontSize: '1.1rem', textAlign: 'center' }}>
              👑 CEO → 💼 CFO → 📊 Asset Manager → 📈 Analyst
            </div>
            <p style={{ marginTop: '0.5rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
              Each role inherits permissions from roles below in the hierarchy
            </p>
          </div>
        </div>

        {/* Audit Log */}
        <div className="card">
          <h3>Recent Activity</h3>
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>User</th>
                  <th>Action</th>
                  <th>Details</th>
                </tr>
              </thead>
              <tbody>
                {auditLogs.length === 0 ? (
                  <tr>
                    <td colSpan={4} style={{ textAlign: 'center', padding: '2rem' }}>
                      No audit logs available
                    </td>
                  </tr>
                ) : (
                  auditLogs.slice(0, 10).map((log, idx) => (
                    <tr key={idx}>
                      <td>{new Date(log.timestamp).toLocaleString()}</td>
                      <td>{log.user_name}</td>
                      <td><strong>{log.action}</strong></td>
                      <td>{log.details}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Create Role Modal */}
      {showCreateModal && (
        <div className="modal-overlay" onClick={() => setShowCreateModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2>Create Custom Role</h2>
            <form onSubmit={handleCreateRole}>
              <div className="form-group">
                <label>Role Name*</label>
                <input
                  type="text"
                  className="input"
                  value={newRole.name}
                  onChange={(e) => setNewRole({ ...newRole, name: e.target.value })}
                  placeholder="e.g., Portfolio Manager"
                  required
                />
              </div>

              <div className="form-group">
                <label>Description*</label>
                <textarea
                  className="input"
                  value={newRole.description}
                  onChange={(e) => setNewRole({ ...newRole, description: e.target.value })}
                  placeholder="Describe the responsibilities and access level"
                  rows={3}
                  required
                />
              </div>

              <div style={{ display: 'flex', gap: '0.5rem', marginTop: '1.5rem' }}>
                <button type="submit" className="btn btn-primary">Create Role</button>
                <button type="button" className="btn btn-secondary" onClick={() => setShowCreateModal(false)}>
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
