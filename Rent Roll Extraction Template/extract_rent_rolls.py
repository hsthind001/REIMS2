#!/usr/bin/env python3
"""
Rent Roll Data Extraction Script v2.0
Extracts data from commercial property rent roll PDFs following
the comprehensive template requirements.
"""

import re
import csv
import json
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path
import pdfplumber

class RentRollExtractor:
    """Extracts and validates rent roll data from PDF documents."""
    
    def __init__(self, pdf_path: str):
        self.pdf_path = Path(pdf_path)
        self.property_code = self._extract_property_code()
        self.report_date = None
        self.records = []
        self.vacant_units = []
        self.gross_rent_rows = []
        self.summary_data = {}
        self.validation_flags = []
        
    def _extract_property_code(self) -> str:
        """Extract property code from filename."""
        name = self.pdf_path.stem.lower()
        if 'hammond' in name:
            return 'HMND'
        elif 'tcsh' in name or 'spring' in name:
            return 'TCSH'
        elif 'wendover' in name:
            return 'WEND'
        elif 'esp' in name or 'eastern' in name:
            return 'ESP'
        return 'UNKNOWN'
    
    def extract(self) -> Dict[str, Any]:
        """Main extraction method."""
        print(f"\n{'='*60}")
        print(f"Extracting: {self.pdf_path.name}")
        print(f"Property Code: {self.property_code}")
        print(f"{'='*60}")
        
        with pdfplumber.open(self.pdf_path) as pdf:
            # Extract report date from first page
            first_page = pdf.pages[0]
            self.report_date = self._extract_report_date(first_page.extract_text())
            print(f"Report Date: {self.report_date}")
            
            # Process each page
            for page_num, page in enumerate(pdf.pages, 1):
                print(f"\nProcessing page {page_num}/{len(pdf.pages)}...")
                self._process_page(page, page_num)
        
        # Validate and prepare output
        self._validate_data()
        self._calculate_summaries()
        
        return self._prepare_output()
    
    def _extract_report_date(self, text: str) -> str:
        """Extract report date from text."""
        # Look for "As of Date: MM/DD/YYYY"
        match = re.search(r'As of Date:\s*(\d{2}/\d{2}/\d{4})', text)
        if match:
            date_str = match.group(1)
            # Convert to ISO format
            dt = datetime.strptime(date_str, '%m/%d/%Y')
            return dt.strftime('%Y-%m-%d')
        return None
    
    def _process_page(self, page, page_num: int):
        """Process a single page."""
        # Extract tables from page
        tables = page.extract_tables()
        
        if not tables:
            print(f"  No tables found on page {page_num}")
            return
        
        # Process main table (usually the largest one)
        main_table = max(tables, key=lambda t: len(t) if t else 0)
        
        if not main_table:
            return
            
        print(f"  Found table with {len(main_table)} rows")
        
        # Identify header row and process data rows
        headers = self._identify_headers(main_table)
        if headers:
            self._process_table_rows(main_table, headers, page_num)
    
    def _identify_headers(self, table: List[List[str]]) -> Optional[Dict[str, int]]:
        """Identify column headers and their positions."""
        # Look for header row (usually row 0 or 1)
        for row in table[:3]:
            if not row:
                continue
            
            # Check if this looks like a header row
            row_text = ' '.join([str(cell or '') for cell in row]).lower()
            if 'unit' in row_text and 'lease' in row_text and 'area' in row_text:
                # Map headers to indices
                headers = {}
                for idx, cell in enumerate(row):
                    if cell:
                        header_clean = cell.strip().lower()
                        headers[header_clean] = idx
                return headers
        
        # If no header found, use default positions based on template
        print("  Warning: Using default column positions")
        return {
            'property': 0,
            'unit(s)': 1,
            'lease': 2,
            'lease type': 3,
            'area': 4,
            'lease from': 5,
            'lease to': 6,
            'term': 7,
            'tenancy years': 8,
            'monthly rent': 9,
            'monthly rent/area': 10,
            'annual rent': 11,
            'annual rent/area': 12,
        }
    
    def _process_table_rows(self, table: List[List[str]], headers: Dict[str, int], page_num: int):
        """Process data rows from table."""
        current_property = None
        parent_row_id = None
        
        for row_idx, row in enumerate(table):
            if not row or len(row) < 5:
                continue
            
            # Skip header rows
            row_text = ' '.join([str(cell or '') for cell in row]).lower()
            if 'property' in row_text and 'unit' in row_text:
                continue
            if 'occupancy summary' in row_text:
                # Start of summary section
                self._process_summary_section(table[row_idx:])
                break
            
            # Check if this is a property name row, regular lease row, gross rent row, or vacant
            record = self._parse_row(row, headers, current_property)
            
            if record:
                if record.get('property_name'):
                    current_property = record['property_name']
                
                if record.get('is_gross_rent_row'):
                    # Link to parent
                    if parent_row_id:
                        record['parent_row_id'] = parent_row_id
                    self.gross_rent_rows.append(record)
                elif record.get('is_vacant'):
                    self.vacant_units.append(record)
                else:
                    parent_row_id = len(self.records) + 1
                    record['row_id'] = parent_row_id
                    self.records.append(record)
    
    def _parse_row(self, row: List[str], headers: Dict[str, int], 
                   current_property: str) -> Optional[Dict[str, Any]]:
        """Parse a single data row."""
        record = {
            'property_code': self.property_code,
            'report_date': self.report_date,
            'is_vacant': False,
            'is_gross_rent_row': False,
        }
        
        # Extract property name
        prop_cell = self._get_cell(row, headers, 'property')
        if prop_cell and prop_cell.strip() and 'Gross Rent' not in prop_cell:
            # Extract property name and code
            match = re.match(r'(.+?)\((\w+)\)', prop_cell)
            if match:
                record['property_name'] = match.group(1).strip()
                current_property = record['property_name']
        elif current_property:
            record['property_name'] = current_property
        
        # Check for Gross Rent row
        if prop_cell and 'Gross Rent' in prop_cell:
            record['is_gross_rent_row'] = True
            record['property_name'] = current_property
        
        # Extract unit number
        unit = self._get_cell(row, headers, 'unit(s)')
        if not unit or not unit.strip():
            return None
        record['unit_number'] = unit.strip()
        
        # Extract tenant name
        tenant = self._get_cell(row, headers, 'lease')
        if tenant:
            tenant = tenant.strip()
            if tenant.upper() == 'VACANT':
                record['is_vacant'] = True
                record['tenant_name'] = 'VACANT'
            else:
                # Extract tenant name and ID
                match = re.match(r'(.+?)\s*\(t\d+\)', tenant)
                if match:
                    record['tenant_name'] = match.group(1).strip()
                    # Extract ID
                    id_match = re.search(r'\(t(\d+)\)', tenant)
                    if id_match:
                        record['tenant_id'] = f"t{id_match.group(1)}"
                else:
                    record['tenant_name'] = tenant
        
        # Extract lease type
        lease_type = self._get_cell(row, headers, 'lease type')
        if lease_type and lease_type.strip():
            record['lease_type'] = lease_type.strip()
        
        # Extract area
        area = self._get_cell(row, headers, 'area')
        if area:
            record['area_sqft'] = self._parse_number(area)
        
        # Extract dates
        lease_from = self._get_cell(row, headers, 'lease from')
        if lease_from:
            record['lease_from_date'] = self._parse_date(lease_from)
        
        lease_to = self._get_cell(row, headers, 'lease to')
        if lease_to:
            record['lease_to_date'] = self._parse_date(lease_to)
        
        # Extract term
        term = self._get_cell(row, headers, 'term')
        if term:
            record['term_months'] = self._parse_number(term, as_int=True)
        
        # Extract tenancy years
        tenancy = self._get_cell(row, headers, 'tenancy years')
        if tenancy:
            record['tenancy_years'] = self._parse_number(tenancy)
        
        # Extract financial data
        monthly_rent = self._get_cell(row, headers, 'monthly rent')
        if monthly_rent:
            record['monthly_rent'] = self._parse_number(monthly_rent)
        
        monthly_rent_area = self._get_cell(row, headers, 'monthly rent/area')
        if monthly_rent_area:
            record['monthly_rent_per_sf'] = self._parse_number(monthly_rent_area)
        
        annual_rent = self._get_cell(row, headers, 'annual rent')
        if annual_rent:
            record['annual_rent'] = self._parse_number(annual_rent)
        
        annual_rent_area = self._get_cell(row, headers, 'annual rent/area')
        if annual_rent_area:
            record['annual_rent_per_sf'] = self._parse_number(annual_rent_area)
        
        # Try to get additional columns if present
        security = self._get_cell(row, headers, 'security deposit received')
        if security:
            record['security_deposit'] = self._parse_number(security)
        
        loc = self._get_cell(row, headers, 'loc amount/ bank guarantee')
        if loc:
            record['loc_bank_guarantee'] = self._parse_number(loc)
        
        return record
    
    def _get_cell(self, row: List[str], headers: Dict[str, int], 
                  header_name: str) -> Optional[str]:
        """Safely get cell value by header name."""
        if header_name in headers:
            idx = headers[header_name]
            if idx < len(row):
                return row[idx]
        return None
    
    def _parse_number(self, value: str, as_int: bool = False) -> Optional[float]:
        """Parse a number from string, handling commas and formatting."""
        if not value or not isinstance(value, str):
            return None
        
        # Remove commas, spaces, dollar signs
        clean = value.replace(',', '').replace('$', '').replace(' ', '').strip()
        
        if not clean or clean == '-':
            return None
        
        try:
            num = float(clean)
            return int(num) if as_int else round(num, 2)
        except ValueError:
            return None
    
    def _parse_date(self, value: str) -> Optional[str]:
        """Parse date and return in ISO format."""
        if not value or not isinstance(value, str):
            return None
        
        # Try different date formats
        formats = ['%m/%d/%Y', '%m/%d/%y']
        
        for fmt in formats:
            try:
                dt = datetime.strptime(value.strip(), fmt)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue
        
        return None
    
    def _process_summary_section(self, rows: List[List[str]]):
        """Process occupancy summary section."""
        for row in rows:
            if not row:
                continue
            
            row_text = ' '.join([str(cell or '') for cell in row])
            
            # Extract key metrics
            if 'Occupied Area' in row_text:
                # Extract occupied area and percentage
                numbers = re.findall(r'[\d,]+\.?\d*', row_text)
                if len(numbers) >= 2:
                    self.summary_data['occupied_area'] = self._parse_number(numbers[0])
                    self.summary_data['occupancy_pct'] = self._parse_number(numbers[1])
            
            elif 'Vacant Area' in row_text:
                numbers = re.findall(r'[\d,]+\.?\d*', row_text)
                if len(numbers) >= 2:
                    self.summary_data['vacant_area'] = self._parse_number(numbers[0])
                    self.summary_data['vacancy_pct'] = self._parse_number(numbers[1])
            
            elif 'Grand Total' in row_text or 'Total' in row_text:
                numbers = re.findall(r'[\d,]+\.?\d*', row_text)
                if numbers:
                    self.summary_data['total_area'] = self._parse_number(numbers[0])
    
    def _validate_data(self):
        """Validate extracted data against business rules."""
        print(f"\n{'='*60}")
        print("Validating extracted data...")
        print(f"{'='*60}")
        
        for idx, record in enumerate(self.records, 1):
            # Validate financial math
            if record.get('monthly_rent') and record.get('annual_rent'):
                calculated_annual = record['monthly_rent'] * 12
                actual_annual = record['annual_rent']
                diff_pct = abs(calculated_annual - actual_annual) / actual_annual * 100
                
                if diff_pct > 2:
                    self.validation_flags.append({
                        'severity': 'WARNING',
                        'record_id': idx,
                        'unit': record.get('unit_number'),
                        'message': f'Annual rent mismatch: Expected {calculated_annual:.2f}, got {actual_annual:.2f} ({diff_pct:.1f}% diff)'
                    })
            
            # Validate rent per SF
            if (record.get('monthly_rent') and record.get('area_sqft') and 
                record['area_sqft'] > 0 and record.get('monthly_rent_per_sf')):
                calculated_per_sf = record['monthly_rent'] / record['area_sqft']
                actual_per_sf = record['monthly_rent_per_sf']
                diff = abs(calculated_per_sf - actual_per_sf)
                
                if diff > 0.05:
                    self.validation_flags.append({
                        'severity': 'WARNING',
                        'record_id': idx,
                        'unit': record.get('unit_number'),
                        'message': f'Rent per SF mismatch: Expected {calculated_per_sf:.2f}, got {actual_per_sf:.2f}'
                    })
            
            # Validate date sequence
            if record.get('lease_from_date') and record.get('lease_to_date'):
                from_date = datetime.strptime(record['lease_from_date'], '%Y-%m-%d')
                to_date = datetime.strptime(record['lease_to_date'], '%Y-%m-%d')
                
                if to_date < from_date:
                    self.validation_flags.append({
                        'severity': 'CRITICAL',
                        'record_id': idx,
                        'unit': record.get('unit_number'),
                        'message': f'Lease To date {record["lease_to_date"]} is before Lease From date {record["lease_from_date"]}'
                    })
            
            # Check for expired leases
            if record.get('lease_to_date') and self.report_date:
                to_date = datetime.strptime(record['lease_to_date'], '%Y-%m-%d')
                report_dt = datetime.strptime(self.report_date, '%Y-%m-%d')
                
                if to_date < report_dt:
                    self.validation_flags.append({
                        'severity': 'WARNING',
                        'record_id': idx,
                        'unit': record.get('unit_number'),
                        'message': f'Lease expired on {record["lease_to_date"]} but tenant still listed (possible holdover)'
                    })
        
        # Print validation summary
        critical = [f for f in self.validation_flags if f['severity'] == 'CRITICAL']
        warnings = [f for f in self.validation_flags if f['severity'] == 'WARNING']
        
        print(f"\nValidation Results:")
        print(f"  Total Records: {len(self.records)}")
        print(f"  Vacant Units: {len(self.vacant_units)}")
        print(f"  Gross Rent Rows: {len(self.gross_rent_rows)}")
        print(f"  Critical Issues: {len(critical)}")
        print(f"  Warnings: {len(warnings)}")
        
        if critical:
            print(f"\nCRITICAL ISSUES:")
            for flag in critical:
                print(f"  - Unit {flag['unit']}: {flag['message']}")
        
        if warnings and len(warnings) <= 10:
            print(f"\nWARNINGS:")
            for flag in warnings:
                print(f"  - Unit {flag['unit']}: {flag['message']}")
        elif warnings:
            print(f"\nWARNINGS: {len(warnings)} warnings found (showing first 5):")
            for flag in warnings[:5]:
                print(f"  - Unit {flag['unit']}: {flag['message']}")
    
    def _calculate_summaries(self):
        """Calculate summary statistics."""
        # Calculate totals
        total_monthly_rent = sum(r.get('monthly_rent', 0) or 0 for r in self.records)
        total_annual_rent = sum(r.get('annual_rent', 0) or 0 for r in self.records)
        total_area = sum(r.get('area_sqft', 0) or 0 for r in self.records)
        vacant_area = sum(r.get('area_sqft', 0) or 0 for r in self.vacant_units)
        
        self.summary_data.update({
            'total_monthly_rent': round(total_monthly_rent, 2),
            'total_annual_rent': round(total_annual_rent, 2),
            'number_of_leases': len(self.records),
            'number_vacant_units': len(self.vacant_units),
        })
        
        # Calculate average rent per SF
        if total_area > 0:
            self.summary_data['avg_monthly_rent_per_sf'] = round(total_monthly_rent / total_area, 2)
            self.summary_data['avg_annual_rent_per_sf'] = round(total_annual_rent / total_area, 2)
    
    def _prepare_output(self) -> Dict[str, Any]:
        """Prepare final output package."""
        return {
            'property_code': self.property_code,
            'report_date': self.report_date,
            'records': self.records,
            'vacant_units': self.vacant_units,
            'gross_rent_rows': self.gross_rent_rows,
            'summary': self.summary_data,
            'validation_flags': self.validation_flags,
            'quality_score': self._calculate_quality_score(),
        }
    
    def _calculate_quality_score(self) -> float:
        """Calculate overall quality score."""
        total_records = len(self.records) + len(self.vacant_units)
        if total_records == 0:
            return 0.0
        
        # Count critical and warning flags
        critical_count = len([f for f in self.validation_flags if f['severity'] == 'CRITICAL'])
        warning_count = len([f for f in self.validation_flags if f['severity'] == 'WARNING'])
        
        # Calculate score (100 - penalties)
        score = 100.0
        score -= critical_count * 5  # -5% per critical issue
        score -= warning_count * 1   # -1% per warning
        
        return max(0.0, min(100.0, score))


def save_to_csv(data: Dict[str, Any], output_dir: Path):
    """Save extracted data to CSV files."""
    output_dir.mkdir(exist_ok=True)
    
    property_code = data['property_code']
    report_date_str = data['report_date'].replace('-', '')
    
    # Save main rent roll data
    rent_roll_file = output_dir / f"{property_code}_RentRoll_{report_date_str}_v1.csv"
    
    fieldnames = [
        'property_name', 'property_code', 'report_date', 'unit_number',
        'tenant_name', 'tenant_id', 'lease_type', 'area_sqft',
        'lease_from_date', 'lease_to_date', 'term_months', 'tenancy_years',
        'monthly_rent', 'monthly_rent_per_sf', 'annual_rent', 'annual_rent_per_sf',
        'security_deposit', 'loc_bank_guarantee', 'is_vacant', 'notes'
    ]
    
    with open(rent_roll_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        
        # Write active leases
        for record in data['records']:
            writer.writerow(record)
        
        # Write vacant units
        for record in data['vacant_units']:
            writer.writerow(record)
    
    print(f"\n✓ Saved rent roll data to: {rent_roll_file}")
    
    # Save summary data
    summary_file = output_dir / f"{property_code}_Summary_{report_date_str}_v1.csv"
    with open(summary_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=data['summary'].keys())
        writer.writeheader()
        writer.writerow(data['summary'])
    
    print(f"✓ Saved summary data to: {summary_file}")
    
    # Save validation report
    validation_file = output_dir / f"{property_code}_Validation_{report_date_str}.txt"
    with open(validation_file, 'w', encoding='utf-8') as f:
        f.write(f"Rent Roll Extraction Validation Report\n")
        f.write(f"{'='*60}\n\n")
        f.write(f"Property: {property_code}\n")
        f.write(f"Report Date: {data['report_date']}\n")
        f.write(f"Extraction Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"Summary:\n")
        f.write(f"  Total Active Leases: {len(data['records'])}\n")
        f.write(f"  Vacant Units: {len(data['vacant_units'])}\n")
        f.write(f"  Gross Rent Rows: {len(data['gross_rent_rows'])}\n")
        f.write(f"  Validation Flags: {len(data['validation_flags'])}\n")
        f.write(f"  Quality Score: {data['quality_score']:.1f}%\n\n")
        
        if data['validation_flags']:
            f.write(f"Validation Issues:\n")
            f.write(f"{'-'*60}\n")
            for flag in data['validation_flags']:
                f.write(f"{flag['severity']}: Unit {flag.get('unit', 'N/A')}\n")
                f.write(f"  {flag['message']}\n\n")
        
        # Recommendation
        if data['quality_score'] >= 99 and not any(f['severity'] == 'CRITICAL' for f in data['validation_flags']):
            f.write(f"\nRECOMMENDATION: AUTO-APPROVE\n")
        else:
            f.write(f"\nRECOMMENDATION: HUMAN REVIEW REQUIRED\n")
    
    print(f"✓ Saved validation report to: {validation_file}")


def main():
    """Main execution function."""
    print("\n" + "="*60)
    print("RENT ROLL EXTRACTION SCRIPT v2.0")
    print("="*60)
    
    # Input and output directories
    input_dir = Path('/mnt/user-data/uploads')
    output_dir = Path('/mnt/user-data/outputs')
    
    # Find all rent roll PDFs
    pdf_files = list(input_dir.glob('*Rent*Roll*.pdf'))
    pdf_files.extend(input_dir.glob('*Roll*2025.pdf'))  # Also match files like "ESP_Roll_April_2025.pdf"
    pdf_files = list(set(pdf_files))  # Remove duplicates
    
    if not pdf_files:
        print("\nNo rent roll PDF files found!")
        return
    
    print(f"\nFound {len(pdf_files)} rent roll file(s)")
    
    # Process each file
    results = []
    for pdf_file in pdf_files:
        try:
            extractor = RentRollExtractor(pdf_file)
            data = extractor.extract()
            save_to_csv(data, output_dir)
            results.append(data)
        except Exception as e:
            print(f"\n✗ Error processing {pdf_file.name}: {str(e)}")
            import traceback
            traceback.print_exc()
    
    # Final summary
    print(f"\n{'='*60}")
    print("EXTRACTION COMPLETE")
    print(f"{'='*60}")
    print(f"\nProcessed {len(results)} file(s)")
    
    for result in results:
        status = "✓ PASS" if result['quality_score'] >= 95 else "⚠ REVIEW NEEDED"
        print(f"  {result['property_code']}: {status} (Quality: {result['quality_score']:.1f}%)")
    
    print(f"\nOutput files saved to: {output_dir}")
    print("\nNext steps:")
    print("1. Review validation reports for any issues")
    print("2. Verify summary totals match source documents")
    print("3. Check for any missing or vacant units")
    print("4. Review any flagged warnings or critical issues")


if __name__ == '__main__':
    main()
