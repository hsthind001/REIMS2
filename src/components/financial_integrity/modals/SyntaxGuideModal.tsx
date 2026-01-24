import React from 'react';
import { X, Calculator, AlertCircle, CheckCircle, Copy } from 'lucide-react';
import { Button } from '../../design-system';

interface SyntaxGuideModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function SyntaxGuideModal({ isOpen, onClose }: SyntaxGuideModalProps) {
  if (!isOpen) return null;

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  const examples = [
    {
      title: "Basic Arithmetic",
      formula: "Total Assets - Total Liabilities",
      description: "Simple subtraction of two account values"
    },
    {
      title: "Accounting Equation",
      formula: "Total Assets - (Total Liabilities + Total Equity)",
      description: "Using parentheses for grouping"
    },
    {
      title: "Percentage Calculation",
      formula: "(Net Income / Total Revenue) * 100",
      description: "Calculate profit margin as percentage"
    },
    {
      title: "Ratio Calculation",
      formula: "Current Assets / Current Liabilities",
      description: "Current ratio for liquidity analysis"
    },
    {
      title: "Multi-Line Items",
      formula: "Cash + Accounts Receivable + Inventory - Accounts Payable",
      description: "Working capital calculation"
    },
    {
      title: "Nested Operations",
      formula: "(Total Revenue - Total Expenses) / Total Revenue * 100",
      description: "Net margin percentage with nested operations"
    }
  ];

  const operators = [
    { symbol: "+", name: "Addition", example: "A + B" },
    { symbol: "-", name: "Subtraction", example: "A - B" },
    { symbol: "*", name: "Multiplication", example: "A * B" },
    { symbol: "/", name: "Division", example: "A / B" },
    { symbol: "()", name: "Parentheses", example: "(A + B) * C" },
  ];

  const bestPractices = [
    "Use exact account names as they appear in your financial statements",
    "Use parentheses to ensure correct order of operations",
    "Account names are case-sensitive",
    "Spaces in account names should be preserved exactly",
    "Use descriptive names that match your chart of accounts",
    "Test formulas with known values before deploying"
  ];

  const commonErrors = [
    {
      error: "Division by zero",
      solution: "Ensure denominators are never zero or use conditional logic"
    },
    {
      error: "Account name not found",
      solution: "Verify account names match exactly with financial statements"
    },
    {
      error: "Missing parentheses",
      solution: "Add parentheses to clarify order of operations"
    },
    {
      error: "Syntax errors",
      solution: "Check for matching parentheses and valid operators"
    }
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div 
        className="absolute inset-0 bg-gray-900/60 backdrop-blur-sm" 
        onClick={onClose}
      />
      
      <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200 bg-gradient-to-r from-blue-50 to-purple-50">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-600 rounded-lg">
                <Calculator className="w-5 h-5 text-white" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-gray-900">Formula Syntax Guide</h2>
                <p className="text-sm text-gray-600">Learn how to write powerful validation rules</p>
              </div>
            </div>
            <button 
              onClick={onClose}
              className="p-2 text-gray-400 hover:text-gray-600 hover:bg-white rounded-lg transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-8">
          
          {/* Basic Syntax */}
          <section>
            <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
              <span className="w-8 h-8 bg-blue-100 text-blue-700 rounded-full flex items-center justify-center text-sm font-bold">1</span>
              Basic Syntax
            </h3>
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 space-y-3">
              <p className="text-sm text-gray-700">
                Formulas are mathematical expressions that reference account names from your financial statements.
                The system evaluates these formulas and compares the result with expected values.
              </p>
              <div className="bg-white border border-gray-200 rounded p-3">
                <code className="text-sm font-mono text-blue-600">
                  Account Name [Operator] Account Name
                </code>
              </div>
            </div>
          </section>

          {/* Operators */}
          <section>
            <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
              <span className="w-8 h-8 bg-blue-100 text-blue-700 rounded-full flex items-center justify-center text-sm font-bold">2</span>
              Available Operators
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {operators.map((op, idx) => (
                <div key={idx} className="bg-white border border-gray-200 rounded-lg p-4 hover:border-blue-300 transition-colors">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-2xl font-bold text-blue-600">{op.symbol}</span>
                    <span className="text-xs text-gray-500 font-mono bg-gray-100 px-2 py-1 rounded">{op.example}</span>
                  </div>
                  <p className="text-sm text-gray-700">{op.name}</p>
                </div>
              ))}
            </div>
          </section>

          {/* Examples */}
          <section>
            <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
              <span className="w-8 h-8 bg-blue-100 text-blue-700 rounded-full flex items-center justify-center text-sm font-bold">3</span>
              Formula Examples
            </h3>
            <div className="space-y-3">
              {examples.map((ex, idx) => (
                <div key={idx} className="bg-white border border-gray-200 rounded-lg p-4 hover:border-blue-300 transition-colors">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <h4 className="font-semibold text-gray-900">{ex.title}</h4>
                        <CheckCircle className="w-4 h-4 text-green-500" />
                      </div>
                      <p className="text-sm text-gray-600 mb-3">{ex.description}</p>
                      <div className="bg-gray-900 rounded-lg p-3 font-mono text-sm text-blue-300 flex items-center justify-between">
                        <code>{ex.formula}</code>
                        <button
                          onClick={() => copyToClipboard(ex.formula)}
                          className="p-1 hover:bg-gray-800 rounded transition-colors"
                          title="Copy formula"
                        >
                          <Copy className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* Best Practices */}
          <section>
            <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
              <span className="w-8 h-8 bg-green-100 text-green-700 rounded-full flex items-center justify-center text-sm font-bold">✓</span>
              Best Practices
            </h3>
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <ul className="space-y-2">
                {bestPractices.map((practice, idx) => (
                  <li key={idx} className="flex items-start gap-2 text-sm text-gray-700">
                    <CheckCircle className="w-4 h-4 text-green-600 mt-0.5 shrink-0" />
                    <span>{practice}</span>
                  </li>
                ))}
              </ul>
            </div>
          </section>

          {/* Common Errors */}
          <section>
            <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
              <span className="w-8 h-8 bg-amber-100 text-amber-700 rounded-full flex items-center justify-center text-sm font-bold">!</span>
              Common Errors & Solutions
            </h3>
            <div className="space-y-3">
              {commonErrors.map((item, idx) => (
                <div key={idx} className="bg-amber-50 border border-amber-200 rounded-lg p-4">
                  <div className="flex items-start gap-3">
                    <AlertCircle className="w-5 h-5 text-amber-600 mt-0.5 shrink-0" />
                    <div className="flex-1">
                      <h4 className="font-semibold text-amber-900 mb-1">{item.error}</h4>
                      <p className="text-sm text-amber-700">{item.solution}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* Account Reference Guide */}
          <section>
            <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
              <span className="w-8 h-8 bg-purple-100 text-purple-700 rounded-full flex items-center justify-center text-sm font-bold">4</span>
              Account Reference Guide
            </h3>
            <div className="bg-purple-50 border border-purple-200 rounded-lg p-4 space-y-3">
              <p className="text-sm text-gray-700">
                Account names must match exactly as they appear in your financial statements. Common account names include:
              </p>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                {[
                  "Total Assets",
                  "Total Liabilities",
                  "Total Equity",
                  "Total Revenue",
                  "Total Expenses",
                  "Net Income",
                  "Current Assets",
                  "Current Liabilities",
                  "Cash",
                  "Accounts Receivable",
                  "Accounts Payable",
                  "Operating Expenses"
                ].map((account, idx) => (
                  <div key={idx} className="bg-white border border-purple-200 rounded px-3 py-2 text-sm font-mono text-gray-700">
                    {account}
                  </div>
                ))}
              </div>
              <p className="text-xs text-gray-600 mt-2">
                <strong>Note:</strong> Your actual account names may differ. Refer to your Chart of Accounts for exact names.
              </p>
            </div>
          </section>

          {/* Order of Operations */}
          <section>
            <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
              <span className="w-8 h-8 bg-blue-100 text-blue-700 rounded-full flex items-center justify-center text-sm font-bold">5</span>
              Order of Operations
            </h3>
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <p className="text-sm text-gray-700 mb-3">
                Formulas follow standard mathematical order of operations (PEMDAS):
              </p>
              <ol className="space-y-2 text-sm text-gray-700">
                <li className="flex items-start gap-2">
                  <span className="font-bold text-blue-600 w-6">1.</span>
                  <span><strong>Parentheses</strong> - Operations inside parentheses are evaluated first</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="font-bold text-blue-600 w-6">2.</span>
                  <span><strong>Multiplication & Division</strong> - Left to right</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="font-bold text-blue-600 w-6">3.</span>
                  <span><strong>Addition & Subtraction</strong> - Left to right</span>
                </li>
              </ol>
              <div className="mt-4 p-3 bg-white border border-blue-200 rounded">
                <p className="text-xs text-gray-600 mb-2">Example:</p>
                <code className="text-sm font-mono text-blue-600">A + B * C</code>
                <p className="text-xs text-gray-600 mt-1">Evaluates as: A + (B * C)</p>
              </div>
            </div>
          </section>

        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-200 bg-gray-50">
          <div className="flex items-center justify-between">
            <p className="text-sm text-gray-600">
              Need help? Contact the finance team for assistance with formula syntax.
            </p>
            <Button onClick={onClose}>
              Got it
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
