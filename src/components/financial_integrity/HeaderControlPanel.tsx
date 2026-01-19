import React from 'react';
import { 
  Building2, 
  Download, 
  Calendar as CalendarIcon,
  ChevronDown,
  RefreshCw
} from 'lucide-react';
import { Menu, Transition } from '@headlessui/react';
import type { Property } from '../../types/api';

interface HeaderControlPanelProps {
  properties: Property[];
  selectedPropertyId: number | null;
  selectedPeriodId: number | null;
  periods: any[];
  onPropertyChange: (id: number) => void;
  onPeriodChange: (id: number) => void;
  onValidate: () => void;
  isValidating: boolean;
  onExport?: (format: string) => void;
}

export default function HeaderControlPanel({
  properties,
  selectedPropertyId,
  selectedPeriodId,
  periods,
  onPropertyChange,
  onPeriodChange,
  onValidate,
  isValidating,
  onExport
}: HeaderControlPanelProps) {
  
  const selectedProperty = properties.find(p => p.id === selectedPropertyId);
  const selectedPeriod = periods.find(p => p.id === selectedPeriodId);

  return (
    <div className="bg-white/80 backdrop-blur-md border-b border-gray-200 sticky top-0 z-40 shadow-sm transition-all duration-200">
      <div className="max-w-[1920px] mx-auto px-6 py-4">
        {/* Breadcrumb & Title Row */}
        <div className="flex items-center text-sm text-gray-500 mb-2 font-medium">
            <span className="flex items-center hover:text-gray-900 transition-colors cursor-pointer">
              <Building2 className="w-4 h-4 mr-1.5" />
              Properties
            </span>
            <ChevronDown className="w-4 h-4 mx-2 text-gray-400 rotate-[-90deg]" />
            <span className="flex items-center hover:text-gray-900 transition-colors cursor-pointer truncate max-w-[200px]">
              {selectedProperty?.property_name || 'Select Property'}
            </span>
            <ChevronDown className="w-4 h-4 mx-2 text-gray-400 rotate-[-90deg]" />
            <span className="text-blue-600 font-semibold bg-blue-50 px-2 py-0.5 rounded-full">
              Financial Integrity
            </span>
        </div>

        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <h1 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-gray-900 to-gray-700 tracking-tight">
              Financial Integrity Hub
            </h1>
            <span className="px-2.5 py-0.5 rounded-full bg-green-100 text-green-700 text-xs font-bold uppercase tracking-wider border border-green-200 shadow-sm">
              Live
            </span>
          </div>

          <div className="flex items-center gap-3 bg-gray-50/50 p-1.5 rounded-xl border border-gray-100 shadow-sm">
            {/* Property Selector */}
            <div className="relative group">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <Building2 className="h-4 w-4 text-gray-400 group-hover:text-blue-500 transition-colors" />
              </div>
              <select
                value={selectedPropertyId || ''}
                onChange={(e) => onPropertyChange(Number(e.target.value))}
                className="pl-9 pr-8 py-2 bg-white border border-gray-200 text-gray-700 text-sm rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none shadow-sm hover:border-gray-300 transition-all cursor-pointer appearance-none min-w-[240px] font-medium"
              >
                <option value="">Select Property</option>
                {properties.map(prop => (
                  <option key={prop.id} value={prop.id}>{prop.property_name}</option>
                ))}
              </select>
              <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
                <ChevronDown className="h-3 w-3 text-gray-400" />
              </div>
            </div>

            <div className="h-6 w-px bg-gray-300 mx-1" />

            {/* Period Selector */}
            <div className="relative group">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <CalendarIcon className="h-4 w-4 text-gray-400 group-hover:text-blue-500 transition-colors" />
              </div>
              <select
                value={selectedPeriodId || ''}
                onChange={(e) => onPeriodChange(Number(e.target.value))}
                className="pl-9 pr-8 py-2 bg-white border border-gray-200 text-gray-700 text-sm rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none shadow-sm hover:border-gray-300 transition-all cursor-pointer appearance-none min-w-[180px] font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                disabled={!selectedPropertyId}
              >
                <option value="">Select Period</option>
                {periods.map(period => (
                 <option key={period.id} value={period.id}>
                    {new Date(period.period_year, period.period_month - 1).toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}
                 </option>
                ))}
              </select>
              <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
                <ChevronDown className="h-3 w-3 text-gray-400" />
              </div>
            </div>
            
            <div className="h-6 w-px bg-gray-300 mx-1" />

            {/* Actions */}
            <button
                onClick={onValidate}
                disabled={isValidating || !selectedPropertyId || !selectedPeriodId}
                className={`
                    flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all shadow-sm
                    ${isValidating 
                        ? 'bg-blue-50 text-blue-400 cursor-wait' 
                        : 'bg-white text-gray-700 hover:bg-gray-50 hover:text-blue-600 border border-gray-200 hover:border-blue-200'
                    }
                `}
            >
                <RefreshCw className={`w-4 h-4 ${isValidating ? 'animate-spin' : ''}`} />
                {isValidating ? 'Validating...' : 'Validate'}
            </button>

            <Menu as="div" className="relative">
                <Menu.Button className="flex items-center gap-2 px-4 py-2 bg-gray-900 hover:bg-black text-white rounded-lg text-sm font-medium transition-all shadow-md hover:shadow-lg active:scale-95">
                    <Download className="w-4 h-4" />
                    Export
                    <ChevronDown className="w-3 h-3 opacity-70" />
                </Menu.Button>
                <Transition
                    enter="transition duration-100 ease-out"
                    enterFrom="transform scale-95 opacity-0"
                    enterTo="transform scale-100 opacity-100"
                    leave="transition duration-75 ease-out"
                    leaveFrom="transform scale-100 opacity-100"
                    leaveTo="transform scale-95 opacity-0"
                >
                    <Menu.Items className="absolute right-0 mt-2 w-48 bg-white rounded-xl shadow-xl border border-gray-100 focus:outline-none py-1 z-50 origin-top-right ring-1 ring-black ring-opacity-5">
                        {['PDF Report', 'Excel Workbook', 'CSV Data'].map((item) => (
                            <Menu.Item key={item}>
                                {({ active }) => (
                                    <button
                                        onClick={() => onExport && onExport(item)}
                                        className={`${
                                            active ? 'bg-blue-50 text-blue-700' : 'text-gray-700'
                                        } group flex w-full items-center px-4 py-2.5 text-sm transition-colors`}
                                    >
                                        {item}
                                    </button>
                                )}
                            </Menu.Item>
                        ))}
                    </Menu.Items>
                </Transition>
            </Menu>
          </div>
        </div>
      </div>
    </div>
  );
}
