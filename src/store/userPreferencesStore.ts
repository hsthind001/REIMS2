import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface SavedView {
  id: string;
  name: string;
  page: string;
  filters: any;
  createdAt: Date;
}

export interface RecentAction {
  id: string;
  type: string;
  label: string;
  path: string;
  timestamp: Date;
}

export interface UserPreferencesStore {
  // Theme
  theme: 'light' | 'dark';
  setTheme: (theme: 'light' | 'dark') => void;
  toggleTheme: () => void;

  // Display preferences
  sidebarOpen: boolean;
  compactMode: boolean;
  showMiniCharts: boolean;

  setSidebarOpen: (open: boolean) => void;
  toggleSidebar: () => void;
  setCompactMode: (compact: boolean) => void;
  setShowMiniCharts: (show: boolean) => void;

  // Saved views
  savedViews: SavedView[];
  addSavedView: (view: Omit<SavedView, 'id' | 'createdAt'>) => void;
  removeSavedView: (id: string) => void;

  // Recent actions
  recentActions: RecentAction[];
  addRecentAction: (action: Omit<RecentAction, 'id' | 'timestamp'>) => void;
  clearRecentActions: () => void;

  // Notification preferences
  enableNotifications: boolean;
  notificationSound: boolean;
  emailDigest: 'daily' | 'weekly' | 'never';

  setEnableNotifications: (enable: boolean) => void;
  setNotificationSound: (enable: boolean) => void;
  setEmailDigest: (frequency: 'daily' | 'weekly' | 'never') => void;

  // Auto-refresh
  autoRefresh: boolean;
  autoRefreshInterval: number; // in milliseconds

  setAutoRefresh: (enable: boolean) => void;
  setAutoRefreshInterval: (interval: number) => void;

  // Dashboard customization
  dashboardLayout: 'default' | 'compact' | 'detailed';
  setDashboardLayout: (layout: 'default' | 'compact' | 'detailed') => void;

  // Data display
  currencyFormat: 'compact' | 'full';
  dateFormat: 'MM/DD/YYYY' | 'DD/MM/YYYY' | 'YYYY-MM-DD';
  numberFormat: 'us' | 'eu';

  setCurrencyFormat: (format: 'compact' | 'full') => void;
  setDateFormat: (format: 'MM/DD/YYYY' | 'DD/MM/YYYY' | 'YYYY-MM-DD') => void;
  setNumberFormat: (format: 'us' | 'eu') => void;
}

const MAX_RECENT_ACTIONS = 10;
const MAX_SAVED_VIEWS = 20;

export const useUserPreferencesStore = create<UserPreferencesStore>()(
  persist(
    (set, get) => ({
      // Initial state
      theme: 'light',
      sidebarOpen: true,
      compactMode: false,
      showMiniCharts: true,
      savedViews: [],
      recentActions: [],
      enableNotifications: true,
      notificationSound: true,
      emailDigest: 'weekly',
      autoRefresh: false,
      autoRefreshInterval: 60000, // 1 minute
      dashboardLayout: 'default',
      currencyFormat: 'compact',
      dateFormat: 'MM/DD/YYYY',
      numberFormat: 'us',

      // Theme actions
      setTheme: (theme) => {
        set({ theme });
        document.documentElement.setAttribute('data-theme', theme);
      },

      toggleTheme: () => {
        const currentTheme = get().theme;
        const newTheme = currentTheme === 'light' ? 'dark' : 'light';
        get().setTheme(newTheme);
      },

      // Display actions
      setSidebarOpen: (open) => set({ sidebarOpen: open }),

      toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),

      setCompactMode: (compact) => set({ compactMode: compact }),

      setShowMiniCharts: (show) => set({ showMiniCharts: show }),

      // Saved views actions
      addSavedView: (view) => {
        const newView: SavedView = {
          ...view,
          id: `view-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
          createdAt: new Date(),
        };

        set((state) => {
          const updatedViews = [newView, ...state.savedViews].slice(0, MAX_SAVED_VIEWS);
          return { savedViews: updatedViews };
        });
      },

      removeSavedView: (id) =>
        set((state) => ({
          savedViews: state.savedViews.filter((view) => view.id !== id)
        })),

      // Recent actions
      addRecentAction: (action) => {
        const newAction: RecentAction = {
          ...action,
          id: `action-${Date.now()}`,
          timestamp: new Date(),
        };

        set((state) => {
          // Remove duplicates and limit to MAX_RECENT_ACTIONS
          const filteredActions = state.recentActions.filter(
            (a) => a.path !== action.path || a.type !== action.type
          );
          const updatedActions = [newAction, ...filteredActions].slice(0, MAX_RECENT_ACTIONS);
          return { recentActions: updatedActions };
        });
      },

      clearRecentActions: () => set({ recentActions: [] }),

      // Notification actions
      setEnableNotifications: (enable) => set({ enableNotifications: enable }),

      setNotificationSound: (enable) => set({ notificationSound: enable }),

      setEmailDigest: (frequency) => set({ emailDigest: frequency }),

      // Auto-refresh actions
      setAutoRefresh: (enable) => set({ autoRefresh: enable }),

      setAutoRefreshInterval: (interval) => set({ autoRefreshInterval: interval }),

      // Dashboard layout
      setDashboardLayout: (layout) => set({ dashboardLayout: layout }),

      // Data format actions
      setCurrencyFormat: (format) => set({ currencyFormat: format }),

      setDateFormat: (format) => set({ dateFormat: format }),

      setNumberFormat: (format) => set({ numberFormat: format }),
    }),
    {
      name: 'user-preferences-storage',
      // Persist everything except recent actions (they're session-based)
      partialize: (state) => ({
        theme: state.theme,
        sidebarOpen: state.sidebarOpen,
        compactMode: state.compactMode,
        showMiniCharts: state.showMiniCharts,
        savedViews: state.savedViews,
        enableNotifications: state.enableNotifications,
        notificationSound: state.notificationSound,
        emailDigest: state.emailDigest,
        autoRefresh: state.autoRefresh,
        autoRefreshInterval: state.autoRefreshInterval,
        dashboardLayout: state.dashboardLayout,
        currencyFormat: state.currencyFormat,
        dateFormat: state.dateFormat,
        numberFormat: state.numberFormat,
      }),
    }
  )
);
