
import React, { useState } from 'react';

import { useForm } from 'react-hook-form';
import { 
  X, 
  Save, 
  Calculator, 
  AlertTriangle,
  Info
} from 'lucide-react';
import { Button } from '../../design-system';
import SyntaxGuideModal from './SyntaxGuideModal';

interface EditRuleModalProps {
  isOpen: boolean;
  onClose: () => void;
  rule: {
    id: string;
    name: string;
    description: string;
    formula: string;
    threshold: number;
    type: string;
  };
  onSave: (data: any) => Promise<void>;
}

interface RuleFormInputs {
    name: string;
    description: string;
    formula: string;
    threshold: number;
}

export default function EditRuleModal({ isOpen, onClose, rule, onSave }: EditRuleModalProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showSyntaxGuide, setShowSyntaxGuide] = useState(false);
  const { register, handleSubmit, formState: { errors } } = useForm<RuleFormInputs>({
      defaultValues: {
          name: rule.name,
          description: rule.description,
          formula: rule.formula,
          threshold: rule.threshold
      }
  });

  if (!isOpen) return null;

  const onSubmit = async (data: RuleFormInputs) => {
      setIsSubmitting(true);
      try {
          await onSave(data);
          onClose();
      } catch (error) {
          console.error("Failed to save rule:", error);
      } finally {
          setIsSubmitting(false);
      }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6">
      <div 
        className="absolute inset-0 bg-gray-900/60 backdrop-blur-sm transition-opacity" 
        onClick={onClose}
      />
      
      <div className="relative bg-white rounded-2xl shadow-xl w-full max-w-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between bg-gray-50/50">
          <div>
            <div className="flex items-center gap-2 mb-1">
               <span className="text-xs font-mono font-medium text-gray-500 bg-white border border-gray-200 px-1.5 py-0.5 rounded">
                 {rule.id}
               </span>
               <span className="text-xs font-bold text-blue-700 bg-blue-50 border border-blue-100 px-2 py-0.5 rounded-full uppercase tracking-wide">
                 Editing Logic
               </span>
            </div>
            <h3 className="text-lg font-bold text-gray-900">Configure Rule</h3>
          </div>
          <button 
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-full transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
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
                    <button 
                      type="button"
                      onClick={() => setShowSyntaxGuide(true)}
                      className="flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800 hover:underline transition-colors"
                    >
                        <Info className="w-3 h-3" /> Syntax Guide
                    </button>
                </div>
                
                <div className="relative">
                    <textarea 
                        {...register("formula", { required: "Formula is required" })}
                        rows={3}
                        className="w-full px-4 py-3 bg-gray-900 text-blue-300 font-mono text-sm rounded-xl border border-gray-800 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        spellCheck={false}
                    />
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
           <Button variant="outline" onClick={onClose}>
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

      {/* Syntax Guide Modal */}
      <SyntaxGuideModal 
        isOpen={showSyntaxGuide}
        onClose={() => setShowSyntaxGuide(false)}
      />
    </div>
  );
}
