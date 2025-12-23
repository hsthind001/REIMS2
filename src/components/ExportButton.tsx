/**
 * ExportButton Component
 * 
 * Reusable component for exporting data to Excel or CSV formats.
 * Provides loading states and user feedback.
 */
import { useState } from 'react';
import { Download, FileSpreadsheet, FileText, Loader2 } from 'lucide-react';
import { exportToExcel, exportToCSV } from '../lib/exportUtils';
import { Button } from './design-system';

interface ExportButtonProps {
  /** Data to export */
  data?: any[];
  /** Base filename (without extension) */
  filename?: string;
  /** Export format: 'excel', 'csv', or 'both' */
  format?: 'excel' | 'csv' | 'both';
  /** Optional sheet name for Excel exports */
  sheetName?: string;
  /** Button variant */
  variant?: 'primary' | 'secondary' | 'outline';
  /** Button size */
  size?: 'sm' | 'md' | 'lg';
  /** Custom label */
  label?: string;
  /** Disabled state */
  disabled?: boolean;
  /** Show icon */
  showIcon?: boolean;
  /** Custom className */
  className?: string;
  /** Optional callback function for custom export logic */
  onExport?: (format: 'excel' | 'csv') => void | Promise<void>;
}

export function ExportButton({
  data,
  filename = 'export',
  format = 'both',
  sheetName = 'Sheet1',
  variant = 'secondary',
  size = 'md',
  label,
  disabled = false,
  showIcon = true,
  className = '',
  onExport
}: ExportButtonProps) {
  const [exporting, setExporting] = useState(false);
  const [lastExport, setLastExport] = useState<'excel' | 'csv' | null>(null);

  const handleExport = async (exportFormat: 'excel' | 'csv') => {
    // If onExport callback is provided, use it
    if (onExport) {
      setExporting(true);
      setLastExport(exportFormat);
      try {
        await onExport(exportFormat);
        setTimeout(() => {
          setExporting(false);
          setLastExport(null);
        }, 500);
      } catch (error: any) {
        console.error('Export failed:', error);
        alert(`Export failed: ${error.message || 'Unknown error'}`);
        setExporting(false);
        setLastExport(null);
      }
      return;
    }

    // Otherwise, use data-based export
    if (!data || !Array.isArray(data) || data.length === 0) {
      alert('No data to export');
      return;
    }

    setExporting(true);
    setLastExport(exportFormat);

    try {
      if (exportFormat === 'excel') {
        exportToExcel(data, filename, sheetName);
      } else {
        exportToCSV(data, filename);
      }
      
      // Show success feedback
      setTimeout(() => {
        setExporting(false);
        setLastExport(null);
      }, 500);
    } catch (error: any) {
      console.error('Export failed:', error);
      alert(`Export failed: ${error.message || 'Unknown error'}`);
      setExporting(false);
      setLastExport(null);
    }
  };

  if (format === 'both') {
    return (
      <div className={`flex gap-2 ${className}`}>
        <Button
          variant={variant}
          size={size}
          onClick={() => handleExport('excel')}
          disabled={disabled || exporting || (data && (!Array.isArray(data) || data.length === 0))}
          className="flex items-center gap-2"
        >
          {exporting && lastExport === 'excel' ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : showIcon ? (
            <FileSpreadsheet className="w-4 h-4" />
          ) : null}
          {label || 'Export Excel'}
        </Button>
        <Button
          variant={variant}
          size={size}
          onClick={() => handleExport('csv')}
          disabled={disabled || exporting || (data && (!Array.isArray(data) || data.length === 0))}
          className="flex items-center gap-2"
        >
          {exporting && lastExport === 'csv' ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : showIcon ? (
            <FileText className="w-4 h-4" />
          ) : null}
          {label || 'Export CSV'}
        </Button>
      </div>
    );
  }

  return (
    <Button
      variant={variant}
      size={size}
      onClick={() => handleExport(format)}
      disabled={disabled || exporting || (data && (!Array.isArray(data) || data.length === 0))}
      className={`flex items-center gap-2 ${className}`}
    >
      {exporting ? (
        <Loader2 className="w-4 h-4 animate-spin" />
      ) : showIcon ? (
        format === 'excel' ? (
          <FileSpreadsheet className="w-4 h-4" />
        ) : (
          <FileText className="w-4 h-4" />
        )
      ) : null}
      {label || (format === 'excel' ? 'Export Excel' : 'Export CSV')}
    </Button>
  );
}

/**
 * ExportDropdown Component
 * 
 * Dropdown menu for export options
 */
import { ChevronDown } from 'lucide-react';

interface ExportDropdownProps {
  data: any[];
  filename: string;
  sheetName?: string;
  variant?: 'primary' | 'secondary' | 'outline';
  size?: 'sm' | 'md' | 'lg';
  disabled?: boolean;
}

export function ExportDropdown({
  data,
  filename,
  sheetName = 'Sheet1',
  variant = 'secondary',
  size = 'md',
  disabled = false
}: ExportDropdownProps) {
  const [exporting, setExporting] = useState(false);
  const [showMenu, setShowMenu] = useState(false);

  const handleExport = async (format: 'excel' | 'csv') => {
    if (!data || !Array.isArray(data) || data.length === 0) {
      alert('No data to export');
      return;
    }

    setExporting(true);
    setShowMenu(false);

    try {
      if (format === 'excel') {
        exportToExcel(data, filename, sheetName);
      } else {
        exportToCSV(data, filename);
      }
      
      setTimeout(() => {
        setExporting(false);
      }, 500);
    } catch (error: any) {
      console.error('Export failed:', error);
      alert(`Export failed: ${error.message || 'Unknown error'}`);
      setExporting(false);
    }
  };

  return (
    <div className="relative inline-block">
      <Button
        variant={variant}
        size={size}
        onClick={() => setShowMenu(!showMenu)}
        disabled={disabled || exporting || (!data || !Array.isArray(data) || data.length === 0)}
        className="flex items-center gap-2"
      >
        {exporting ? (
          <Loader2 className="w-4 h-4 animate-spin" />
        ) : (
          <Download className="w-4 h-4" />
        )}
        Export
        <ChevronDown className="w-4 h-4" />
      </Button>
      
      {showMenu && (
        <>
          <div
            className="fixed inset-0 z-10"
            onClick={() => setShowMenu(false)}
          />
          <div className="absolute right-0 mt-2 w-48 bg-white rounded-md shadow-lg z-20 border border-gray-200">
            <div className="py-1">
              <button
                className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 flex items-center gap-2"
                onClick={() => handleExport('excel')}
                disabled={exporting}
              >
                <FileSpreadsheet className="w-4 h-4" />
                Export to Excel
              </button>
              <button
                className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 flex items-center gap-2"
                onClick={() => handleExport('csv')}
                disabled={exporting}
              >
                <FileText className="w-4 h-4" />
                Export to CSV
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

