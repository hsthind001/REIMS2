/**
 * Workflow Locks API Service
 * Functions for managing workflow locks
 */

const API_BASE_URL = import.meta.env.VITE_API_URL 
  ? `${import.meta.env.VITE_API_URL}/api/v1` 
  : 'http://localhost:8000/api/v1';

// Enums
export enum LockReason {
  DSCR_BREACH = 'DSCR_BREACH',
  OCCUPANCY_THRESHOLD = 'OCCUPANCY_THRESHOLD',
  COVENANT_VIOLATION = 'COVENANT_VIOLATION',
  COMMITTEE_REVIEW = 'COMMITTEE_REVIEW',
  FINANCIAL_ANOMALY = 'FINANCIAL_ANOMALY',
  VARIANCE_BREACH = 'VARIANCE_BREACH',
  MANUAL_HOLD = 'MANUAL_HOLD',
  DATA_QUALITY_ISSUE = 'DATA_QUALITY_ISSUE',
}

export enum LockScope {
  PROPERTY_ALL = 'PROPERTY_ALL',
  FINANCIAL_UPDATES = 'FINANCIAL_UPDATES',
  REPORTING_ONLY = 'REPORTING_ONLY',
  TRANSACTION_APPROVAL = 'TRANSACTION_APPROVAL',
  DATA_ENTRY = 'DATA_ENTRY',
}

export enum LockStatus {
  ACTIVE = 'ACTIVE',
  PENDING_APPROVAL = 'PENDING_APPROVAL',
  APPROVED = 'APPROVED',
  REJECTED = 'REJECTED',
  RELEASED = 'RELEASED',
}

// Label dictionaries
export const LockReasonLabels: Record<string, string> = {
  DSCR_BREACH: 'DSCR Breach',
  OCCUPANCY_THRESHOLD: 'Occupancy Threshold',
  COVENANT_VIOLATION: 'Covenant Violation',
  COMMITTEE_REVIEW: 'Committee Review',
  FINANCIAL_ANOMALY: 'Financial Anomaly',
  VARIANCE_BREACH: 'Variance Breach',
  MANUAL_HOLD: 'Manual Hold',
  DATA_QUALITY_ISSUE: 'Data Quality Issue',
};

export const LockScopeLabels: Record<string, string> = {
  PROPERTY_ALL: 'All Property Operations',
  FINANCIAL_UPDATES: 'Financial Updates',
  REPORTING_ONLY: 'Reporting Only',
  TRANSACTION_APPROVAL: 'Transaction Approval',
  DATA_ENTRY: 'Data Entry',
};

export const LockStatusLabels: Record<string, string> = {
  ACTIVE: 'Active',
  PENDING_APPROVAL: 'Pending Approval',
  APPROVED: 'Approved',
  REJECTED: 'Rejected',
  RELEASED: 'Released',
};

// Interfaces
export interface WorkflowLock {
  id: number;
  property_id: number;
  alert_id?: number;
  lock_reason: string;
  lock_scope: string;
  status: string;
  title: string;
  description?: string;
  requires_committee_approval: boolean;
  approval_committee?: string;
  locked_at: string;
  unlocked_at?: string;
  approved_at?: string;
  rejected_at?: string;
  locked_by: number;
  unlocked_by?: number;
  approved_by?: number;
  rejected_by?: number;
  resolution_notes?: string;
  rejection_reason?: string;
  auto_release_conditions?: any;
  auto_released: boolean;
  lock_metadata?: any;
  br_id?: string;
  created_at: string;
  updated_at: string;
}

export interface CreateLockRequest {
  property_id: number;
  lock_reason: string;
  lock_scope: string;
  title: string;
  description: string;
  locked_by: number;
  alert_id?: number;
  approval_committee?: string;
  br_id?: string;
}

export interface ReleaseLockRequest {
  unlocked_by: number;
  resolution_notes?: string;
}

export interface ApproveLockRequest {
  approved_by: number;
  resolution_notes?: string;
}

export interface RejectLockRequest {
  rejected_by: number;
  rejection_reason: string;
}

export interface OperationCheckResult {
  success: boolean;
  allowed: boolean;
  property_id: number;
  operation: string;
  blocking_locks: WorkflowLock[];
  reason: string;
  message?: string;
}

/**
 * Get all workflow locks for a property
 */
export async function getPropertyLocks(
  propertyId: number,
  status?: string
): Promise<WorkflowLock[]> {
  const url = new URL(`${API_BASE_URL}/workflow-locks/properties/${propertyId}`);
  if (status) {
    url.searchParams.append('status', status);
  }

  const response = await fetch(url.toString(), {
    credentials: 'include',
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch workflow locks: ${response.statusText}`);
  }

  const data = await response.json();
  return data.locks || [];
}

/**
 * Get a specific workflow lock by ID
 */
export async function getLockDetails(lockId: number): Promise<WorkflowLock> {
  const response = await fetch(`${API_BASE_URL}/workflow-locks/${lockId}`, {
    credentials: 'include',
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch lock details: ${response.statusText}`);
  }

  const data = await response.json();
  return data;
}

/**
 * Create a new workflow lock
 */
export async function createLock(request: CreateLockRequest): Promise<WorkflowLock> {
  const response = await fetch(`${API_BASE_URL}/workflow-locks/create`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'include',
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || `Failed to create lock: ${response.statusText}`);
  }

  const result = await response.json();
  if (!result.success) {
    throw new Error(result.error || 'Failed to create lock');
  }
  return result.lock;
}

/**
 * Release/unlock a workflow lock
 */
export async function releaseLock(
  lockId: number,
  request: ReleaseLockRequest
): Promise<WorkflowLock> {
  const response = await fetch(`${API_BASE_URL}/workflow-locks/${lockId}/release`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'include',
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || `Failed to release lock: ${response.statusText}`);
  }

  const result = await response.json();
  if (!result.success) {
    throw new Error(result.error || 'Failed to release lock');
  }
  return result.lock;
}

/**
 * Approve a workflow lock (committee approval)
 */
export async function approveLock(
  lockId: number,
  request: ApproveLockRequest
): Promise<WorkflowLock> {
  const response = await fetch(`${API_BASE_URL}/workflow-locks/${lockId}/approve`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'include',
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || `Failed to approve lock: ${response.statusText}`);
  }

  const result = await response.json();
  if (!result.success) {
    throw new Error(result.error || 'Failed to approve lock');
  }
  return result.lock;
}

/**
 * Reject a workflow lock (committee rejection)
 */
export async function rejectLock(
  lockId: number,
  request: RejectLockRequest
): Promise<WorkflowLock> {
  const response = await fetch(`${API_BASE_URL}/workflow-locks/${lockId}/reject`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'include',
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || `Failed to reject lock: ${response.statusText}`);
  }

  const result = await response.json();
  if (!result.success) {
    throw new Error(result.error || 'Failed to reject lock');
  }
  return result.lock;
}

/**
 * Check if an operation is allowed for a property
 */
export async function checkOperationAllowed(
  propertyId: number,
  operation: string
): Promise<OperationCheckResult> {
  const response = await fetch(`${API_BASE_URL}/workflow-locks/check-operation`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'include',
    body: JSON.stringify({
      property_id: propertyId,
      operation: operation,
    }),
  });

  if (!response.ok) {
    throw new Error(`Failed to check operation: ${response.statusText}`);
  }

  const data = await response.json();
  return {
    success: data.success ?? true,
    allowed: data.allowed,
    property_id: data.property_id ?? propertyId,
    operation: data.operation ?? operation,
    blocking_locks: data.blocking_locks || [],
    reason: data.reason || '',
    message: data.message,
  };
}

/**
 * Get all locks pending committee approval
 */
export async function getPendingApprovals(committee?: string): Promise<{ success: boolean; committee: string; locks: WorkflowLock[]; total: number }> {
  const url = new URL(`${API_BASE_URL}/workflow-locks/pending-approvals`);
  if (committee) {
    url.searchParams.append('committee', committee);
  }

  const response = await fetch(url.toString(), {
    credentials: 'include',
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch pending approvals: ${response.statusText}`);
  }

  const data = await response.json();
  return {
    success: data.success ?? true,
    committee: data.committee || 'All',
    locks: data.locks || [],
    total: data.total || 0,
  };
}

/**
 * Get statistics about workflow locks
 */
export async function getStatistics(): Promise<{ success: boolean; statistics: any }> {
  const response = await fetch(`${API_BASE_URL}/workflow-locks/statistics/summary`, {
    credentials: 'include',
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch statistics: ${response.statusText}`);
  }

  const data = await response.json();
  return {
    success: data.success ?? true,
    statistics: data.statistics || {},
  };
}

// Store function references after they're defined to avoid naming conflicts in class methods
const workflowLockFunctions = {
  createLock,
  releaseLock,
  approveLock,
  rejectLock,
  getPropertyLocks,
  getPendingApprovals,
  getLockDetails,
  getStatistics,
  checkOperationAllowed,
};

/**
 * WorkflowLockService class wrapper for convenience
 * Provides class-based interface while using the function exports
 */
class WorkflowLockService {
  async createLock(request: CreateLockRequest): Promise<{ success: boolean; lock?: WorkflowLock; message?: string; error?: string }> {
    try {
      const lock = await workflowLockFunctions.createLock(request);
      return { success: true, lock, message: 'Workflow lock created successfully' };
    } catch (error: any) {
      return { success: false, error: error.message || 'Failed to create lock' };
    }
  }

  async releaseLock(lockId: number, request: ReleaseLockRequest): Promise<{ success: boolean; message?: string; error?: string }> {
    try {
      await workflowLockFunctions.releaseLock(lockId, request);
      return { success: true, message: 'Workflow lock released successfully' };
    } catch (error: any) {
      return { success: false, error: error.message || 'Failed to release lock' };
    }
  }

  async approveLock(lockId: number, request: ApproveLockRequest): Promise<{ success: boolean; message?: string; error?: string }> {
    try {
      await workflowLockFunctions.approveLock(lockId, request);
      return { success: true, message: 'Workflow lock approved successfully' };
    } catch (error: any) {
      return { success: false, error: error.message || 'Failed to approve lock' };
    }
  }

  async rejectLock(lockId: number, request: RejectLockRequest): Promise<{ success: boolean; message?: string; error?: string }> {
    try {
      await workflowLockFunctions.rejectLock(lockId, request);
      return { success: true, message: 'Workflow lock rejected successfully' };
    } catch (error: any) {
      return { success: false, error: error.message || 'Failed to reject lock' };
    }
  }

  async checkOperation(request: { property_id: number; operation: string }): Promise<OperationCheckResult> {
    return workflowLockFunctions.checkOperationAllowed(request.property_id, request.operation);
  }

  async getPropertyLocks(propertyId: number, status?: string): Promise<{ success: boolean; property_id: number; property_name?: string; locks: WorkflowLock[]; total: number }> {
    try {
      const locks = await workflowLockFunctions.getPropertyLocks(propertyId, status);
      return {
        success: true,
        property_id: propertyId,
        locks,
        total: locks.length,
      };
    } catch (error: any) {
      return { success: false, property_id: propertyId, locks: [], total: 0 };
    }
  }

  async getPendingApprovals(committee?: string): Promise<{ success: boolean; committee: string; locks: WorkflowLock[]; total: number }> {
    return workflowLockFunctions.getPendingApprovals(committee);
  }

  async getLock(lockId: number): Promise<WorkflowLock> {
    return workflowLockFunctions.getLockDetails(lockId);
  }

  async getStatistics(): Promise<{ success: boolean; statistics: any }> {
    return workflowLockFunctions.getStatistics();
  }

  async pausePropertyOperations(propertyId: number, reason: string, lockedBy: number): Promise<{ success: boolean; lock?: WorkflowLock; message?: string; error?: string }> {
    const response = await fetch(`${API_BASE_URL}/workflow-locks/properties/${propertyId}/pause`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ reason, locked_by: lockedBy }),
    });

    if (!response.ok) {
      const error = await response.json();
      return { success: false, error: error.detail || 'Failed to pause property operations' };
    }

    const result = await response.json();
    return result;
  }

  async resumePropertyOperations(propertyId: number, unlockedBy: number, resolutionNotes: string): Promise<{ success: boolean; message?: string; error?: string }> {
    const response = await fetch(`${API_BASE_URL}/workflow-locks/properties/${propertyId}/resume`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ unlocked_by: unlockedBy, resolution_notes: resolutionNotes }),
    });

    if (!response.ok) {
      const error = await response.json();
      return { success: false, error: error.detail || 'Failed to resume property operations' };
    }

    const result = await response.json();
    return result;
  }
}

// Export service instance
export const workflowLockService = new WorkflowLockService();
