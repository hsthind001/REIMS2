import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { User, Organization } from '../types/api';

interface AuthState {
  user: User | null;
  currentOrganization: Organization | null;
  isAuthenticated: boolean;
  
  // Actions
  setUser: (user: User | null) => void;
  setOrganization: (org: Organization | null) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      currentOrganization: null,
      isAuthenticated: false,

      setUser: (user) => set((state) => {
        // If user is null, clear everything
        if (!user) {
          return { user: null, currentOrganization: null, isAuthenticated: false };
        }

        // If setting user, and no current org is selected, select the first one
        let nextOrg = state.currentOrganization;
        if (!nextOrg && user.organization_memberships?.length > 0) {
          nextOrg = user.organization_memberships[0].organization;
        } else if (nextOrg && user.organization_memberships?.length > 0) {
            // Verify current org is still valid for this user
            const isMember = user.organization_memberships.some(m => m.organization.id === nextOrg?.id);
            if (!isMember) {
                 nextOrg = user.organization_memberships[0].organization;
            }
        }

        return { user, isAuthenticated: true, currentOrganization: nextOrg };
      }),

      setOrganization: (org) => set({ currentOrganization: org }),

      logout: () => set({ user: null, currentOrganization: null, isAuthenticated: false }),
    }),
    {
      name: 'auth-storage', // name of item in the storage (must be unique)
      partialize: (state) => ({ currentOrganization: state.currentOrganization }), // Only persist organization preference
    }
  )
);
