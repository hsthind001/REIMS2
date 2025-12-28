/**
 * Property Service
 * 
 * API calls for property management (CRUD operations)
 */

import { api } from './api';
import type { Property, PropertyCreate } from '../types/api';

export class PropertyService {
  private withDisplayName(property: Property): Property {
    return {
      ...property,
      name: property.property_name || property.property_code || `Property ${property.id}`,
    };
  }

  /**
   * Get all properties
   */
  async getAllProperties(params?: {
    skip?: number;
    limit?: number;
    status?: string;
  }): Promise<Property[]> {
    const properties = await api.get<Property[]>('/properties', params);
    return properties.map((property) => this.withDisplayName(property));
  }

  /**
   * Get property by ID
   */
  async getProperty(propertyId: number): Promise<Property> {
    const property = await api.get<Property>(`/properties/${propertyId}`);
    return this.withDisplayName(property);
  }

  /**
   * Create new property
   */
  async createProperty(propertyData: PropertyCreate): Promise<Property> {
    const property = await api.post<Property>('/properties', propertyData);
    return this.withDisplayName(property);
  }

  /**
   * Update property
   */
  async updateProperty(
    propertyId: number,
    propertyData: Partial<PropertyCreate>
  ): Promise<Property> {
    const property = await api.put<Property>(`/properties/${propertyId}`, propertyData);
    return this.withDisplayName(property);
  }

  /**
   * Delete property
   */
  async deleteProperty(propertyId: number): Promise<void> {
    await api.delete<void>(`/properties/${propertyId}`);
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
