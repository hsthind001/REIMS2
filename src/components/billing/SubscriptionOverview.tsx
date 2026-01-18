import { useState, useEffect } from 'react';
import { CreditCard, Calendar, DollarSign, AlertCircle, CheckCircle, ExternalLink } from 'lucide-react';
import { Card, Button } from '../design-system';
import type { Subscription } from '../../types/billing';
import { billingService } from '../../services/billingService';

export function SubscriptionOverview() {
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadSubscription();
  }, []);

  const loadSubscription = async () => {
    try {
      setLoading(true);
      const data = await billingService.getSubscription();
      setSubscription(data);
    } catch (err) {
      console.error('Failed to load subscription:', err);
      setError('Failed to load subscription data');
    } finally {
      setLoading(false);
    }
  };

  const handleManageBilling = async () => {
    try {
      const portal = await billingService.createPortalSession();
      window.open(portal.url, '_blank');
    } catch (err) {
      console.error('Failed to open billing portal:', err);
      alert('Failed to open billing portal. Please try again.');
    }
  };

  const getStatusBadge = (status: string) => {
    const configs = {
      active: { icon: CheckCircle, color: 'text-success bg-success-light', label: 'Active' },
      trialing: { icon: Calendar, color: 'text-info bg-info-light', label: 'Trial' },
      past_due: { icon: AlertCircle, color: 'text-warning bg-warning-light', label: 'Past Due' },
      canceled: { icon: AlertCircle, color: 'text-text-secondary bg-background', label: 'Canceled' },
      incomplete: { icon: AlertCircle, color: 'text-danger bg-danger-light', label: 'Incomplete' },
    };

    const config = configs[status as keyof typeof configs] || configs.active;
    const Icon = config.icon;

    return (
      <span className={`inline-flex items-center gap-1 px-3 py-1 rounded-full font-medium ${config.color}`}>
        <Icon className="w-4 h-4" />
        {config.label}
      </span>
    );
  };

  if (loading) {
    return (
      <Card className="p-6">
        <div className="text-center text-text-secondary">Loading subscription...</div>
      </Card>
    );
  }

  if (error || !subscription) {
    return (
      <Card className="p-6">
        <div className="text-center text-danger">{error || 'Failed to load subscription'}</div>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Status Banner */}
      <Card className="p-6">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-2">
              <h2 className="text-2xl font-bold text-text-primary">{subscription.plan_name} Plan</h2>
              {getStatusBadge(subscription.subscription_status)}
            </div>
            <p className="text-text-secondary">
              {subscription.organization_name}
            </p>
          </div>
          <Button 
            variant="primary" 
            icon={<ExternalLink className="w-4 h-4" />}
            onClick={handleManageBilling}
          >
            Manage Billing
          </Button>
        </div>
      </Card>

      {/* Subscription Details Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Billing Cycle */}
        <Card className="p-6">
          <div className="flex items-start gap-3">
            <div className="p-2 bg-info-light rounded-lg">
              <Calendar className="w-5 h-5 text-info" />
            </div>
            <div className="flex-1">
              <div className="text-sm text-text-secondary mb-1">Billing Cycle</div>
              <div className="text-xl font-semibold text-text-primary capitalize">
                {subscription.billing_cycle}
              </div>
            </div>
          </div>
        </Card>

        {/* Amount */}
        <Card className="p-6">
          <div className="flex items-start gap-3">
            <div className="p-2 bg-success-light rounded-lg">
              <DollarSign className="w-5 h-5 text-success" />
            </div>
            <div className="flex-1">
              <div className="text-sm text-text-secondary mb-1">Amount</div>
              <div className="text-xl font-semibold text-text-primary">
                ${subscription.amount?.toFixed(2) || '0.00'} 
                <span className="text-sm font-normal text-text-secondary">
                  /{subscription.billing_cycle === 'yearly' ? 'year' : 'month'}
                </span>
              </div>
            </div>
          </div>
        </Card>

        {/* Next Billing Date */}
        <Card className="p-6">
          <div className="flex items-start gap-3">
            <div className="p-2 bg-warning-light rounded-lg">
              <CreditCard className="w-5 h-5 text-warning" />
            </div>
            <div className="flex-1">
              <div className="text-sm text-text-secondary mb-1">Next Billing</div>
              <div className="text-xl font-semibold text-text-primary">
                {subscription.next_billing_date 
                  ? new Date(subscription.next_billing_date).toLocaleDateString()
                  : 'N/A'
                }
              </div>
            </div>
          </div>
        </Card>
      </div>

      {/* Status Warnings */}
      {subscription.subscription_status === 'past_due' && (
        <Card variant="warning" className="p-4">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-warning flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="font-semibold text-warning mb-1">Payment Past Due</h3>
              <p className="text-sm text-text-secondary">
                Your last payment failed. Please update your payment method to avoid service interruption.
              </p>
              <Button 
                variant="warning" 
                size="sm" 
                className="mt-2"
                onClick={handleManageBilling}
              >
                Update Payment Method
              </Button>
            </div>
          </div>
        </Card>
      )}

      {subscription.subscription_status === 'trialing' && subscription.next_billing_date && (
        <Card variant="info" className="p-4">
          <div className="flex items-start gap-3">
            <CheckCircle className="w-5 h-5 text-info flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="font-semibold text-info mb-1">Trial Period Active</h3>
              <p className="text-sm text-text-secondary">
                Your trial ends on {new Date(subscription.next_billing_date).toLocaleDateString()}. 
                Add a payment method to continue using REIMS after your trial.
              </p>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}
