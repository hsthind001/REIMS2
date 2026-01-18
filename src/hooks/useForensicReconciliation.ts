import { useQuery, useMutation, useQueryClient, keepPreviousData } from '@tanstack/react-query';
import { forensicReconciliationService } from '../lib/forensic_reconciliation';
import type { ForensicMatch, ForensicDiscrepancy } from '../lib/forensic_reconciliation';

// Query Keys
export const forensicKeys = {
  all: ['forensic'] as const,
  availability: (propertyId: number | null, periodId: number | null) => 
    [...forensicKeys.all, 'availability', propertyId, periodId] as const,
  dashboard: (propertyId: number | null, periodId: number | null) => 
    [...forensicKeys.all, 'dashboard', propertyId, periodId] as const,
  session: (sessionId: number | null) => 
    [...forensicKeys.all, 'session', sessionId] as const,
  matches: (sessionId: number | null, filters?: any) => 
    [...forensicKeys.all, 'matches', sessionId, filters] as const,
  discrepancies: (sessionId: number | null, filters?: any) => 
    [...forensicKeys.all, 'discrepancies', sessionId, filters] as const,
  health: (propertyId: number | null, periodId: number | null) => 
    [...forensicKeys.all, 'health', propertyId, periodId] as const,
};

export function useForensicDataAvailability(propertyId: number | null, periodId: number | null) {
  return useQuery({
    queryKey: forensicKeys.availability(propertyId, periodId),
    queryFn: () => forensicReconciliationService.checkDataAvailability(propertyId!, periodId!),
    enabled: !!propertyId && !!periodId,
    staleTime: 5 * 60 * 1000,
  });
}

export function useForensicDashboard(propertyId: number | null, periodId: number | null) {
  return useQuery({
    queryKey: forensicKeys.dashboard(propertyId, periodId),
    queryFn: () => forensicReconciliationService.getDashboard(propertyId!, periodId!),
    enabled: !!propertyId && !!periodId,
  });
}

export function useForensicSession(sessionId: number | null) {
  return useQuery({
    queryKey: forensicKeys.session(sessionId),
    queryFn: () => forensicReconciliationService.getSession(sessionId!),
    enabled: !!sessionId,
  });
}

type MatchesResponse = {
  matches: ForensicMatch[];
  total: number;
};

export function useForensicMatches(sessionId: number | null, filters: any = {}) {
  return useQuery<MatchesResponse>({
    queryKey: forensicKeys.matches(sessionId, filters),
    queryFn: () => forensicReconciliationService.getMatches(sessionId!, filters),
    enabled: !!sessionId,
    placeholderData: keepPreviousData,
  });
}

type DiscrepanciesResponse = {
  discrepancies: ForensicDiscrepancy[];
  total: number;
};

export function useForensicDiscrepancies(sessionId: number | null, filters: any = {}) {
  return useQuery<DiscrepanciesResponse>({
    queryKey: forensicKeys.discrepancies(sessionId, filters),
    queryFn: () => forensicReconciliationService.getDiscrepancies(sessionId!, filters),
    enabled: !!sessionId,
    placeholderData: keepPreviousData,
  });
}

export function useForensicHealthScore(propertyId: number | null, periodId: number | null) {
  return useQuery({
    queryKey: forensicKeys.health(propertyId, periodId),
    queryFn: () => forensicReconciliationService.getHealthScore(propertyId!, periodId!),
    enabled: !!propertyId && !!periodId,
  });
}

// Mutations
export function useForensicMutations() {
  const queryClient = useQueryClient();

  const createSessionMutation = useMutation({
    mutationFn: (params: { property_id: number; period_id: number; session_type?: string }) =>
      forensicReconciliationService.createSession(params),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: forensicKeys.all });
    },
  });

  const runReconciliationMutation = useMutation({
    mutationFn: (params: { sessionId: number; options?: any }) =>
      forensicReconciliationService.runReconciliation(params.sessionId, params.options),
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({ queryKey: forensicKeys.all });
      queryClient.invalidateQueries({ queryKey: forensicKeys.session(variables.sessionId) });
    },
  });

  const validateSessionMutation = useMutation({
    mutationFn: (sessionId: number) => forensicReconciliationService.validateSession(sessionId),
    onSuccess: (data, sessionId) => {
      queryClient.invalidateQueries({ queryKey: forensicKeys.all });
      queryClient.invalidateQueries({ queryKey: forensicKeys.session(sessionId) });
    },
  });

  const approveMatchMutation = useMutation({
    mutationFn: (params: { matchId: number; notes?: string }) =>
      forensicReconciliationService.approveMatch(params.matchId, { notes: params.notes }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: forensicKeys.all });
    },
  });

  const rejectMatchMutation = useMutation({
    mutationFn: (params: { matchId: number; reason: string }) =>
      forensicReconciliationService.rejectMatch(params.matchId, { reason: params.reason }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: forensicKeys.all });
    },
  });

  const resolveDiscrepancyMutation = useMutation({
    mutationFn: (params: { discrepancyId: number; notes: string; newValue?: number }) =>
      forensicReconciliationService.resolveDiscrepancy(params.discrepancyId, { resolution_notes: params.notes, new_value: params.newValue }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: forensicKeys.all });
    },
  });

  const completeSessionMutation = useMutation({
    mutationFn: (sessionId: number) => forensicReconciliationService.completeSession(sessionId),
    onSuccess: (data, sessionId) => {
      queryClient.invalidateQueries({ queryKey: forensicKeys.all });
      queryClient.invalidateQueries({ queryKey: forensicKeys.session(sessionId) });
    },
  });

  return {
    createSession: createSessionMutation,
    runReconciliation: runReconciliationMutation,
    validateSession: validateSessionMutation,
    approveMatch: approveMatchMutation,
    rejectMatch: rejectMatchMutation,
    resolveDiscrepancy: resolveDiscrepancyMutation,
    completeSession: completeSessionMutation,
  };
}
