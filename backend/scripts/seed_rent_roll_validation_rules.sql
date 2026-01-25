-- Validation Rules Seed Data for Rent Roll
-- Comprehensive business logic validation rules for rent roll

-- Clear existing rent roll rules (idempotent)
DELETE FROM validation_rules WHERE document_type = 'rent_roll';

-- Rent Roll Validation Rules (9 rules)
INSERT INTO validation_rules (
    rule_name,
    rule_description,
    document_type,
    rule_type,
    rule_formula,
    error_message,
    severity,
    is_active
) VALUES

-- 1. Annual vs Monthly Rent Calculation
(
    'rent_roll_annual_monthly_check',
    'Annual Rent should equal Monthly Rent * 12',
    'rent_roll',
    'balance_check',
    'annual_rent = monthly_rent * 12',
    'Annual rent does not match monthly rent * 12 (tolerance: $100)',
    'warning',
    TRUE
),

-- 2. Occupancy Rate Calculation
(
    'rent_roll_occupancy_rate',
    'Calculate and monitor occupancy rate',
    'rent_roll',
    'ratio_check',
    'occupancy_rate = occupied_units / total_units',
    'Occupancy rate calculated for monitoring',
    'info',
    TRUE
),

-- 3. Vacancy Area Integrity
(
    'rent_roll_vacancy_area_check',
    'Total Area = Occupied Area + Vacant Area',
    'rent_roll',
    'balance_check',
    'total_area = occupied_area + vacant_area',
    'Occupied + Vacant areas do not sum to total area',
    'warning',
    TRUE
),

-- 4. Monthly Rent Per Square Foot
(
    'rent_roll_monthly_rent_psf',
    'Calculate average monthly rent per square foot',
    'rent_roll',
    'calculation_check',
    'monthly_rent_psf = total_monthly_rent / total_area',
    'Monthly rent PSF calculated for monitoring',
    'info',
    TRUE
),

-- 5. Annual Rent Per Square Foot
(
    'rent_roll_annual_rent_psf',
    'Calculate average annual rent per square foot',
    'rent_roll',
    'calculation_check',
    'annual_rent_psf = total_annual_rent / total_area',
    'Annual rent PSF calculated for monitoring',
    'info',
    TRUE
),

-- 6. Tenant-Specific: Petsmart Rent Tracking
(
    'rent_roll_petsmart_rent_check',
    'Verify Petsmart rent matches expected amount (with increase tracking)',
    'rent_roll',
    'specific_tenant_check',
    'petsmart_monthly_rent IN (22179.40, 23016.35)',
    'Petsmart rent does not match expected value (Aug-Sep: $22,179.40, Oct-Dec: $23,016.35)',
    'warning',
    TRUE
),

-- 7. Tenant-Specific: Spirit Halloween Seasonal
(
    'rent_roll_spirit_halloween_seasonal',
    'Verify Unit 600 (Spirit Halloween) has $0 rent when vacant/seasonal',
    'rent_roll',
    'specific_tenant_check',
    'spirit_halloween_rent = 0 OR status = seasonal',
    'Unit 600 (Spirit Halloween) seasonal logic check',
    'info',
    TRUE
),

-- 8. Total Monthly Rent Range Check
(
    'rent_roll_total_monthly_rent',
    'Total monthly rent should be within expected range (> $220,000)',
    'rent_roll',
    'range_check',
    'SUM(monthly_rent) > 220000',
    'Total monthly rent is below expected range',
    'error',
    TRUE
),

-- 9. Vacant Units Tracking
(
    'rent_roll_vacant_units_count',
    'Monitor number of vacant units (expected: 2-3 units)',
    'rent_roll',
    'count_check',
    'COUNT(units WHERE status = Vacant) BETWEEN 2 AND 3',
    'Vacant unit count outside expected range',
    'warning',
    TRUE
);

-- Query to verify seeding
SELECT document_type, COUNT(*) as rule_count, 
       COUNT(CASE WHEN severity = 'error' THEN 1 END) as errors, 
       COUNT(CASE WHEN severity = 'warning' THEN 1 END) as warnings,
       COUNT(CASE WHEN severity = 'info' THEN 1 END) as info
FROM validation_rules
WHERE document_type = 'rent_roll' AND is_active = true
GROUP BY document_type;
