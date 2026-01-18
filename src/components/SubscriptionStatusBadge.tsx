import { useQuery } from '@tanstack/react-query';
import { billingService } from '../services/billingService';
import type { Subscription } from '../types/billing';
import { useState } from 'react';

export function SubscriptionStatusBadge() {
  const [showDetails, setShowDetails] = useState(false);

  const { data: subscription, isLoading, error } = useQuery<Subscription>({
    queryKey: ['subscription-status'],
    queryFn: billingService.getSubscription,
    refetchInterval: 5 * 60 * 1000, // Refetch every 5 minutes
    retry: 1,
  });

  if (isLoading) {
    return (
      <div className="subscription-badge loading">
        <span className="badge-dot">●</span>
        <span className="badge-text">...</span>
      </div>
    );
  }

  if (error || !subscription) {
    // Don't show badge if there's an error or no subscription
    return null;
  }

  const getStatusConfig = (status: string) => {
    switch (status) {
      case 'active':
        return { color: 'success', label: 'Active', dot: '●' };
      case 'trialing':
        return { color: 'info', label: 'Trial', dot: '●' };
      case 'past_due':
        return { color: 'warning', label: 'Past Due', dot: '●' };
      case 'canceled':
        return { color: 'error', label: 'Canceled', dot: '●' };
      case 'unpaid':
        return { color: 'error', label: 'Unpaid', dot: '●' };
      default:
        return { color: 'default', label: 'Unknown', dot: '●' };
    }
  };

  const statusConfig = getStatusConfig(subscription.subscription_status);

  return (
    <div 
      className="subscription-badge"
      onMouseEnter={() => setShowDetails(true)}
      onMouseLeave={() => setShowDetails(false)}
      style={{ position: 'relative', cursor: 'pointer' }}
    >
      <div className={`badge-content badge-${statusConfig.color}`}>
        <span className="badge-dot">{statusConfig.dot}</span>
        <span className="badge-text">{statusConfig.label}</span>
      </div>

      {showDetails && (
        <div className="subscription-tooltip">
          <div className="tooltip-header">
            <strong>{subscription.plan_name}</strong>
          </div>
          <div className="tooltip-body">
            <div className="tooltip-row">
              <span>Status:</span>
              <span className={`status-${statusConfig.color}`}>{statusConfig.label}</span>
            </div>
            {subscription.current_period_end && (
              <div className="tooltip-row">
                <span>{subscription.cancel_at_period_end ? 'Expires:' : 'Renews:'}</span>
                <span>{new Date(subscription.current_period_end).toLocaleDateString()}</span>
              </div>
            )}
            {subscription.cancel_at_period_end && (
              <div className="tooltip-warning">
                ⚠️ Subscription will cancel on renewal date
              </div>
            )}
          </div>
          <div className="tooltip-footer">
            <a href="#" onClick={(e) => {
              e.preventDefault();
              window.location.hash = 'admin';
              // Navigate to billing tab after a short delay
              setTimeout(() => {
                const billingTab = document.querySelector('[data-tab="billing"]') as HTMLElement;
                billingTab?.click();
              }, 100);
            }}>
              Manage Billing →
            </a>
          </div>
        </div>
      )}

      <style>{`
        .subscription-badge {
          display: inline-flex;
          align-items: center;
          margin-right: 1rem;
        }

        .badge-content {
          display: flex;
          align-items: center;
          gap: 0.375rem;
          padding: 0.25rem 0.75rem;
          border-radius: 9999px;
          font-size: 0.875rem;
          font-weight: 500;
          transition: all 0.2s;
        }

        .badge-success {
          background-color: rgba(34, 197, 94, 0.1);
          color: rgb(22, 163, 74);
          border: 1px solid rgba(34, 197, 94, 0.2);
        }

        .badge-info {
          background-color: rgba(59, 130, 246, 0.1);
          color: rgb(37, 99, 235);
          border: 1px solid rgba(59, 130, 246, 0.2);
        }

        .badge-warning {
          background-color: rgba(251, 191, 36, 0.1);
          color: rgb(217, 119, 6);
          border: 1px solid rgba(251, 191, 36, 0.2);
        }

        .badge-error {
          background-color: rgba(239, 68, 68, 0.1);
          color: rgb(220, 38, 38);
          border: 1px solid rgba(239, 68, 68, 0.2);
        }

        .badge-default {
          background-color: rgba(148, 163, 184, 0.1);
          color: rgb(100, 116, 139);
          border: 1px solid rgba(148, 163, 184, 0.2);
        }

        .badge-dot {
          font-size: 1.25rem;
          line-height: 1;
        }

        .badge-text {
          font-size: 0.875rem;
        }

        .subscription-badge.loading .badge-content {
          background-color: rgba(148, 163, 184, 0.1);
          color: rgb(148, 163, 184);
          border: 1px solid rgba(148, 163, 184, 0.2);
        }

        .subscription-tooltip {
          position: absolute;
          top: calc(100% + 0.5rem);
          right: 0;
          min-width: 280px;
          background: white;
          border: 1px solid rgba(226, 232, 240, 1);
          border-radius: 0.5rem;
          box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
          z-index: 1000;
          overflow: hidden;
        }

        [data-theme="dark"] .subscription-tooltip {
          background: rgb(30, 41, 59);
          border-color: rgba(71, 85, 105, 1);
        }

        .tooltip-header {
          padding: 0.75rem 1rem;
          background-color: rgba(241, 245, 249, 1);
          border-bottom: 1px solid rgba(226, 232, 240, 1);
          font-size: 0.875rem;
        }

        [data-theme="dark"] .tooltip-header {
          background-color: rgba(51, 65, 85, 1);
          border-bottom-color: rgba(71, 85, 105, 1);
        }

        .tooltip-body {
          padding: 0.75rem 1rem;
        }

        .tooltip-row {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 0.5rem;
          font-size: 0.875rem;
        }

        .tooltip-row:last-child {
          margin-bottom: 0;
        }

        .tooltip-row span:first-child {
          color: rgb(100, 116, 139);
        }

        [data-theme="dark"] .tooltip-row span:first-child {
          color: rgb(148, 163, 184);
        }

        .tooltip-row .status-success { color: rgb(22, 163, 74); }
        .tooltip-row .status-info { color: rgb(37, 99, 235); }
        .tooltip-row .status-warning { color: rgb(217, 119, 6); }
        .tooltip-row .status-error { color: rgb(220, 38, 38); }

        .tooltip-warning {
          margin-top: 0.75rem;
          padding: 0.5rem;
          background-color: rgba(251, 191, 36, 0.1);
          border-left: 3px solid rgb(251, 191, 36);
          border-radius: 0.25rem;
          font-size: 0.75rem;
          color: rgb(217, 119, 6);
        }

        .tooltip-footer {
          padding: 0.75rem 1rem;
          background-color: rgba(241, 245, 249, 1);
          border-top: 1px solid rgba(226, 232, 240, 1);
        }

        [data-theme="dark"] .tooltip-footer {
          background-color: rgba(51, 65, 85, 1);
          border-top-color: rgba(71, 85, 105, 1);
        }

        .tooltip-footer a {
          color: rgb(59, 130, 246);
          text-decoration: none;
          font-size: 0.875rem;
          font-weight: 500;
          transition: color 0.2s;
        }

        .tooltip-footer a:hover {
          color: rgb(37, 99, 235);
        }
      `}</style>
    </div>
  );
}
