/**
 * Organization Settings - Org-level admin (P2)
 * Manage members, view audit log. Requires org admin/owner role.
 */
import { useState, useEffect } from 'react';
import { Users, FileText, Plus, Trash2, Edit2, RefreshCw } from 'lucide-react';
import { Card, Button } from '../components/design-system';

const API_BASE = (import.meta.env.VITE_API_URL || 'http://localhost:8000') + '/api/v1';

interface Member {
  id: number;
  user_id: number;
  username: string;
  email: string;
  role: string;
}

interface AuditEntry {
  id: number;
  action: string;
  user_id: number | null;
  resource_type: string | null;
  resource_id: string | null;
  details: string | null;
  created_at: string;
}

type Tab = 'members' | 'audit';

export default function OrganizationSettings() {
  const [tab, setTab] = useState<Tab>('members');
  const [members, setMembers] = useState<Member[]>([]);
  const [audit, setAudit] = useState<AuditEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showAdd, setShowAdd] = useState(false);
  const [addUserId, setAddUserId] = useState('');
  const [addRole, setAddRole] = useState('viewer');
  const [editingMember, setEditingMember] = useState<Member | null>(null);
  const [editRole, setEditRole] = useState('');

  const orgId = (window as any).__REIMS_ORG_ID__ || localStorage.getItem('X-Organization-ID') || '';

  useEffect(() => {
    if (tab === 'members') loadMembers();
    else loadAudit();
  }, [tab]);

  const loadMembers = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await fetch(`${API_BASE}/organization/members/`, { credentials: 'include' });
      if (!res.ok) throw new Error(res.status === 403 ? 'Admin access required' : 'Failed to load');
      const data = await res.json();
      setMembers(data || []);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const loadAudit = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await fetch(`${API_BASE}/organization/members/audit?limit=100`, { credentials: 'include' });
      if (!res.ok) throw new Error(res.status === 403 ? 'Admin access required' : 'Failed to load');
      const data = await res.json();
      setAudit(data || []);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleAddMember = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!addUserId.trim()) return;
    try {
      const res = await fetch(`${API_BASE}/organization/members/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ user_id: parseInt(addUserId, 10), role: addRole }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to add member');
      }
      setShowAdd(false);
      setAddUserId('');
      setAddRole('viewer');
      loadMembers();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleUpdateRole = async () => {
    if (!editingMember || !editRole) return;
    try {
      const res = await fetch(`${API_BASE}/organization/members/${editingMember.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ role: editRole }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to update');
      }
      setEditingMember(null);
      loadMembers();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleRemoveMember = async (m: Member) => {
    if (!confirm(`Remove ${m.username} from the organization?`)) return;
    try {
      const res = await fetch(`${API_BASE}/organization/members/${m.id}`, {
        method: 'DELETE',
        credentials: 'include',
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to remove');
      }
      loadMembers();
    } catch (e: any) {
      setError(e.message);
    }
  };

  return (
    <div className="min-h-screen bg-background p-6">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-2xl font-bold text-text-primary mb-2">Organization Settings</h1>
        <p className="text-text-secondary mb-6">Manage team members and view audit log</p>

        {error && (
          <div className="mb-4 p-4 bg-destructive/10 text-destructive rounded-lg">{error}</div>
        )}

        <div className="flex gap-2 border-b border-border mb-6">
          <button
            onClick={() => setTab('members')}
            className={`px-4 py-2 font-medium flex items-center gap-2 ${
              tab === 'members' ? 'text-info border-b-2 border-info' : 'text-text-secondary'
            }`}
          >
            <Users className="w-4 h-4" /> Members
          </button>
          <button
            onClick={() => setTab('audit')}
            className={`px-4 py-2 font-medium flex items-center gap-2 ${
              tab === 'audit' ? 'text-info border-b-2 border-info' : 'text-text-secondary'
            }`}
          >
            <FileText className="w-4 h-4" /> Audit Log
          </button>
        </div>

        {tab === 'members' && (
          <Card className="p-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-lg font-semibold">Team Members</h2>
              <Button variant="primary" size="sm" onClick={() => setShowAdd(true)} icon={<Plus className="w-4 h-4" />}>
                Add Member
              </Button>
            </div>
            {showAdd && (
              <form onSubmit={handleAddMember} className="mb-4 p-4 bg-muted rounded-lg flex flex-wrap gap-3 items-end">
                <div>
                  <label className="block text-sm text-text-secondary mb-1">User ID</label>
                  <input
                    type="number"
                    value={addUserId}
                    onChange={(e) => setAddUserId(e.target.value)}
                    placeholder="User ID"
                    className="border border-border rounded px-3 py-2 w-32"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm text-text-secondary mb-1">Role</label>
                  <select
                    value={addRole}
                    onChange={(e) => setAddRole(e.target.value)}
                    className="border border-border rounded px-3 py-2"
                  >
                    <option value="viewer">Viewer</option>
                    <option value="editor">Editor</option>
                    <option value="admin">Admin</option>
                    <option value="owner">Owner</option>
                  </select>
                </div>
                <Button type="submit" variant="primary">Add</Button>
                <Button type="button" variant="outline" onClick={() => setShowAdd(false)}>Cancel</Button>
              </form>
            )}
            {loading ? (
              <div className="py-8 text-center text-text-secondary">Loading...</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-border">
                      <th className="text-left py-3 px-2">User</th>
                      <th className="text-left py-3 px-2">Role</th>
                      <th className="text-right py-3 px-2">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {members.map((m) => (
                      <tr key={m.id} className="border-b border-border">
                        <td className="py-3 px-2">
                          <div className="font-medium">{m.username}</div>
                          <div className="text-sm text-text-secondary">{m.email}</div>
                        </td>
                        <td className="py-3 px-2">
                          {editingMember?.id === m.id ? (
                            <div className="flex gap-2 items-center">
                              <select
                                value={editRole}
                                onChange={(e) => setEditRole(e.target.value)}
                                className="border border-border rounded px-2 py-1 text-sm"
                              >
                                <option value="viewer">Viewer</option>
                                <option value="editor">Editor</option>
                                <option value="admin">Admin</option>
                                <option value="owner">Owner</option>
                              </select>
                              <Button size="sm" variant="primary" onClick={handleUpdateRole}>Save</Button>
                              <Button size="sm" variant="outline" onClick={() => setEditingMember(null)}>Cancel</Button>
                            </div>
                          ) : (
                            <span className="px-2 py-1 bg-info-light text-info rounded text-sm">{m.role}</span>
                          )}
                        </td>
                        <td className="py-3 px-2 text-right">
                          {editingMember?.id !== m.id && (
                            <>
                              <Button size="sm" variant="ghost" icon={<Edit2 className="w-4 h-4" />}
                                onClick={() => { setEditingMember(m); setEditRole(m.role); }} />
                              <Button size="sm" variant="ghost" icon={<Trash2 className="w-4 h-4 text-destructive" />}
                                onClick={() => handleRemoveMember(m)} disabled={m.role === 'owner'} />
                            </>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        )}

        {tab === 'audit' && (
          <Card className="p-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-lg font-semibold">Audit Log</h2>
              <Button variant="outline" size="sm" onClick={loadAudit} icon={<RefreshCw className="w-4 h-4" />}>
                Refresh
              </Button>
            </div>
            {loading ? (
              <div className="py-8 text-center text-text-secondary">Loading...</div>
            ) : (
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {audit.length === 0 ? (
                  <p className="text-text-secondary py-4">No audit entries yet.</p>
                ) : (
                  audit.map((a) => (
                    <div key={a.id} className="flex flex-wrap gap-2 py-2 border-b border-border text-sm">
                      <span className="font-mono text-info">{a.action}</span>
                      <span className="text-text-secondary">{a.details || '-'}</span>
                      <span className="text-text-muted ml-auto">{new Date(a.created_at).toLocaleString()}</span>
                    </div>
                  ))
                )}
              </div>
            )}
          </Card>
        )}
      </div>
    </div>
  );
}
