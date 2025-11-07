/**
 * Property Service
 * 
 * API calls for property management (CRUD operations)
 */

import { api } from './api';
import type { Property, PropertyCreate } from '../types/api';

export class PropertyService {
  /**
   * Get all properties
   */
  async getAllProperties(params?: {
    skip?: number;
    limit?: number;
    status?: string;
  }): Promise<Property[]> {
    return api.get<Property[]>('/properties', params);
  }

  /**
   * Get property by ID
   */
  async getProperty(propertyId: number): Promise<Property> {
    return api.get<Property>(`/properties/${propertyId}`);
  }

  /**
   * Create new property
   */
  async createProperty(propertyData: PropertyCreate): Promise<Property> {
    return api.post<Property>('/properties', propertyData);
  }

  /**
   * Update property
   */
  async updateProperty(
    propertyCode: string,
    propertyData: Partial<PropertyCreate>
  ): Promise<Property> {
    return api.put<Property>(`/properties/${propertyCode}`, propertyData);
  }

  /**
   * Delete property
   */
  async deleteProperty(propertyCode: string): Promise<void> {
    await api.delete<void>(`/properties/${propertyCode}`);
  }

  /**
   * Get property summary with financial periods
   */
  async getPropertySummary(propertyId: number): Promise<any> {
    return api.get<any>(`/properties/${propertyId}/summary`);
  }
}

// Export singleton
export const propertyService = new PropertyService();

