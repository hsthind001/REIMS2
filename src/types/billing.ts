/**
 * Billing and Subscription TypeScript Interfaces
 */

export interface Subscription {
  id: number;
  organization_name: string;
  subscription_status: 'active' | 'trialing' | 'past_due' | 'canceled' | 'incomplete';
  status?: 'active' | 'trialing' | 'past_due' | 'canceled' | 'incomplete'; // Alias for compatibility
  stripe_customer_id?: string;
  plan_name: string;
  billing_cycle: 'monthly' | 'yearly';
  next_billing_date?: string;
  current_period_end?: string; // For tooltip display
  cancel_at_period_end?: boolean; // For cancellation warning
  amount?: number;
  currency: string;
}

export interface Invoice {
  id: string;
  invoice_number: string;
  amount: number;
  currency: string;
  status: 'draft' | 'open' | 'paid' | 'void' | 'uncollectible';
  created_at: string;
  due_date?: string;
  pdf_url?: string;
}

export interface Plan {
  id: string;
  name: string;
  description: string;
  price_monthly: number;
  price_yearly: number;
  currency: string;
  features: string[];
  is_popular: boolean;
}

export interface PortalSession {
  url: string;
}
