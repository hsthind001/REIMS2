/**
 * Billing Service - API calls for subscription management
 */

import { api } from '../lib/api';
import type { Subscription, Invoice, Plan, PortalSession } from '../types/billing';

export const billingService = {
  /**
   * Get current organization's subscription
   */
  async getSubscription(): Promise<Subscription> {
    return await api.get<Subscription>('/billing/subscription');
  },

  /**
   * Get billing invoices
   */
  async getInvoices(limit: number = 10, offset: number = 0): Promise<Invoice[]> {
    return await api.get<Invoice[]>('/billing/invoices', { limit, offset });
  },

  /**
   * Create Stripe customer portal session
   */
  async createPortalSession(returnUrl?: string): Promise<PortalSession> {
    return await api.post<PortalSession>('/billing/portal', {
      return_url: returnUrl || window.location.href
    });
  },

  /**
   * Get available subscription plans
   */
  async getPlans(): Promise<Plan[]> {
    return await api.get<Plan[]>('/billing/plans');
  }
};


