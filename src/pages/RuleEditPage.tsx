import React, { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { useQueryClient } from '@tanstack/react-query';
import { 
  Save, 
  Calculator, 
  AlertTriangle,
  Info,
  ArrowLeft,
  Loader2
} from 'lucide-react';
import { Button } from '../components/design-system';
import { forensicReconciliationService } from '../lib/forensic_reconciliation';
import SyntaxGuideModal from '../components/financial_integrity/modals/SyntaxGuideModal';

interface RuleFormInputs {
    name: string;
    description: string;
    formula: string;
    threshold: number;
}

export default function RuleEditPage() {
  const queryClient = useQueryClient();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [ruleData, setRuleData] = useState<any>(null);
  const [showSyntaxGuide, setShowSyntaxGuide] = useState(false);

  // Get rule data from localStorage (set by RuleConfigurationPage) OR fetch from API
  useEffect(() => {
    const stored = localStorage.getItem('editingRule');
    if (stored) {
      try {
        const data = JSON.parse(stored);
        setRuleData(data);
        return;
      } catch (err) {
        console.error('Failed to parse rule data:', err);
      }
    }

    // Fallback: Fetch from API using ID from URL
    const hash = window.location.hash;
    // URL format: #/rule-edit/BS-1
    const parts = hash.split('/');
    const ruleId = parts[parts.length - 1];

    if (ruleId && !ruleId.includes('?')) {
        const fetchRule = async () => {
            try {
                // We need to fetch all rules to find the one we want
                // In a real app, we'd have a specific endpoint for this
                const rules = await forensicReconciliationService.getCalculatedRules();
                const rule = rules.find((r: any) => r.rule_id === ruleId);
                
                if (rule) {
                    setRuleData({
                        id: rule.rule_id,
                        name: rule.rule_name,
                        description: rule.description,
                        formula: rule.formula,
                        threshold: rule.tolerance_absolute || 0.01
                    });
                }
            } catch (err) {
                console.error("Failed to fetch rule:", err);
            }
        };
        fetchRule();
    }
  }, []);

  const { register, handleSubmit, reset, formState: { errors } } = useForm<RuleFormInputs>({
      defaultValues: ruleData ? {
          name: ruleData.name,
          description: ruleData.description,
          formula: ruleData.formula,
          threshold: ruleData.threshold
      } : undefined
  });

  // Update form when data load completes
  useEffect(() => {
      if (ruleData) {
          reset({
              name: ruleData.name,
              description: ruleData.description,
              formula: ruleData.formula,
              threshold: ruleData.threshold
          });
      }
  }, [ruleData, reset]);

  const handleBack = () => {
    // Navigate back to rule configuration page
    if (ruleData?.id) {
      // Use the ID we have, whether from local storage or API
      window.location.hash = `rule-configuration/${ruleData.id}`;
    } else {
      window.location.hash = 'forensic-reconciliation';
    }
  };

  const onSubmit = async (data: RuleFormInputs) => {
      if (!ruleData?.id) return;
      
      setIsSubmitting(true);
      try {
          // Update rule (creates new version in backend)
          await forensicReconciliationService.updateCalculatedRule(ruleData.id, data);
          
          // Refresh query to show updated rule
          queryClient.invalidateQueries({ queryKey: ['rule-evaluation'] });
          
          // Navigate back to rule configuration page
          window.location.hash = `rule-configuration/${ruleData.id}`;
      } catch (error) {
          console.error("Failed to save rule:", error);
          alert('Failed to save rule. Please try again.');
      } finally {
          setIsSubmitting(false);
      }
  };

  if (!ruleData) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
            <Loader2 className="w-8 h-8 animate-spin text-blue-600 mx-auto mb-2" />
            <p className="text-gray-500">Loading rule details...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Navigation Header */}
        <div className="flex items-center gap-4">
          <Button 
            variant="outline" 
            onClick={handleBack}
            icon={<ArrowLeft className="w-4 h-4" />}
          >
            Back to Rule
          </Button>
          <div className="h-6 w-px bg-gray-300" />
          <h1 className="text-xl font-bold text-gray-900">Edit Rule Logic</h1>
        </div>

        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden">
          {/* Header */}
          <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between bg-gray-50/50">
            <div>
              <div className="flex items-center gap-2 mb-1">
                 <span className="text-xs font-mono font-medium text-gray-500 bg-white border border-gray-200 px-1.5 py-0.5 rounded">
                   {ruleData.id}
                 </span>
                 <span className="text-xs font-bold text-blue-700 bg-blue-50 border border-blue-100 px-2 py-0.5 rounded-full uppercase tracking-wide">
                   Editing Logic
                 </span>
              </div>
              <h3 className="text-lg font-bold text-gray-900">Configure Rule</h3>
            </div>
          </div>

          {/* Content */}
          <form onSubmit={handleSubmit(onSubmit)} className="flex-1 overflow-y-auto p-6 space-y-6">
              
              {/* Warning Banner */}
              <div className="bg-amber-50 border border-amber-100 rounded-lg p-4 flex gap-3">
                  <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
                  <div>
                      <h4 className="text-sm font-bold text-amber-900">Advanced Configuration</h4>
                      <p className="text-xs text-amber-700 mt-1">
                          Modifying the formula will affect how this rule is evaluated for all future periods. 
                          Historical data will not be changed.
                      </p>
                  </div>
              </div>

              {/* Basic Info */}
              <div className="space-y-4">
                  <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Rule Name</label>
                      <input 
                          {...register("name", { required: "Rule name is required" })}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      />
                      {errors.name && <span className="text-xs text-red-500">{errors.name.message}</span>}
                  </div>

                  <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                      <textarea 
                          {...register("description")}
                          rows={3}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none"
                      />
                  </div>
              </div>

              <div className="h-px bg-gray-100" />

              {/* Formula Logic */}
              <div className="space-y-4">
                  <div className="flex items-center justify-between">
                      <label className="flex items-center gap-2 text-sm font-medium text-gray-900">
                          <Calculator className="w-4 h-4 text-gray-400" />
                          Execution Formula
                      </label>
                      <a 
                        href="#syntax-guide" 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className="flex items-center gap-1 text-xs text-blue-600 hover:underline"
                      >
                          <Info className="w-3 h-3" /> Syntax Guide
                      </a>
                  </div>
                  
                  <div className="relative">
                      <textarea 
                          {...register("formula", { required: "Formula is required" })}
                          rows={3}
                          className="w-full px-4 py-3 bg-gray-900 text-blue-300 font-mono text-sm rounded-xl border border-gray-800 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                          spellCheck={false}
                      />
                      {errors.formula && <span className="text-xs text-red-500">{errors.formula.message}</span>}
                  </div>
                  
                  <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Variance Threshold (Absolute)</label>
                      <div className="flex items-center gap-2">
                          <span className="text-sm text-gray-400">$</span>
                          <input 
                              type="number"
                              step="0.01"
                              {...register("threshold", { valueAsNumber: true })}
                              className="w-32 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                          />
                      </div>
                      <p className="text-xs text-gray-500 mt-1">Variances below this amount will be considered passing.</p>
                  </div>
              </div>
          </form>

          {/* Footer */}
          <div className="p-4 border-t border-gray-100 bg-gray-50 flex items-center justify-end gap-3">
             <Button variant="outline" onClick={handleBack}>
                 Cancel
             </Button>
             <Button 
              onClick={handleSubmit(onSubmit)}
              isLoading={isSubmitting}
              icon={<Save className="w-4 h-4" />}
             >
                 Save Changes
             </Button>
          </div>
        </div>
      </div>

      {/* Syntax Guide Modal */}
      <SyntaxGuideModal 
        isOpen={showSyntaxGuide}
        onClose={() => setShowSyntaxGuide(false)}
      />
    </div>
  );
}
