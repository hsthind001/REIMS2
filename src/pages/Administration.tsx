import { useState, useEffect } from 'react';
import { 
  Shield, 
  Plus, 
  Edit, 
  Trash2,
  CheckCircle,
  XCircle,
  FileText,
  Search,
  Filter,
  CreditCard
} from 'lucide-react';
import { Card, Button } from '../components/design-system';
import { SubscriptionOverview } from '../components/billing/SubscriptionOverview';
import { BillingHistory } from '../components/billing/BillingHistory';
import { PlanManagement } from '../components/billing/PlanManagement';

const API_BASE_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000') + '/api/v1';

type AdminTab = 'users' | 'roles' | 'audit' | 'settings' | 'billing';

interface User {
  id: number;
  username: string;
  email: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

interface Role {
  id: number;
  name: string;
  description: string;
  user_count: number;
  permission_count: number;
  is_system_role: boolean;
}

interface Permission {
  module: string;
  can_view: boolean;
  can_create: boolean;
  can_edit: boolean;
  can_delete: boolean;
}

interface AuditLog {
  id: number;
  timestamp: string;
  user_name: string;
  action: string;
  details: string;
  ip_address?: string;
}

export default function AdminHub() {
  const [activeTab, setActiveTab] = useState<AdminTab>('users');
  const [billingTab, setBillingTab] = useState<'overview' | 'history' | 'plans'>('overview');
  const [users, setUsers] = useState<User[]>([]);
  const [roles, setRoles] = useState<Role[]>([]);
  const [selectedRole, setSelectedRole] = useState<Role | null>(null);
  const [rolePermissions, setRolePermissions] = useState<Permission[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    if (selectedRole) {
      loadRoleDetails(selectedRole.id);
    }
  }, [selectedRole]);

  const loadData = async () => {
    try {

      // Load users
      const usersRes = await fetch(`${API_BASE_URL}/users`, {
        credentials: 'include'
      });
      if (usersRes.ok) {
        const usersData = await usersRes.json();
        setUsers(usersData.users || usersData || []);
      }

      // Load roles
      const rolesRes = await fetch(`${API_BASE_URL}/rbac/roles`, {
        credentials: 'include'
      });
      if (rolesRes.ok) {
        const rolesData = await rolesRes.json();
        setRoles(rolesData.roles || rolesData || []);
      }

      // Load audit logs
      const auditRes = await fetch(`${API_BASE_URL}/rbac/audit`, {
        credentials: 'include'
      });
      if (auditRes.ok) {
        const auditData = await auditRes.json();
        setAuditLogs(auditData.logs || auditData || []);
      }
    } catch (err) {
      console.error('Failed to load admin data:', err);
    }
  };

  const loadRoleDetails = async (roleId: number) => {
    try {
      const res = await fetch(`${API_BASE_URL}/rbac/roles/${roleId}`, {
        credentials: 'include'
      });
      if (res.ok) {
        const data = await res.json();
        setRolePermissions(data.permissions || []);
      }
    } catch (err) {
      console.error('Failed to load role details:', err);
    }
  };

  const filteredUsers = users.filter(u =>
    u.username.toLowerCase().includes(searchTerm.toLowerCase()) ||
    u.email.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-7xl mx-auto px-6 py-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-3xl font-bold text-text-primary">Admin Hub</h1>
            <p className="text-text-secondary mt-1">User management, roles, permissions, and system settings</p>
          </div>
          <Button variant="primary" icon={<Plus className="w-4 h-4" />}>
            Add User
          </Button>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 border-b border-border mb-6">
          {(['users', 'roles', 'audit', 'billing', 'settings'] as AdminTab[]).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 font-medium text-sm transition-colors capitalize ${
                activeTab === tab
                  ? 'text-info border-b-2 border-info'
                  : 'text-text-secondary hover:text-text-primary'
              }`}
            >
              {tab === 'billing' && <CreditCard className="w-4 h-4 inline mr-2" />}
              {tab}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        {activeTab === 'users' && (
          <div className="space-y-6">
            {/* Search */}
            <Card className="p-4">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-text-secondary" />
                <input
                  type="text"
                  placeholder="Search users..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-info"
                />
              </div>
            </Card>

            {/* Users Table */}
            <Card className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-2xl font-bold">Users</h2>
                <div className="text-sm text-text-secondary">
                  {filteredUsers.length} user{filteredUsers.length !== 1 ? 's' : ''}
                </div>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-border">
                      <th className="text-left py-3 px-4 font-semibold">Username</th>
                      <th className="text-left py-3 px-4 font-semibold">Email</th>
                      <th className="text-left py-3 px-4 font-semibold">Role</th>
                      <th className="text-left py-3 px-4 font-semibold">Status</th>
                      <th className="text-left py-3 px-4 font-semibold">Created</th>
                      <th className="text-right py-3 px-4 font-semibold">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredUsers.map((user) => (
                      <tr key={user.id} className="border-b border-border hover:bg-background">
                        <td className="py-3 px-4 font-medium">{user.username}</td>
                        <td className="py-3 px-4 text-text-secondary">{user.email}</td>
                        <td className="py-3 px-4">
                          <span className="px-2 py-1 bg-info-light text-info rounded text-sm">
                            {user.role}
                          </span>
                        </td>
                        <td className="py-3 px-4">
                          {user.is_active ? (
                            <span className="flex items-center gap-1 text-success">
                              <CheckCircle className="w-4 h-4" />
                              Active
                            </span>
                          ) : (
                            <span className="flex items-center gap-1 text-text-secondary">
                              <XCircle className="w-4 h-4" />
                              Inactive
                            </span>
                          )}
                        </td>
                        <td className="py-3 px-4 text-text-secondary text-sm">
                          {new Date(user.created_at).toLocaleDateString()}
                        </td>
                        <td className="py-3 px-4">
                          <div className="flex gap-2 justify-end">
                            <Button variant="primary" size="sm" icon={<Edit className="w-4 h-4" />}>
                              Edit
                            </Button>
                            <Button variant="danger" size="sm" icon={<Trash2 className="w-4 h-4" />}>
                              Delete
                            </Button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          </div>
        )}

        {activeTab === 'roles' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Roles List */}
            <div className="lg:col-span-1">
              <Card className="p-6">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-xl font-bold">Roles</h2>
                  <Button variant="primary" size="sm" icon={<Plus className="w-4 h-4" />}>
                    Add Role
                  </Button>
                </div>
                <div className="space-y-2">
                  {roles.map((role) => (
                    <Card
                      key={role.id}
                      variant={selectedRole?.id === role.id ? 'info' : 'default'}
                      className={`p-4 cursor-pointer transition-all ${
                        selectedRole?.id === role.id ? 'ring-2 ring-info' : ''
                      }`}
                      onClick={() => setSelectedRole(role)}
                      hover
                    >
                      <div className="font-semibold">{role.name}</div>
                      <div className="text-sm text-text-secondary mt-1">{role.description}</div>
                      <div className="flex gap-4 mt-2 text-xs text-text-secondary">
                        <span>{role.user_count} users</span>
                        <span>{role.permission_count} permissions</span>
                      </div>
                      {role.is_system_role && (
                        <span className="text-xs text-warning mt-2 block">System Role</span>
                      )}
                    </Card>
                  ))}
                </div>
              </Card>
            </div>

            {/* Role Details & Permissions Matrix */}
            <div className="lg:col-span-2">
              {selectedRole ? (
                <Card className="p-6">
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <h2 className="text-2xl font-bold">{selectedRole.name}</h2>
                      <p className="text-text-secondary">{selectedRole.description}</p>
                    </div>
                    <Button variant="primary" icon={<Edit className="w-4 h-4" />}>
                      Edit Role
                    </Button>
                  </div>

                  {/* Permissions Matrix */}
                  <div className="mt-6">
                    <h3 className="text-lg font-semibold mb-4">Permissions Matrix</h3>
                    <div className="overflow-x-auto">
                      <table className="w-full">
                        <thead>
                          <tr className="border-b border-border">
                            <th className="text-left py-2 px-4 font-semibold">Module</th>
                            <th className="text-center py-2 px-4 font-semibold">View</th>
                            <th className="text-center py-2 px-4 font-semibold">Create</th>
                            <th className="text-center py-2 px-4 font-semibold">Edit</th>
                            <th className="text-center py-2 px-4 font-semibold">Delete</th>
                          </tr>
                        </thead>
                        <tbody>
                          {rolePermissions.length > 0 ? (
                            rolePermissions.map((perm, i) => (
                              <tr key={i} className="border-b border-border">
                                <td className="py-2 px-4 font-medium">{perm.module}</td>
                                <td className="text-center py-2 px-4">
                                  {perm.can_view ? (
                                    <CheckCircle className="w-5 h-5 text-success mx-auto" />
                                  ) : (
                                    <XCircle className="w-5 h-5 text-text-secondary mx-auto" />
                                  )}
                                </td>
                                <td className="text-center py-2 px-4">
                                  {perm.can_create ? (
                                    <CheckCircle className="w-5 h-5 text-success mx-auto" />
                                  ) : (
                                    <XCircle className="w-5 h-5 text-text-secondary mx-auto" />
                                  )}
                                </td>
                                <td className="text-center py-2 px-4">
                                  {perm.can_edit ? (
                                    <CheckCircle className="w-5 h-5 text-success mx-auto" />
                                  ) : (
                                    <XCircle className="w-5 h-5 text-text-secondary mx-auto" />
                                  )}
                                </td>
                                <td className="text-center py-2 px-4">
                                  {perm.can_delete ? (
                                    <CheckCircle className="w-5 h-5 text-success mx-auto" />
                                  ) : (
                                    <XCircle className="w-5 h-5 text-text-secondary mx-auto" />
                                  )}
                                </td>
                              </tr>
                            ))
                          ) : (
                            <tr>
                              <td colSpan={5} className="py-8 text-center text-text-secondary">
                                No permissions configured. Click "Edit Role" to add permissions.
                              </td>
                            </tr>
                          )}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </Card>
              ) : (
                <Card className="p-12 text-center">
                  <Shield className="w-16 h-16 mx-auto mb-4 text-text-secondary" />
                  <h3 className="text-xl font-semibold mb-2">No Role Selected</h3>
                  <p className="text-text-secondary">Select a role from the list to view permissions</p>
                </Card>
              )}
            </div>
          </div>
        )}

        {activeTab === 'audit' && (
          <Card className="p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-2xl font-bold">Audit Log</h2>
              <div className="flex gap-2">
                <Button variant="primary" size="sm" icon={<Filter className="w-4 h-4" />}>
                  Filter
                </Button>
                <Button variant="primary" size="sm" icon={<FileText className="w-4 h-4" />}>
                  Export
                </Button>
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-border">
                    <th className="text-left py-3 px-4 font-semibold">Timestamp</th>
                    <th className="text-left py-3 px-4 font-semibold">User</th>
                    <th className="text-left py-3 px-4 font-semibold">Action</th>
                    <th className="text-left py-3 px-4 font-semibold">Details</th>
                    <th className="text-left py-3 px-4 font-semibold">IP Address</th>
                  </tr>
                </thead>
                <tbody>
                  {auditLogs.slice(0, 50).map((log) => (
                    <tr key={log.id} className="border-b border-border hover:bg-background">
                      <td className="py-3 px-4 text-sm text-text-secondary">
                        {new Date(log.timestamp).toLocaleString()}
                      </td>
                      <td className="py-3 px-4 font-medium">{log.user_name}</td>
                      <td className="py-3 px-4">
                        <span className="px-2 py-1 bg-info-light text-info rounded text-sm">
                          {log.action}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-text-secondary text-sm">{log.details}</td>
                      <td className="py-3 px-4 text-text-secondary text-sm">{log.ip_address || '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        )}

        {activeTab === 'settings' && (
          <Card className="p-6">
            <h2 className="text-2xl font-bold mb-4">System Settings</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2">System Name</label>
                <input
                  type="text"
                  defaultValue="REIMS 2.0"
                  className="w-full px-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-info"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Session Timeout (minutes)</label>
                <input
                  type="number"
                  defaultValue="30"
                  className="w-full px-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-info"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Max Upload Size (MB)</label>
                <input
                  type="number"
                  defaultValue="100"
                  className="w-full px-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-info"
                />
              </div>
              <Button variant="primary">Save Settings</Button>
            </div>
          </Card>
        )}

        {activeTab === 'billing' && (
          <div className="space-y-6">
            {/* Sub-tabs for Billing */}
            <div className="flex gap-2 border-b border-border">
              <button
                onClick={() => setBillingTab('overview')}
                className={`px-4 py-2 font-medium text-sm transition-colors ${
                  billingTab === 'overview'
                    ? 'text-info border-b-2 border-info'
                    : 'text-text-secondary hover:text-text-primary'
                }`}
              >
                Overview
              </button>
              <button
                onClick={() => setBillingTab('history')}
                className={`px-4 py-2 font-medium text-sm transition-colors ${
                  billingTab === 'history'
                    ? 'text-info border-b-2 border-info'
                    : 'text-text-secondary hover:text-text-primary'
                }`}
              >
                Billing History
              </button>
              <button
                onClick={() => setBillingTab('plans')}
                className={`px-4 py-2 font-medium text-sm transition-colors ${
                  billingTab === 'plans'
                    ? 'text-info border-b-2 border-info'
                    : 'text-text-secondary hover:text-text-primary'
                }`}
              >
                Plans
              </button>
            </div>

            {/* Billing Content */}
            {billingTab === 'overview' && <SubscriptionOverview />}
            {billingTab === 'history' && <BillingHistory />}
            {billingTab === 'plans' && <PlanManagement />}
          </div>
        )}
      </div>
    </div>
  );
}

