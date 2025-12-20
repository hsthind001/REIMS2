/**
 * Hook for checking if operations are allowed on properties
 * 
 * This hook checks for workflow locks before allowing operations like:
 * - financial_update
 * - report_generation  
 * - data_entry
 * - transaction
 */

import { useState, useCallback } from 'react';
import { workflowLockService, OperationCheckResult } from '../lib/workflowLocks';

export const useOperationCheck = () => {
  const [checking, setChecking] = useState(false);
  const [lastCheck, setLastCheck] = useState<OperationCheckResult | null>(null);

  const checkOperation = useCallback(async (
    propertyId: number,
    operation: 'financial_update' | 'report_generation' | 'data_entry' | 'transaction'
  ): Promise<OperationCheckResult> => {
    setChecking(true);
    try {
      const result = await workflowLockService.checkOperation({
        property_id: propertyId,
        operation,
      });
      setLastCheck(result);
      return result;
    } catch (error: any) {
      console.error('Failed to check operation:', error);
      // Default to allowing on error (fail open)
      const errorResult: OperationCheckResult = {
        success: false,
        allowed: true,
        property_id: propertyId,
        operation,
        blocking_locks: [],
        reason: 'Check failed - assuming allowed',
        message: error.message || 'Unknown error',
      };
      setLastCheck(errorResult);
      return errorResult;
    } finally {
      setChecking(false);
    }
  }, []);

  const requireOperation = useCallback(async (
    propertyId: number,
    operation: 'financial_update' | 'report_generation' | 'data_entry' | 'transaction',
    onBlocked?: (result: OperationCheckResult) => void
  ): Promise<boolean> => {
    const result = await checkOperation(propertyId, operation);
    
    if (!result.allowed) {
      if (onBlocked) {
        onBlocked(result);
      } else {
        // Default behavior: show alert
        const lockMessages = result.blocking_locks.map(lock => 
          `- ${lock.title} (${lock.lock_reason})`
        ).join('\n');
        
        alert(
          `❌ Operation "${operation}" is blocked by workflow locks:\n\n${lockMessages}\n\n` +
          `Please resolve the locks or get committee approval before proceeding.\n\n` +
          `Go to Risk Management → Workflow Locks to manage locks.`
        );
      }
      return false;
    }
    
    return true;
  }, [checkOperation]);

  return {
    checkOperation,
    requireOperation,
    checking,
    lastCheck,
  };
};

