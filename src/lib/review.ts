/**
 * Review Service
 * 
 * API calls for reviewing and correcting extracted data
 */

import { api } from './api';
import type { ReviewQueueItem } from '../types/api';

export class ReviewService {
  /**
   * Get review queue (items needing review)
   */
  async getReviewQueue(params?: {
    property_code?: string;
    document_type?: string;
    skip?: number;
    limit?: number;
  }): Promise<any> {
    return api.get<any>('/review/queue', params);
  }

  /**
   * Approve a financial data record
   */
  async approveRecord(recordId: number, tableName: string, notes?: string): Promise<void> {
    return api.put<void>(`/review/${recordId}/approve`, {
      table_name: tableName,
      notes
    });
  }

  /**
   * Correct a financial data record
   */
  async correctRecord(
    recordId: number,
    tableName: string,
    fieldName: string,
    newValue: any,
    notes?: string
  ): Promise<void> {
    return api.put<void>(`/review/${recordId}/correct`, {
      table_name: tableName,
      field_name: fieldName,
      new_value: newValue,
      notes
    });
  }

  /**
   * Bulk approve records
   */
  async bulkApprove(records: Array<{ id: number; table_name: string }>): Promise<void> {
    return api.post<void>('/review/bulk-approve', { records });
  }
}

// Export singleton
export const reviewService = new ReviewService();

