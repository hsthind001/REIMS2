import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { Property } from '../types/api';

export interface FilterState {
  search: string;
  minValue?: number;
  maxValue?: number;
  minDSCR?: number;
  maxDSCR?: number;
  status?: string[];
  city?: string[];
  state?: string[];
  minNOI?: number;
  minOccupancy?: number;
  minUnits?: number;
  maxLTV?: number;
  tags?: string[];
}

export interface PortfolioStore {
  // Selected state
  selectedProperty: Property | null;
  selectedYear: number;
  selectedMonth: number;
  viewMode: 'list' | 'map' | 'grid';

  // Filters
  filters: FilterState;

  // Comparison mode
  comparisonMode: boolean;
  selectedForComparison: Set<number>; // property IDs

  // Actions
  setSelectedProperty: (property: Property | null) => void;
  setSelectedYear: (year: number) => void;
  setSelectedMonth: (month: number) => void;
  setViewMode: (mode: 'list' | 'map' | 'grid') => void;
  setFilters: (filters: Partial<FilterState>) => void;
  resetFilters: () => void;

  // Comparison actions
  toggleComparisonMode: () => void;
  addToComparison: (propertyId: number) => void;
  removeFromComparison: (propertyId: number) => void;
  clearComparison: () => void;
}

const defaultFilters: FilterState = {
  search: '',
  minValue: undefined,
  maxValue: undefined,
  minDSCR: undefined,
  maxDSCR: undefined,
  status: undefined,
  city: undefined,
  state: undefined,
  minNOI: undefined,
  minOccupancy: undefined,
  minUnits: undefined,
  maxLTV: undefined,
  tags: undefined,
};

export const usePortfolioStore = create<PortfolioStore>()(
  persist(
    (set, get) => ({
      // Initial state
      selectedProperty: null,
      selectedYear: new Date().getFullYear(),
      selectedMonth: new Date().getMonth() + 1,
      viewMode: 'grid',
      filters: defaultFilters,
      comparisonMode: false,
      selectedForComparison: new Set<number>(),

      // Actions
      setSelectedProperty: (property) => set({ selectedProperty: property }),

      setSelectedYear: (year) => set({ selectedYear: year }),

      setSelectedMonth: (month) => set({ selectedMonth: month }),

      setViewMode: (mode) => set({ viewMode: mode }),

      setFilters: (newFilters) =>
        set((state) => ({
          filters: { ...state.filters, ...newFilters }
        })),

      resetFilters: () => set({ filters: defaultFilters }),

      toggleComparisonMode: () =>
        set((state) => ({
          comparisonMode: !state.comparisonMode,
          selectedForComparison: !state.comparisonMode ? new Set<number>() : state.selectedForComparison
        })),

      addToComparison: (propertyId) =>
        set((state) => {
          const newSet = new Set(state.selectedForComparison);
          newSet.add(propertyId);
          return { selectedForComparison: newSet };
        }),

      removeFromComparison: (propertyId) =>
        set((state) => {
          const newSet = new Set(state.selectedForComparison);
          newSet.delete(propertyId);
          return { selectedForComparison: newSet };
        }),

      clearComparison: () => set({ selectedForComparison: new Set<number>() }),
    }),
    {
      name: 'portfolio-storage',
      partialize: (state) => ({
        selectedYear: state.selectedYear,
        selectedMonth: state.selectedMonth,
        viewMode: state.viewMode,
        filters: state.filters,
      }),
    }
  )
);
