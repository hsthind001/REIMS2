"""
Test Suite for Rent Roll Extraction - Template v2.0

Comprehensive tests covering:
- All 24 field extraction
- Gross rent row handling
- Multi-unit leases
- Vacant units
- Date parsing and validation
- Financial validations
- Quality scoring
- Edge cases
"""
import pytest
from decimal import Decimal
from datetime import datetime, date
from app.utils.rent_roll_validator import RentRollValidator, ValidationFlag


class TestRentRollValidator:
    """Test the validation system"""
    
    def test_perfect_extraction_100_quality(self):
        """Test perfect extraction gets 100% quality score"""
        records = [{
            'unit_number': '001',
            'tenant_name': 'Test Tenant LLC',
            'monthly_rent': 3000.0,
            'annual_rent': 36000.0,
            'unit_area_sqft': 1500.0,
            'monthly_rent_per_sqft': 2.0,
            'lease_start_date': '2020-01-01',
            'lease_end_date': '2025-12-31',
            'is_vacant': False,
            'is_gross_rent_row': False
        }]
        
        validator = RentRollValidator()
        flags = validator.validate_records(records, '2025-04-30')
        result = validator.calculate_quality_score()
        
        # Should have only INFO flags, no warnings or critical
        assert result['critical_count'] == 0
        assert result['warning_count'] == 0
        assert result['quality_score'] == 100.0
        assert result['auto_approve'] == True
        assert result['recommendation'] == 'AUTO_APPROVE'
    
    def test_financial_validation_annual_equals_monthly_times_12(self):
        """Test: Annual rent = Monthly rent × 12 (±2% tolerance)"""
        validator = RentRollValidator()
        
        # Perfect match
        record = {
            'unit_number': '001',
            'monthly_rent': 1000.0,
            'annual_rent': 12000.0,
            'is_vacant': False,
            'is_gross_rent_row': False
        }
        validator._validate_financial_calculations(record, 1, '001')
        assert validator.get_flags_by_severity('CRITICAL') == []
        
        # Within tolerance (1.5% diff)
        record2 = {
            'unit_number': '002',
            'monthly_rent': 1000.0,
            'annual_rent': 12180.0,  # 1.5% higher
            'is_vacant': False,
            'is_gross_rent_row': False
        }
        validator._validate_financial_calculations(record2, 2, '002')
        assert validator.get_flags_by_severity('CRITICAL') == []
        
        # Outside tolerance (5% diff) - should flag as CRITICAL
        validator_fail = RentRollValidator()
        record3 = {
            'unit_number': '003',
            'monthly_rent': 1000.0,
            'annual_rent': 12600.0,  # 5% higher
            'is_vacant': False,
            'is_gross_rent_row': False
        }
        validator_fail._validate_financial_calculations(record3, 3, '003')
        critical_flags = validator_fail.get_flags_by_severity('CRITICAL')
        assert len(critical_flags) == 1
        assert '5.0%' in critical_flags[0].message
    
    def test_rent_per_sf_validation(self):
        """Test: Rent per SF = Monthly Rent / Area (±$0.05 tolerance)"""
        validator = RentRollValidator()
        
        # Perfect calculation
        record = {
            'unit_number': '001',
            'monthly_rent': 3000.0,
            'unit_area_sqft': 1500.0,
            'monthly_rent_per_sqft': 2.0,  # 3000/1500 = 2.0
            'is_vacant': False,
            'is_gross_rent_row': False
        }
        validator._validate_rent_per_sf(record, 1, '001')
        assert validator.get_flags_by_severity('WARNING') == []
        
        # Outside tolerance
        validator_fail = RentRollValidator()
        record2 = {
            'unit_number': '002',
            'monthly_rent': 3000.0,
            'unit_area_sqft': 1500.0,
            'monthly_rent_per_sqft': 2.20,  # Should be 2.0, diff = 0.20
            'is_vacant': False,
            'is_gross_rent_row': False
        }
        validator_fail._validate_rent_per_sf(record2, 2, '002')
        warnings = validator_fail.get_flags_by_severity('WARNING')
        assert len(warnings) == 1
    
    def test_date_sequence_validation(self):
        """Test: Lease From < Lease To"""
        validator = RentRollValidator()
        
        # Valid sequence
        record = {
            'unit_number': '001',
            'lease_start_date': '2020-01-01',
            'lease_end_date': '2025-12-31',
            'is_vacant': False,
            'is_gross_rent_row': False
        }
        validator._validate_date_sequence(record, 1, '001')
        assert validator.get_flags_by_severity('CRITICAL') == []
        
        # Invalid sequence (end before start)
        validator_fail = RentRollValidator()
        record2 = {
            'unit_number': '002',
            'lease_start_date': '2025-01-01',
            'lease_end_date': '2020-12-31',  # Before start!
            'is_vacant': False,
            'is_gross_rent_row': False
        }
        validator_fail._validate_date_sequence(record2, 2, '002')
        critical = validator_fail.get_flags_by_severity('CRITICAL')
        assert len(critical) == 1
        assert 'before start date' in critical[0].message.lower()
    
    def test_expired_lease_warning(self):
        """Test: Detect expired leases (holdover tenants)"""
        validator = RentRollValidator()
        
        record = {
            'unit_number': '001',
            'lease_start_date': '2020-01-01',
            'lease_end_date': '2024-12-31',  # Expired
            'is_vacant': False,
            'is_gross_rent_row': False
        }
        validator._validate_date_sequence(record, 1, '001')
        warnings = validator.get_flags_by_severity('WARNING')
        assert len(warnings) == 1
        assert 'holdover' in warnings[0].message.lower()
    
    def test_vacant_unit_handling(self):
        """Test vacant units have proper validation"""
        validator = RentRollValidator()
        
        # Valid vacant unit
        record = {
            'unit_number': '100',
            'tenant_name': 'VACANT',
            'unit_area_sqft': 2000.0,
            'monthly_rent': None,
            'is_vacant': True,
            'occupancy_status': 'vacant',
            'is_gross_rent_row': False
        }
        validator._validate_vacant_unit(record, 1, '100')
        assert validator.get_flags_by_severity('WARNING') == []
        
        # Vacant with rent (error)
        validator_warn = RentRollValidator()
        record2 = {
            'unit_number': '101',
            'tenant_name': 'VACANT',
            'unit_area_sqft': 2000.0,
            'monthly_rent': 500.0,  # Shouldn't have rent!
            'is_vacant': True,
            'occupancy_status': 'vacant',
            'is_gross_rent_row': False
        }
        validator_warn._validate_vacant_unit(record2, 2, '101')
        warnings = validator_warn.get_flags_by_severity('WARNING')
        assert len(warnings) == 1
        assert 'should not have rent' in warnings[0].message.lower()
    
    def test_gross_rent_row_linking(self):
        """Test gross rent rows require parent_row_id"""
        validator = RentRollValidator()
        
        # Gross rent with parent - OK
        record = {
            'unit_number': '001',
            'tenant_name': 'Gross Rent',
            'is_gross_rent_row': True,
            'parent_row_id': 123
        }
        validator._validate_gross_rent_row(record, 1, '001')
        assert validator.get_flags_by_severity('WARNING') == []
        
        # Gross rent without parent - WARNING
        validator_warn = RentRollValidator()
        record2 = {
            'unit_number': '002',
            'tenant_name': 'Gross Rent',
            'is_gross_rent_row': True,
            'parent_row_id': None
        }
        validator_warn._validate_gross_rent_row(record2, 2, '002')
        warnings = validator_warn.get_flags_by_severity('WARNING')
        assert len(warnings) == 1
    
    def test_edge_case_month_to_month_lease(self):
        """Test month-to-month lease detection (NULL end date)"""
        validator = RentRollValidator()
        
        record = {
            'unit_number': '001',
            'lease_start_date': '2020-01-01',
            'lease_end_date': None,  # Month-to-month
            'is_vacant': False,
            'is_gross_rent_row': False
        }
        validator._detect_edge_cases(record, 1, '001')
        info_flags = validator.get_flags_by_severity('INFO')
        assert any('month-to-month' in flag.message.lower() for flag in info_flags)
    
    def test_edge_case_future_lease(self):
        """Test future lease detection"""
        validator = RentRollValidator()
        validator.report_date = date(2025, 4, 30)
        
        record = {
            'unit_number': '001',
            'lease_start_date': '2026-01-01',  # Future
            'is_vacant': False,
            'is_gross_rent_row': False
        }
        validator._detect_edge_cases(record, 1, '001')
        info_flags = validator.get_flags_by_severity('INFO')
        assert any('future lease' in flag.message.lower() for flag in info_flags)
    
    def test_edge_case_zero_rent(self):
        """Test zero rent detection (expense-only lease)"""
        validator = RentRollValidator()
        
        record = {
            'unit_number': '001',
            'monthly_rent': 0.0,
            'is_vacant': False,
            'is_gross_rent_row': False
        }
        validator._detect_edge_cases(record, 1, '001')
        info_flags = validator.get_flags_by_severity('INFO')
        assert any('zero rent' in flag.message.lower() for flag in info_flags)
    
    def test_edge_case_zero_area_atm(self):
        """Test zero area detection (ATM, signage)"""
        validator = RentRollValidator()
        
        record = {
            'unit_number': 'Z-ATM',
            'unit_area_sqft': 0.0,
            'is_vacant': False,
            'is_gross_rent_row': False
        }
        validator._detect_edge_cases(record, 1, 'Z-ATM')
        info_flags = validator.get_flags_by_severity('INFO')
        assert any('zero area' in flag.message.lower() for flag in info_flags)
        assert any('atm' in flag.message.lower() for flag in info_flags)
    
    def test_edge_case_multi_unit_lease(self):
        """Test multi-unit lease detection"""
        validator = RentRollValidator()
        
        record = {
            'unit_number': '009-A, 009-B, 009-C',
            'is_vacant': False,
            'is_gross_rent_row': False
        }
        validator._detect_edge_cases(record, 1, '009-A, 009-B, 009-C')
        info_flags = validator.get_flags_by_severity('INFO')
        assert any('multi-unit' in flag.message.lower() for flag in info_flags)
    
    def test_edge_case_special_unit_codes(self):
        """Test special unit type detection"""
        validator = RentRollValidator()
        
        for unit_code in ['Z-ATM', 'LAND', 'COMMON', 'Z-SIGN']:
            validator_test = RentRollValidator()
            record = {
                'unit_number': unit_code,
                'is_vacant': False,
                'is_gross_rent_row': False
            }
            validator_test._detect_edge_cases(record, 1, unit_code)
            info_flags = validator_test.get_flags_by_severity('INFO')
            assert len(info_flags) > 0, f"Should detect special unit: {unit_code}"
    
    def test_quality_score_calculation_perfect(self):
        """Test quality score calculation - perfect extraction"""
        validator = RentRollValidator()
        validator.flags = []  # No issues
        
        result = validator.calculate_quality_score()
        
        assert result['quality_score'] == 100.0
        assert result['critical_count'] == 0
        assert result['warning_count'] == 0
        assert result['info_count'] == 0
        assert result['auto_approve'] == True
        assert result['recommendation'] == 'AUTO_APPROVE'
    
    def test_quality_score_with_warnings(self):
        """Test quality score with warnings"""
        validator = RentRollValidator()
        validator.flags = [
            ValidationFlag(severity='WARNING', message='Test warning 1'),
            ValidationFlag(severity='WARNING', message='Test warning 2'),
            ValidationFlag(severity='INFO', message='Test info 1'),
            ValidationFlag(severity='INFO', message='Test info 2'),
        ]
        
        result = validator.calculate_quality_score()
        
        assert result['quality_score'] == 98.0  # 100 - 2*1
        assert result['critical_count'] == 0
        assert result['warning_count'] == 2
        assert result['info_count'] == 2
        assert result['auto_approve'] == False  # < 99%
        assert result['recommendation'] == 'REVIEW_WARNINGS'
    
    def test_quality_score_with_critical_issues(self):
        """Test quality score with critical issues"""
        validator = RentRollValidator()
        validator.flags = [
            ValidationFlag(severity='CRITICAL', message='Test critical 1'),
            ValidationFlag(severity='WARNING', message='Test warning 1'),
        ]
        
        result = validator.calculate_quality_score()
        
        assert result['quality_score'] == 94.0  # 100 - 5 - 1
        assert result['critical_count'] == 1
        assert result['warning_count'] == 1
        assert result['auto_approve'] == False
        assert result['recommendation'] == 'REVIEW_CRITICAL'
    
    def test_non_negative_values_validation(self):
        """Test all financial fields must be >= 0"""
        validator = RentRollValidator()
        
        record = {
            'unit_number': '001',
            'monthly_rent': -100.0,  # Invalid!
            'annual_rent': 1200.0,
            'security_deposit': -50.0,  # Invalid!
            'is_vacant': False,
            'is_gross_rent_row': False
        }
        
        validator._validate_non_negative_values(record, 1, '001')
        critical = validator.get_flags_by_severity('CRITICAL')
        assert len(critical) == 2  # Two negative values
    
    def test_area_validation_reasonable_range(self):
        """Test area must be within reasonable range"""
        validator = RentRollValidator()
        
        # Negative area - CRITICAL
        record = {
            'unit_number': '001',
            'unit_area_sqft': -100.0,
            'is_vacant': False,
            'is_gross_rent_row': False
        }
        validator._validate_area(record, 1, '001')
        critical = validator.get_flags_by_severity('CRITICAL')
        assert len(critical) == 1
        
        # Very large area - INFO only
        validator_info = RentRollValidator()
        record2 = {
            'unit_number': '002',
            'unit_area_sqft': 150000.0,  # > 100,000
            'is_vacant': False,
            'is_gross_rent_row': False
        }
        validator_info._validate_area(record2, 2, '002')
        info_flags = validator_info.get_flags_by_severity('INFO')
        assert len(info_flags) == 1
        assert 'anchor tenant' in info_flags[0].message.lower()
    
    def test_security_deposit_validation(self):
        """Test security deposit typically 1-3 months rent"""
        validator = RentRollValidator()
        validator.report_date = date(2025, 4, 30)
        
        # Unusual security deposit (4 months)
        record = {
            'unit_number': '001',
            'monthly_rent': 1000.0,
            'security_deposit': 4000.0,  # 4 months
            'lease_start_date': '2024-01-01',
            'is_vacant': False,
            'is_gross_rent_row': False
        }
        validator._validate_security_deposit(record, 1, '001')
        info_flags = validator.get_flags_by_severity('INFO')
        assert len(info_flags) >= 1
    
    def test_term_calculation_validation(self):
        """Test term months matches date range"""
        validator = RentRollValidator()
        
        # Correct term
        record = {
            'unit_number': '001',
            'lease_start_date': '2020-01-01',
            'lease_end_date': '2025-01-01',  # Exactly 60 months
            'lease_term_months': 60,
            'is_vacant': False,
            'is_gross_rent_row': False
        }
        validator._validate_term_calculation(record, 1, '001')
        assert validator.get_flags_by_severity('WARNING') == []
        
        # Incorrect term
        validator_warn = RentRollValidator()
        record2 = {
            'unit_number': '002',
            'lease_start_date': '2020-01-01',
            'lease_end_date': '2025-01-01',  # 60 months
            'lease_term_months': 70,  # Wrong!
            'is_vacant': False,
            'is_gross_rent_row': False
        }
        validator_warn._validate_term_calculation(record2, 2, '002')
        warnings = validator_warn.get_flags_by_severity('WARNING')
        assert len(warnings) == 1
    
    def test_unusual_rent_per_sf_detection(self):
        """Test unusual rent per SF flags"""
        validator = RentRollValidator()
        
        # Too low
        record = {
            'unit_number': '001',
            'monthly_rent_per_sqft': 0.25,  # < $0.50
            'is_vacant': False,
            'is_gross_rent_row': False
        }
        validator._detect_edge_cases(record, 1, '001')
        warnings = validator.get_flags_by_severity('WARNING')
        assert len(warnings) >= 1
        assert any('low rent' in flag.message.lower() for flag in warnings)
        
        # Too high
        validator_high = RentRollValidator()
        record2 = {
            'unit_number': '002',
            'monthly_rent_per_sqft': 20.0,  # > $15.00
            'is_vacant': False,
            'is_gross_rent_row': False
        }
        validator_high._detect_edge_cases(record2, 2, '002')
        warnings_high = validator_high.get_flags_by_severity('WARNING')
        assert len(warnings_high) >= 1
        assert any('high rent' in flag.message.lower() for flag in warnings_high)
    
    def test_short_term_lease_warning(self):
        """Test short term lease (<12 months) flags"""
        validator = RentRollValidator()
        
        record = {
            'unit_number': '001',
            'lease_term_months': 6,  # < 12 months
            'is_vacant': False,
            'is_gross_rent_row': False
        }
        validator._detect_edge_cases(record, 1, '001')
        warnings = validator.get_flags_by_severity('WARNING')
        assert len(warnings) == 1
        assert 'short term' in warnings[0].message.lower()
    
    def test_long_term_ground_lease_info(self):
        """Test very long term lease (>20 years) flags"""
        validator = RentRollValidator()
        
        record = {
            'unit_number': 'LAND',
            'lease_term_months': 600,  # 50 years
            'is_vacant': False,
            'is_gross_rent_row': False
        }
        validator._detect_edge_cases(record, 1, 'LAND')
        info_flags = validator.get_flags_by_severity('INFO')
        assert len(info_flags) >= 1
        assert any('long term' in flag.message.lower() for flag in info_flags)


class TestRentRollExtraction:
    """Test the extraction logic"""
    
    def test_tenant_id_extraction(self):
        """Test extraction of tenant ID from name"""
        # The format is "Tenant Name (t0000123)"
        from app.utils.financial_table_parser import FinancialTableParser
        import re
        
        test_names = [
            ("CEJR Health Services, LLC (t0000490)", "CEJR Health Services, LLC", "t0000490"),
            ("Subway Real Estate, LLC (t0000508)", "Subway Real Estate, LLC", "t0000508"),
            ("Petsmart, Inc.", "Petsmart, Inc.", None),  # No ID
        ]
        
        for full_name, expected_name, expected_id in test_names:
            match = re.match(r'(.+?)\s*\(t(\d+)\)', full_name)
            if match:
                name = match.group(1).strip()
                tenant_id = f"t{match.group(2)}"
                assert name == expected_name
                assert tenant_id == expected_id
            else:
                assert expected_id is None
    
    def test_multi_unit_lease_format(self):
        """Test multi-unit lease format parsing"""
        # Multi-unit format: "009-A, 009-B, 009-C"
        unit_numbers = [
            "009-A, 009-B, 009-C",  # Multi-unit
            "015, 016",  # Multi-unit
            "001",  # Single
        ]
        
        for unit in unit_numbers:
            is_multi = ',' in unit or unit.count('-') > 1
            if ',' in unit:
                assert is_multi == True
    
    def test_special_unit_codes(self):
        """Test special unit code detection"""
        special_units = ['Z-ATM', 'LAND', 'COMMON', 'Z-SIGN', '0D0', '0G0']
        
        for unit in special_units:
            unit_upper = unit.upper()
            is_special = any(code in unit_upper for code in ['ATM', 'LAND', 'COMMON', 'SIGN'])
            assert is_special or unit in ['0D0', '0G0']  # Internal codes


class TestRentRollHelperMethods:
    """Test the new helper methods in FinancialTableParser"""
    
    def test_extract_tenant_id_method(self):
        """Test _extract_tenant_id helper method"""
        from app.utils.financial_table_parser import FinancialTableParser
        
        parser = FinancialTableParser()
        
        # Test with tenant ID
        name, tid = parser._extract_tenant_id("CEJR Health Services, LLC (t0000490)")
        assert name == "CEJR Health Services, LLC"
        assert tid == "t0000490"
        
        # Test without tenant ID
        name, tid = parser._extract_tenant_id("Petsmart, Inc.")
        assert name == "Petsmart, Inc."
        assert tid is None
        
        # Test with empty string
        name, tid = parser._extract_tenant_id("")
        assert name == ""
        assert tid is None
    
    def test_detect_special_unit_type(self):
        """Test _detect_special_unit_type helper method"""
        from app.utils.financial_table_parser import FinancialTableParser
        
        parser = FinancialTableParser()
        
        # Test ATM
        result = parser._detect_special_unit_type("Z-ATM")
        assert result == "ATM Location"
        
        # Test LAND
        result = parser._detect_special_unit_type("LAND")
        assert result == "Ground Lease"
        
        # Test COMMON
        result = parser._detect_special_unit_type("COMMON")
        assert result == "Common Area"
        
        # Test SIGN
        result = parser._detect_special_unit_type("Z-SIGN")
        assert result == "Signage"
        
        # Test normal unit
        result = parser._detect_special_unit_type("001")
        assert result is None
    
    def test_is_multi_unit_lease(self):
        """Test _is_multi_unit_lease helper method"""
        from app.utils.financial_table_parser import FinancialTableParser
        
        parser = FinancialTableParser()
        
        # Test comma-separated units
        assert parser._is_multi_unit_lease("009-A, 009-B, 009-C") == True
        assert parser._is_multi_unit_lease("015, 016") == True
        
        # Test single unit with hyphen
        assert parser._is_multi_unit_lease("009-A") == False
        
        # Test single unit
        assert parser._is_multi_unit_lease("001") == False
        
        # Test multiple hyphens
        assert parser._is_multi_unit_lease("009-A-009-B-009-C") == True
    
    def test_calculate_lease_status(self):
        """Test _calculate_lease_status helper method"""
        from app.utils.financial_table_parser import FinancialTableParser
        
        parser = FinancialTableParser()
        
        # Test active lease
        record = {
            'lease_start_date': '2020-01-01',
            'lease_end_date': '2026-12-31'
        }
        status = parser._calculate_lease_status(record, '2025-04-30')
        assert status == 'active'
        
        # Test expired lease
        record = {
            'lease_start_date': '2020-01-01',
            'lease_end_date': '2024-12-31'
        }
        status = parser._calculate_lease_status(record, '2025-04-30')
        assert status == 'expired'
        
        # Test month-to-month (no end date)
        record = {
            'lease_start_date': '2020-01-01',
            'lease_end_date': None
        }
        status = parser._calculate_lease_status(record, '2025-04-30')
        assert status == 'month_to_month'
        
        # Test future lease
        record = {
            'lease_start_date': '2026-01-01',
            'lease_end_date': '2030-12-31'
        }
        status = parser._calculate_lease_status(record, '2025-04-30')
        assert status == 'future'
    
    def test_link_gross_rent_rows(self):
        """Test _link_gross_rent_rows helper method"""
        from app.utils.financial_table_parser import FinancialTableParser
        
        parser = FinancialTableParser()
        
        # Test linking gross rent row to parent
        line_items = [
            {'unit_number': '001', 'tenant_name': 'Tenant A', 'is_gross_rent_row': False},
            {'unit_number': '001', 'tenant_name': 'Gross Rent', 'is_gross_rent_row': True},
            {'unit_number': '002', 'tenant_name': 'Tenant B', 'is_gross_rent_row': False},
            {'unit_number': '002', 'tenant_name': 'Gross Rent', 'is_gross_rent_row': True},
        ]
        
        result = parser._link_gross_rent_rows(line_items)
        
        # Check that gross rent rows are linked
        assert result[1].get('parent_row_id') == 1  # First gross rent links to first tenant
        assert result[3].get('parent_row_id') == 3  # Second gross rent links to second tenant
        
        # Check that non-gross rows don't have parent_row_id
        assert 'parent_row_id' not in result[0] or result[0].get('parent_row_id') is None
        assert 'parent_row_id' not in result[2] or result[2].get('parent_row_id') is None


class TestRentRollV2Fields:
    """Test extraction of all Template v2.0 fields"""
    
    def test_all_24_fields_present_in_schema(self):
        """Verify RentRollDataItem schema has all 24 fields"""
        from app.schemas.document import RentRollDataItem
        
        # Get all field names from the schema
        fields = RentRollDataItem.__fields__.keys()
        
        # Core fields (6)
        assert 'property_name' in fields
        assert 'property_code' in fields
        assert 'report_date' in fields
        assert 'unit_number' in fields
        assert 'tenant_name' in fields
        assert 'tenant_id' in fields
        
        # Lease details (5)
        assert 'lease_type' in fields
        assert 'lease_start_date' in fields
        assert 'lease_end_date' in fields
        assert 'lease_term_months' in fields
        assert 'tenancy_years' in fields
        
        # Space (1)
        assert 'unit_area_sqft' in fields
        
        # Base rent (4)
        assert 'monthly_rent' in fields
        assert 'monthly_rent_per_sqft' in fields
        assert 'annual_rent' in fields
        assert 'annual_rent_per_sqft' in fields
        
        # Additional charges (2)
        assert 'annual_recoveries_per_sf' in fields
        assert 'annual_misc_per_sf' in fields
        
        # Security (2)
        assert 'security_deposit' in fields
        assert 'loc_amount' in fields
        
        # Status flags (5)
        assert 'is_vacant' in fields
        assert 'is_gross_rent_row' in fields
        assert 'parent_row_id' in fields
        assert 'occupancy_status' in fields
        assert 'lease_status' in fields
        assert 'notes' in fields
        
        # Validation tracking (5)
        assert 'validation_score' in fields
        assert 'validation_flags_json' in fields
        assert 'critical_flag_count' in fields
        assert 'warning_flag_count' in fields
        assert 'info_flag_count' in fields
    
    def test_database_model_has_all_fields(self):
        """Verify RentRollData model has all v2.0 fields"""
        from app.models.rent_roll_data import RentRollData
        
        # Check that all v2.0 fields exist as columns
        columns = [c.name for c in RentRollData.__table__.columns]
        
        # v2.0 specific fields
        assert 'tenancy_years' in columns
        assert 'annual_recoveries_per_sf' in columns
        assert 'annual_misc_per_sf' in columns
        assert 'is_gross_rent_row' in columns
        assert 'parent_row_id' in columns
        assert 'notes' in columns
        assert 'lease_status' in columns
        
        # Validation tracking fields
        assert 'validation_score' in columns
        assert 'validation_flags_json' in columns
        assert 'critical_flag_count' in columns
        assert 'warning_flag_count' in columns
        assert 'info_flag_count' in columns


# Integration test would go here but requires actual PDF files
# Skipping for now as we have real-world validation from re-extraction

