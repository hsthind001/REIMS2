import * as XLSX from 'xlsx';
import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';

// ==================== CSV Export ====================

export function exportToCSV(data: any[], filename: string) {
  if (data.length === 0) {
    alert('No data to export');
    return;
  }

  const headers = Object.keys(data[0]);
  const csvContent = [
    headers.join(','),
    ...data.map(row =>
      headers.map(header => {
        const value = row[header];
        // Handle commas and quotes in values
        if (typeof value === 'string' && (value.includes(',') || value.includes('"'))) {
          return `"${value.replace(/"/g, '""')}"`;
        }
        return value ?? '';
      }).join(',')
    )
  ].join('\n');

  downloadFile(csvContent, `${filename}.csv`, 'text/csv;charset=utf-8;');
}

// ==================== Excel Export ====================

export function exportToExcel(data: any[], filename: string, sheetName: string = 'Sheet1') {
  if (data.length === 0) {
    alert('No data to export');
    return;
  }

  const worksheet = XLSX.utils.json_to_sheet(data);
  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, worksheet, sheetName);

  // Auto-size columns
  const maxWidth = 50;
  const colWidths = Object.keys(data[0]).map(key => {
    const maxLength = Math.max(
      key.length,
      ...data.map(row => String(row[key] ?? '').length)
    );
    return { wch: Math.min(maxLength + 2, maxWidth) };
  });
  worksheet['!cols'] = colWidths;

  XLSX.writeFile(workbook, `${filename}.xlsx`);
}

export function exportMultiSheetExcel(
  sheets: { name: string; data: any[] }[],
  filename: string
) {
  const workbook = XLSX.utils.book_new();

  sheets.forEach(({ name, data }) => {
    if (data.length > 0) {
      const worksheet = XLSX.utils.json_to_sheet(data);

      // Auto-size columns
      const maxWidth = 50;
      const colWidths = Object.keys(data[0]).map(key => {
        const maxLength = Math.max(
          key.length,
          ...data.map(row => String(row[key] ?? '').length)
        );
        return { wch: Math.min(maxLength + 2, maxWidth) };
      });
      worksheet['!cols'] = colWidths;

      XLSX.utils.book_append_sheet(workbook, worksheet, name);
    }
  });

  if (workbook.SheetNames.length === 0) {
    alert('No data to export');
    return;
  }

  XLSX.writeFile(workbook, `${filename}.xlsx`);
}

// ==================== PDF Export ====================

export function exportTableToPDF(
  title: string,
  headers: string[],
  data: any[][],
  filename: string,
  options: {
    orientation?: 'portrait' | 'landscape';
    subtitle?: string;
    footer?: string;
  } = {}
) {
  const doc = new jsPDF({
    orientation: options.orientation || 'portrait',
    unit: 'mm',
    format: 'a4'
  });

  // Add title
  doc.setFontSize(18);
  doc.setFont('helvetica', 'bold');
  doc.text(title, 14, 20);

  // Add subtitle if provided
  if (options.subtitle) {
    doc.setFontSize(11);
    doc.setFont('helvetica', 'normal');
    doc.text(options.subtitle, 14, 28);
  }

  // Add table
  autoTable(doc, {
    head: [headers],
    body: data,
    startY: options.subtitle ? 35 : 28,
    styles: {
      fontSize: 9,
      cellPadding: 3,
    },
    headStyles: {
      fillColor: [99, 102, 241], // Indigo color
      textColor: 255,
      fontStyle: 'bold'
    },
    alternateRowStyles: {
      fillColor: [249, 250, 251] // Light gray
    },
    margin: { top: 35 }
  });

  // Add footer
  const pageCount = (doc as any).internal.getNumberOfPages();
  for (let i = 1; i <= pageCount; i++) {
    doc.setPage(i);
    doc.setFontSize(8);
    doc.setFont('helvetica', 'normal');

    const footerText = options.footer || `Generated on ${new Date().toLocaleDateString()}`;
    doc.text(footerText, 14, doc.internal.pageSize.height - 10);
    doc.text(
      `Page ${i} of ${pageCount}`,
      doc.internal.pageSize.width - 30,
      doc.internal.pageSize.height - 10
    );
  }

  doc.save(`${filename}.pdf`);
}

export function exportPortfolioHealthToPDF(
  portfolioHealth: {
    score: number;
    status: string;
    totalValue: number;
    totalNOI: number;
    avgOccupancy: number;
    portfolioIRR: number;
    alertCount: { critical: number; warning: number; info: number };
    lastUpdated: Date;
  },
  properties: any[],
  filename: string = 'portfolio-health-report'
) {
  const doc = new jsPDF({
    orientation: 'portrait',
    unit: 'mm',
    format: 'a4'
  });

  // Title
  doc.setFontSize(22);
  doc.setFont('helvetica', 'bold');
  doc.text('Portfolio Health Report', 105, 20, { align: 'center' });

  // Date
  doc.setFontSize(10);
  doc.setFont('helvetica', 'normal');
  doc.text(
    `Generated: ${new Date().toLocaleDateString()} ${new Date().toLocaleTimeString()}`,
    105,
    28,
    { align: 'center' }
  );

  // Health Score Section
  doc.setFontSize(16);
  doc.setFont('helvetica', 'bold');
  doc.text('Portfolio Health Score', 14, 45);

  doc.setFontSize(48);
  const scoreColor = portfolioHealth.score >= 90 ? [16, 185, 129] :
                     portfolioHealth.score >= 75 ? [59, 130, 246] :
                     portfolioHealth.score >= 60 ? [245, 158, 11] : [239, 68, 68];
  doc.setTextColor(scoreColor[0], scoreColor[1], scoreColor[2]);
  doc.text(`${portfolioHealth.score}/100`, 105, 65, { align: 'center' });

  doc.setTextColor(0, 0, 0);
  doc.setFontSize(14);
  doc.text(`Status: ${portfolioHealth.status.toUpperCase()}`, 105, 75, { align: 'center' });

  // Key Metrics Section
  doc.setFontSize(14);
  doc.setFont('helvetica', 'bold');
  doc.text('Key Metrics', 14, 90);

  const metrics = [
    ['Total Portfolio Value', `$${(portfolioHealth.totalValue / 1000000).toFixed(2)}M`],
    ['Total NOI', `$${(portfolioHealth.totalNOI / 1000).toFixed(0)}K`],
    ['Average Occupancy', `${portfolioHealth.avgOccupancy.toFixed(1)}%`],
    ['Portfolio IRR', `${portfolioHealth.portfolioIRR.toFixed(2)}%`],
    ['Critical Alerts', portfolioHealth.alertCount.critical.toString()],
    ['Warning Alerts', portfolioHealth.alertCount.warning.toString()],
  ];

  autoTable(doc, {
    body: metrics,
    startY: 95,
    theme: 'plain',
    styles: {
      fontSize: 11,
      cellPadding: 3,
    },
    columnStyles: {
      0: { fontStyle: 'bold', cellWidth: 80 },
      1: { halign: 'right' }
    }
  });

  // Property Performance Table
  const finalY = (doc as any).lastAutoTable.finalY || 95;
  doc.setFontSize(14);
  doc.setFont('helvetica', 'bold');
  doc.text('Property Performance Summary', 14, finalY + 15);

  const propertyData = properties.map(p => [
    p.name || p.property_name,
    `$${(p.value / 1000000).toFixed(1)}M`,
    `$${(p.noi / 1000).toFixed(0)}K`,
    p.dscr ? p.dscr.toFixed(2) : 'N/A',
    `${p.occupancy.toFixed(1)}%`,
    p.status === 'critical' ? '🔴' : p.status === 'warning' ? '🟡' : '🟢'
  ]);

  autoTable(doc, {
    head: [['Property', 'Value', 'NOI', 'DSCR', 'Occupancy', 'Status']],
    body: propertyData,
    startY: finalY + 20,
    styles: {
      fontSize: 9,
      cellPadding: 2,
    },
    headStyles: {
      fillColor: [99, 102, 241],
      textColor: 255,
      fontStyle: 'bold'
    },
    alternateRowStyles: {
      fillColor: [249, 250, 251]
    }
  });

  // Footer
  const pageCount = (doc as any).internal.getNumberOfPages();
  for (let i = 1; i <= pageCount; i++) {
    doc.setPage(i);
    doc.setFontSize(8);
    doc.setFont('helvetica', 'normal');
    doc.setTextColor(100, 100, 100);
    doc.text(
      'REIMS2 - Real Estate Investment Management System',
      105,
      doc.internal.pageSize.height - 10,
      { align: 'center' }
    );
    doc.text(
      `Page ${i} of ${pageCount}`,
      doc.internal.pageSize.width - 20,
      doc.internal.pageSize.height - 10
    );
  }

  doc.save(`${filename}.pdf`);
}

// ==================== Helper Functions ====================

function downloadFile(content: string, filename: string, mimeType: string) {
  const blob = new Blob([content], { type: mimeType });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(link.href);
}

// ==================== Specialized Exports ====================

export function exportPropertyListToCSV(properties: any[]) {
  const data = properties.map(p => ({
    'Property Code': p.property_code,
    'Property Name': p.property_name,
    'Type': p.property_type || 'N/A',
    'Address': p.address || 'N/A',
    'City': p.city || 'N/A',
    'State': p.state || 'N/A',
    'Status': p.status,
    'Total Area (sqft)': p.total_area_sqft || 0,
    'Acquisition Date': p.acquisition_date || 'N/A',
  }));

  exportToCSV(data, 'properties');
}

export function exportPropertyListToExcel(properties: any[]) {
  const data = properties.map(p => ({
    'Property Code': p.property_code,
    'Property Name': p.property_name,
    'Type': p.property_type || 'N/A',
    'Address': p.address || 'N/A',
    'City': p.city || 'N/A',
    'State': p.state || 'N/A',
    'Status': p.status,
    'Total Area (sqft)': p.total_area_sqft || 0,
    'Acquisition Date': p.acquisition_date || 'N/A',
  }));

  exportToExcel(data, 'properties', 'Properties');
}

export function exportFinancialStatementToExcel(
  incomeStatement: any[],
  balanceSheet: any[],
  cashFlow: any[],
  propertyName: string
) {
  const sheets = [
    {
      name: 'Income Statement',
      data: incomeStatement.map(item => ({
        'Account': item.account_name,
        'Category': item.category,
        'Amount': item.amount,
        'Period': `${item.period_year}-${String(item.period_month).padStart(2, '0')}`
      }))
    },
    {
      name: 'Balance Sheet',
      data: balanceSheet.map(item => ({
        'Account': item.account_name,
        'Category': item.category,
        'Amount': item.amount,
        'Period': `${item.period_year}-${String(item.period_month).padStart(2, '0')}`
      }))
    },
    {
      name: 'Cash Flow',
      data: cashFlow.map(item => ({
        'Account': item.account_name,
        'Category': item.category,
        'Amount': item.amount,
        'Period': `${item.period_year}-${String(item.period_month).padStart(2, '0')}`
      }))
    }
  ];

  exportMultiSheetExcel(sheets, `financial-statements-${propertyName.replace(/\s+/g, '-').toLowerCase()}`);
}
