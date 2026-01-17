import React, { useEffect } from 'react';
import { useAuthStore } from '../store/authStore';

export const OrganizationSwitcher: React.FC = () => {
  const { user, currentOrganization, setOrganization } = useAuthStore();

  if (!user || !user.organization_memberships || user.organization_memberships.length === 0) {
    return null;
  }

  // Ensure currentOrganization is set if available
  useEffect(() => {
    if (!currentOrganization && user.organization_memberships.length > 0) {
        setOrganization(user.organization_memberships[0].organization);
    }
  }, [currentOrganization, user, setOrganization]);

  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const orgId = parseInt(e.target.value);
    const membership = user.organization_memberships.find(m => m.organization.id === orgId);
    if (membership) {
      setOrganization(membership.organization);
      // Optional: Reload page or trigger data refresh if generic query invalidation isn't set up
      window.location.reload(); 
    }
  };

  if (user.organization_memberships.length <= 1) {
     // If only one org, just show the name, no switcher needed yet, or a disabled one?
     // Better to show the name so context is clear.
     return (
         <div className="org-badge" style={{ 
             padding: '0.375rem 0.75rem',
             backgroundColor: 'var(--bg-tertiary)',
             borderRadius: '0.375rem',
             fontSize: '0.875rem',
             color: 'var(--text-secondary)',
             marginRight: '0.5rem',
             display: 'flex',
             alignItems: 'center',
             gap: '0.5rem'
         }}>
             <span>🏢</span>
             <span style={{ fontWeight: 500 }}>{currentOrganization?.name || user.organization_memberships[0].organization.name}</span>
         </div>
     );
  }

  return (
    <div className="org-switcher" style={{ marginRight: '0.5rem' }}>
      <select 
        value={currentOrganization?.id || ''} 
        onChange={handleChange}
        style={{
            padding: '0.375rem 0.75rem',
            borderRadius: '0.375rem',
            border: '1px solid var(--border-color)',
            backgroundColor: 'var(--bg-primary)',
            color: 'var(--text-primary)',
            fontSize: '0.875rem',
            cursor: 'pointer',
            maxWidth: '200px',
            textOverflow: 'ellipsis'
        }}
      >
        {user.organization_memberships.map((membership) => (
          <option key={membership.organization.id} value={membership.organization.id}>
             🏢 {membership.organization.name}
          </option>
        ))}
      </select>
    </div>
  );
};
