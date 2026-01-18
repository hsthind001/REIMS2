import { useState, useEffect } from 'react';
import { Check, Star } from 'lucide-react';
import { Card, Button } from '../design-system';
import type { Plan } from '../../types/billing';
import { billingService } from '../../services/billingService';

export function PlanManagement() {
  const [plans, setPlans] = useState<Plan[]>([]);
  const [loading, setLoading] = useState(true);
  const [billingCycle, setBillingCycle] = useState<'monthly' | 'yearly'>('monthly');

  useEffect(() => {
    loadPlans();
  }, []);

  const loadPlans = async () => {
    try {
      setLoading(true);
      const data = await billingService.getPlans();
      setPlans(data);
    } catch (err) {
      console.error('Failed to load plans:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleUpgrade = (planId: string) => {
    // In a real implementation, this would redirect to Stripe checkout
    alert(`Upgrade to plan: ${planId}`);
  };

  if (loading) {
    return (
      <Card className="p-6">
        <div className="text-center text-text-secondary">Loading plans...</div>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Billing Cycle Toggle */}
      <div className="flex justify-center">
        <div className="inline-flex items-center gap-2 p-1 bg-background rounded-lg border border-border">
          <button
            onClick={() => setBillingCycle('monthly')}
            className={`px-4 py-2 rounded-md font-medium transition-colors ${
              billingCycle === 'monthly'
                ? 'bg-info text-white'
                : 'text-text-secondary hover:text-text-primary'
            }`}
          >
            Monthly
          </button>
          <button
            onClick={() => setBillingCycle('yearly')}
            className={`px-4 py-2 rounded-md font-medium transition-colors ${
              billingCycle === 'yearly'
                ? 'bg-info text-white'
                : 'text-text-secondary hover:text-text-primary'
            }`}
          >
            Yearly 
            <span className="text-xs ml-1">(Save 17%)</span>
          </button>
        </div>
      </div>

      {/* Plans Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {plans.map((plan) => {
          const price = billingCycle === 'yearly' ? plan.price_yearly : plan.price_monthly;
          const monthlyEquivalent = billingCycle === 'yearly' ? plan.price_yearly / 12 : price;

          return (
            <Card
              key={plan.id}
              className={`p-6 relative ${
                plan.is_popular ? 'ring-2 ring-info shadow-lg' : ''
              }`}
              hover
            >
              {plan.is_popular && (
                <div className="absolute -top-3 left-1/2 transform -translate-x-1/2">
                  <span className="inline-flex items-center gap-1 px-3 py-1 bg-info text-white rounded-full text-sm font-medium">
                    <Star className="w-3 h-3 fill-current" />
                    Most Popular
                  </span>
                </div>
              )}

              <div className="text-center mb-6">
                <h3 className="text-xl font-bold text-text-primary mb-2">{plan.name}</h3>
                <p className="text-sm text-text-secondary mb-4">{plan.description}</p>
                
                <div className="mb-2">
                  <span className="text-4xl font-bold text-text-primary">
                    ${monthlyEquivalent.toFixed(0)}
                  </span>
                  <span className="text-text-secondary">/mo</span>
                </div>

                {billingCycle === 'yearly' && (
                  <p className="text-xs text-text-secondary">
                    ${price.toFixed(0)} billed annually
                  </p>
                )}
              </div>

              <ul className="space-y-3 mb-6">
                {plan.features.map((feature, index) => (
                  <li key={index} className="flex items-start gap-2 text-sm">
                    <Check className="w-5 h-5 text-success flex-shrink-0 mt-0.5" />
                    <span className="text-text-secondary">{feature}</span>
                  </li>
                ))}
              </ul>

              <Button
                variant={plan.is_popular ? 'primary' : 'default'}
                className="w-full"
                onClick={() => handleUpgrade(plan.id)}
              >
                Select Plan
              </Button>
            </Card>
          );
        })}
      </div>

      <Card variant="info" className="p-4">
        <p className="text-sm text-text-secondary">
          All plans include a 14-day free trial. No credit card required to start.
          You can upgrade, downgrade, or cancel at any time.
        </p>
      </Card>
    </div>
  );
}
