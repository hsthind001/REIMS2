import { useState, useEffect } from 'react';

const API_BASE_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000') + '/api/v1';

interface Account {
  id: number;
  account_code: string;
  account_name: string;
  account_type: 'Asset' | 'Liability' | 'Equity' | 'Revenue' | 'Expense';
  sub_type?: string;
  parent_account_id?: number;
  is_active: boolean;
  usage_count?: number;
  total_amount?: number;
}

interface AccountDetails extends Account {
  mapped_fields: string[];
  transaction_count: number;
  total_amount: number;
  properties_count: number;
}

export default function ChartOfAccounts() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [selectedAccount, setSelectedAccount] = useState<AccountDetails | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showAddModal, setShowAddModal] = useState(false);
  const [filterType, setFilterType] = useState<string>('all');

  const [newAccount, setNewAccount] = useState({
    account_code: '',
    account_name: '',
    account_type: 'Asset' as const,
    sub_type: '',
    parent_account_id: undefined as number | undefined,
  });

  useEffect(() => {
    loadAccounts();
  }, []);

  const loadAccounts = async () => {
    try {
      setLoading(true);
      setError('');
      const response = await fetch(`${API_BASE_URL}/chart_of_accounts`, {
        credentials: 'include'
      });

      if (!response.ok) throw new Error('Failed to load chart of accounts');

      const data = await response.json();
      setAccounts(data.accounts || []);
    } catch (err) {
      console.error('Failed to load chart of accounts:', err);
      setError('Failed to load chart of accounts');
    } finally {
      setLoading(false);
    }
  };

  const loadAccountDetails = async (accountId: number) => {
    try {
      const response = await fetch(`${API_BASE_URL}/chart_of_accounts/${accountId}`, {
        credentials: 'include'
      });

      if (!response.ok) throw new Error('Failed to load account details');

      const data = await response.json();
      setSelectedAccount(data);
    } catch (err) {
      console.error('Failed to load account details:', err);
      setError('Failed to load account details');
    }
  };

  const handleCreateAccount = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      setError('');
      const response = await fetch(`${API_BASE_URL}/chart_of_accounts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(newAccount)
      });

      if (!response.ok) throw new Error('Failed to create account');

      setShowAddModal(false);
      setNewAccount({
        account_code: '',
        account_name: '',
        account_type: 'Asset',
        sub_type: '',
        parent_account_id: undefined,
      });
      loadAccounts();
    } catch (err) {
      console.error('Failed to create account:', err);
      setError('Failed to create account');
    }
  };

  const handleDeleteAccount = async (accountId: number) => {
    if (!confirm('Are you sure you want to delete this account?')) return;

    try {
      setError('');
      const response = await fetch(`${API_BASE_URL}/chart_of_accounts/${accountId}`, {
        method: 'DELETE',
        credentials: 'include'
      });

      if (!response.ok) throw new Error('Failed to delete account');

      setSelectedAccount(null);
      loadAccounts();
    } catch (err) {
      console.error('Failed to delete account:', err);
      setError('Failed to delete account');
    }
  };

  const getAccountIcon = (type: string) => {
    switch (type) {
      case 'Asset': return '📊';
      case 'Liability': return '💳';
      case 'Equity': return '💰';
      case 'Revenue': return '💵';
      case 'Expense': return '💸';
      default: return '📄';
    }
  };

  const filteredAccounts = filterType === 'all'
    ? accounts
    : accounts.filter(acc => acc.account_type === filterType);

  const groupedAccounts = filteredAccounts.reduce((groups, account) => {
    const type = account.account_type;
    if (!groups[type]) groups[type] = [];
    groups[type].push(account);
    return groups;
  }, {} as Record<string, Account[]>);

  if (loading) {
    return (
      <div className="page">
        <div className="loading">Loading chart of accounts...</div>
      </div>
    );
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1>Chart of Accounts Manager</h1>
        <p className="page-subtitle">Manage account hierarchy and financial categorization</p>
      </div>

      {error && <div className="error-message">{error}</div>}

      <div className="page-content">
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <div>
              <label style={{ marginRight: '0.5rem' }}>Filter by Type:</label>
              <select
                className="input"
                value={filterType}
                onChange={(e) => setFilterType(e.target.value)}
                style={{ width: 'auto', display: 'inline-block' }}
              >
                <option value="all">All Accounts</option>
                <option value="Asset">Assets</option>
                <option value="Liability">Liabilities</option>
                <option value="Equity">Equity</option>
                <option value="Revenue">Revenue</option>
                <option value="Expense">Expenses</option>
              </select>
            </div>

            <div>
              <button className="btn btn-primary" onClick={() => setShowAddModal(true)}>
                + Add Account
              </button>
              <button className="btn btn-secondary" style={{ marginLeft: '0.5rem' }}>
                Import COA Template
              </button>
              <button className="btn btn-secondary" style={{ marginLeft: '0.5rem' }}>
                Export to Excel
              </button>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
            {/* Account Tree */}
            <div>
              <h3>Account Tree</h3>
              <div style={{ maxHeight: '70vh', overflowY: 'auto', border: '1px solid var(--border-color)', borderRadius: '0.5rem', padding: '1rem' }}>
                {Object.entries(groupedAccounts).map(([type, accts]) => (
                  <div key={type} style={{ marginBottom: '1.5rem' }}>
                    <div style={{ fontWeight: 'bold', fontSize: '1.1rem', marginBottom: '0.5rem', color: 'var(--primary-color)' }}>
                      {getAccountIcon(type)} {type}s
                    </div>
                    <div style={{ paddingLeft: '1rem' }}>
                      {accts.map(account => (
                        <div
                          key={account.id}
                          style={{
                            padding: '0.5rem',
                            cursor: 'pointer',
                            borderRadius: '0.25rem',
                            background: selectedAccount?.id === account.id ? 'var(--primary-light)' : 'transparent',
                            marginBottom: '0.25rem',
                          }}
                          onClick={() => loadAccountDetails(account.id)}
                        >
                          <code style={{ marginRight: '0.5rem', color: 'var(--text-secondary)' }}>
                            {account.account_code}
                          </code>
                          <span>{account.account_name}</span>
                          {!account.is_active && (
                            <span style={{ marginLeft: '0.5rem', color: 'var(--error-color)', fontSize: '0.8rem' }}>
                              (Inactive)
                            </span>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                ))}

                {filteredAccounts.length === 0 && (
                  <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-secondary)' }}>
                    No accounts found
                  </div>
                )}
              </div>
            </div>

            {/* Account Details */}
            <div>
              {selectedAccount ? (
                <div>
                  <h3>Account Details</h3>
                  <div style={{ border: '1px solid var(--border-color)', borderRadius: '0.5rem', padding: '1.5rem' }}>
                    <div className="form-group">
                      <label>Account Code</label>
                      <div><strong>{selectedAccount.account_code}</strong></div>
                    </div>

                    <div className="form-group">
                      <label>Account Name</label>
                      <div><strong>{selectedAccount.account_name}</strong></div>
                    </div>

                    <div className="form-group">
                      <label>Type</label>
                      <div>{getAccountIcon(selectedAccount.account_type)} {selectedAccount.account_type}</div>
                    </div>

                    {selectedAccount.sub_type && (
                      <div className="form-group">
                        <label>Sub-type</label>
                        <div>{selectedAccount.sub_type}</div>
                      </div>
                    )}

                    <div className="form-group">
                      <label>Status</label>
                      <div>
                        <span style={{ color: selectedAccount.is_active ? 'var(--success-color)' : 'var(--error-color)' }}>
                          {selectedAccount.is_active ? '✅ Active' : '❌ Inactive'}
                        </span>
                      </div>
                    </div>

                    <hr style={{ margin: '1.5rem 0' }} />

                    <div className="form-group">
                      <label>Mapped Fields</label>
                      <div>
                        {selectedAccount.mapped_fields?.length > 0 ? (
                          <ul style={{ margin: 0, paddingLeft: '1.5rem' }}>
                            {selectedAccount.mapped_fields.map((field, idx) => (
                              <li key={idx}>{field}</li>
                            ))}
                          </ul>
                        ) : (
                          <span style={{ color: 'var(--text-secondary)' }}>No mapped fields</span>
                        )}
                      </div>
                    </div>

                    <div className="form-group">
                      <label>Usage (Last 12 months)</label>
                      <div>
                        <div>Transactions: <strong>{selectedAccount.transaction_count || 0}</strong></div>
                        <div>Total Amount: <strong>${selectedAccount.total_amount?.toLocaleString() || 0}</strong></div>
                        <div>Properties: <strong>{selectedAccount.properties_count || 0}</strong></div>
                      </div>
                    </div>

                    <div style={{ marginTop: '1.5rem', display: 'flex', gap: '0.5rem' }}>
                      <button className="btn btn-primary">Edit</button>
                      <button className="btn btn-secondary">
                        {selectedAccount.is_active ? 'Deactivate' : 'Activate'}
                      </button>
                      <button className="btn btn-secondary">View Transactions</button>
                      <button
                        className="btn"
                        style={{ background: 'var(--error-color)', color: 'white' }}
                        onClick={() => handleDeleteAccount(selectedAccount.id)}
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                </div>
              ) : (
                <div style={{ textAlign: 'center', padding: '4rem', color: 'var(--text-secondary)' }}>
                  <p>Select an account from the tree to view details</p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="card">
          <h3>Quick Actions</h3>
          <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
            <button className="btn btn-secondary">Import Standard COA</button>
            <button className="btn btn-secondary">Import from QuickBooks</button>
            <button className="btn btn-secondary">Bulk Edit Accounts</button>
            <button className="btn btn-secondary">View Audit Trail</button>
          </div>
        </div>
      </div>

      {/* Add Account Modal */}
      {showAddModal && (
        <div className="modal-overlay" onClick={() => setShowAddModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2>Add New Account</h2>
            <form onSubmit={handleCreateAccount}>
              <div className="form-group">
                <label>Account Code*</label>
                <input
                  type="text"
                  className="input"
                  value={newAccount.account_code}
                  onChange={(e) => setNewAccount({ ...newAccount, account_code: e.target.value })}
                  placeholder="e.g., 4010-0000"
                  required
                />
              </div>

              <div className="form-group">
                <label>Account Name*</label>
                <input
                  type="text"
                  className="input"
                  value={newAccount.account_name}
                  onChange={(e) => setNewAccount({ ...newAccount, account_name: e.target.value })}
                  placeholder="e.g., Rental Income"
                  required
                />
              </div>

              <div className="form-group">
                <label>Account Type*</label>
                <select
                  className="input"
                  value={newAccount.account_type}
                  onChange={(e) => setNewAccount({ ...newAccount, account_type: e.target.value as any })}
                  required
                >
                  <option value="Asset">Asset</option>
                  <option value="Liability">Liability</option>
                  <option value="Equity">Equity</option>
                  <option value="Revenue">Revenue</option>
                  <option value="Expense">Expense</option>
                </select>
              </div>

              <div className="form-group">
                <label>Sub-type</label>
                <input
                  type="text"
                  className="input"
                  value={newAccount.sub_type}
                  onChange={(e) => setNewAccount({ ...newAccount, sub_type: e.target.value })}
                  placeholder="e.g., Operating Income"
                />
              </div>

              <div style={{ display: 'flex', gap: '0.5rem', marginTop: '1.5rem' }}>
                <button type="submit" className="btn btn-primary">Create Account</button>
                <button type="button" className="btn btn-secondary" onClick={() => setShowAddModal(false)}>
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
