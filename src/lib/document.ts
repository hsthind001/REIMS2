/**
 * Document Service
 * 
 * API calls for document upload and management
 */

import { api } from './api';
import type {
  DocumentUpload,
  DocumentUploadRequest,
  DocumentUploadResponse,
  PaginatedResponse
} from '../types/api';

export class DocumentService {
  /**
   * Upload a financial document
   */
  async uploadDocument(data: DocumentUploadRequest): Promise<DocumentUploadResponse> {
    const formData = new FormData();
    formData.append('property_code', data.property_code);
    formData.append('period_year', data.period_year.toString());
    formData.append('period_month', data.period_month.toString());
    formData.append('document_type', data.document_type);
    formData.append('file', data.file);

    return api.uploadFile<DocumentUploadResponse>('/documents/upload', formData);
  }

  /**
   * Get list of document uploads with filters
   */
  async getDocuments(params?: {
    property_code?: string;
    document_type?: string;
    extraction_status?: string;
    period_year?: number;
    period_month?: number;
    skip?: number;
    limit?: number;
  }): Promise<PaginatedResponse<DocumentUpload>> {
    return api.get<PaginatedResponse<DocumentUpload>>('/documents/uploads', params);
  }

  /**
   * Get single document upload details
   */
  async getDocument(uploadId: number): Promise<DocumentUpload> {
    return api.get<DocumentUpload>(`/documents/uploads/${uploadId}`);
  }

  /**
   * Get extracted financial data for a document
   */
  async getExtractedData(uploadId: number): Promise<any> {
    return api.get<any>(`/documents/uploads/${uploadId}/data`);
  }

  /**
   * Get presigned download URL for document
   */
  async getDownloadUrl(uploadId: number, expiresIn?: number): Promise<{presigned_url: string}> {
    return api.get<{presigned_url: string}>(
      `/documents/uploads/${uploadId}/download`,
      expiresIn ? { expires_in: expiresIn } : undefined
    );
  }
}

// Export singleton
export const documentService = new DocumentService();

