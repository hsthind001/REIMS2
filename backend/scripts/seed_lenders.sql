-- Seed Lender Master Data
-- All known lenders from Balance Sheet Template v1.0

-- Create lenders table if not exists
CREATE TABLE IF NOT EXISTS lenders (
    id SERIAL PRIMARY KEY,
    lender_name VARCHAR(255) NOT NULL UNIQUE,
    lender_short_name VARCHAR(100),
    lender_type VARCHAR(50),
    account_code VARCHAR(50),
    lender_category VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_lenders_name ON lenders(lender_name);
CREATE INDEX IF NOT EXISTS idx_lenders_active ON lenders(is_active);
CREATE INDEX IF NOT EXISTS idx_lenders_account_code ON lenders(account_code);

-- ==============================================================================
-- INSTITUTIONAL LENDERS (Primary Mortgages)
-- ==============================================================================

INSERT INTO lenders (lender_name, lender_short_name, lender_type, account_code, lender_category, is_active, notes) VALUES

-- Major Institutional Lenders
('CIBC', 'CIBC', 'mortgage', '2611-0000', 'institutional', TRUE, 'Canadian Imperial Bank of Commerce'),
('KeyBank', 'KeyBank', 'mortgage', '2612-0000', 'institutional', TRUE, 'KeyBank National Association'),
('NorthMarq Capital', 'NorthMarq', 'mortgage', '2612-1000', 'institutional', TRUE, 'Common lender across multiple properties'),
('Wells Fargo', 'Wells Fargo', 'mortgage', '2614-1000', 'institutional', TRUE, 'Wells Fargo Bank - Common lender'),
('MidLand Loan Services (PNC)', 'MidLand/PNC', 'mortgage', '2616-0000', 'institutional', TRUE, 'Midland Loan Services, serviced by PNC'),
('RAIT Financial', 'RAIT', 'mortgage', '2614-0000', 'institutional', TRUE, 'RAIT Financial Trust'),
('Berkadia Commercial Mortgage', 'Berkadia', 'mortgage', '2615-0000', 'institutional', TRUE, 'Berkadia Commercial Mortgage LLC'),
('Wachovia Securities', 'Wachovia', 'mortgage', '2614-2000', 'institutional', TRUE, 'Wachovia Securities (now part of Wells Fargo)'),
('Standard Insurance Company', 'Standard Ins', 'mortgage', '2616-1000', 'institutional', TRUE, 'Standard Insurance Company, an Oregon Corporation'),
('WoodForest National Bank', 'WoodForest', 'mortgage', '2619-0000', 'institutional', TRUE, 'Woodforest National Bank'),
('Origin Bank', 'Origin', 'mortgage', '2621-0000', 'institutional', TRUE, 'Origin Bank'),
('StanCorp Mortgage Investors, LLC', 'StanCorp/NMC', 'mortgage', '2620-0000', 'institutional', TRUE, 'StanCorp Mtg Investors, LLC (NMC)'),
('Business Partners', 'Business Partners', 'mortgage', '2617-0000', 'institutional', TRUE, 'Business Partners Lender')

ON CONFLICT (lender_name) DO UPDATE SET
    lender_short_name = EXCLUDED.lender_short_name,
    lender_type = EXCLUDED.lender_type,
    account_code = EXCLUDED.account_code,
    lender_category = EXCLUDED.lender_category,
    is_active = EXCLUDED.is_active,
    notes = EXCLUDED.notes,
    updated_at = CURRENT_TIMESTAMP;

-- ==============================================================================
-- MEZZANINE LENDERS
-- ==============================================================================

INSERT INTO lenders (lender_name, lender_short_name, lender_type, account_code, lender_category, is_active, notes) VALUES

('Trawler Capital Management (MEZZ)', 'Trawler', 'mezzanine', '2618-0000', 'institutional', TRUE, 'Mezzanine financing provider - subordinate debt'),
('KeyBank - Mezzanine', 'KeyBank Mezz', 'mezzanine', '2613-0000', 'institutional', TRUE, 'KeyBank mezzanine financing'),
('CIBC-MEZZ', 'CIBC Mezz', 'mezzanine', '2611-1000', 'institutional', TRUE, 'CIBC mezzanine financing')

ON CONFLICT (lender_name) DO UPDATE SET
    lender_short_name = EXCLUDED.lender_short_name,
    lender_type = EXCLUDED.lender_type,
    account_code = EXCLUDED.account_code,
    lender_category = EXCLUDED.lender_category,
    is_active = EXCLUDED.is_active,
    notes = EXCLUDED.notes,
    updated_at = CURRENT_TIMESTAMP;

-- ==============================================================================
-- FAMILY TRUST LENDERS
-- ==============================================================================

INSERT INTO lenders (lender_name, lender_short_name, lender_type, account_code, lender_category, is_active, notes) VALUES

('The Azad Family Trust (TAFT)', 'TAFT', 'mortgage', '2613-5000', 'family_trust', TRUE, 'The Azad Family Trust')

ON CONFLICT (lender_name) DO UPDATE SET
    lender_short_name = EXCLUDED.lender_short_name,
    lender_type = EXCLUDED.lender_type,
    account_code = EXCLUDED.account_code,
    lender_category = EXCLUDED.lender_category,
    is_active = EXCLUDED.is_active,
    notes = EXCLUDED.notes,
    updated_at = CURRENT_TIMESTAMP;

-- ==============================================================================
-- SHAREHOLDER LOAN ACCOUNTS
-- ==============================================================================

INSERT INTO lenders (lender_name, lender_short_name, lender_type, account_code, lender_category, is_active, notes) VALUES

('Shareholders Loan Accounts', 'Shareholders', 'shareholder_loan', '2650-0000', 'shareholder', TRUE, 'General shareholder loans header'),
('Loans from Stockholders', 'Stockholders', 'shareholder_loan', '2651-0000', 'shareholder', TRUE, 'Loans from individual stockholders'),

-- Individual Shareholders
('Hardam S Azad', 'H.S. Azad', 'shareholder_loan', '2660-0000', 'shareholder', TRUE, 'Individual shareholder loan'),
('Balwant Singh', 'B. Singh', 'shareholder_loan', '2661-0000', 'shareholder', TRUE, 'Individual shareholder loan'),
('Gurnaib S Sidhu', 'G.S. Sidhu', 'shareholder_loan', '2662-0000', 'shareholder', TRUE, 'Individual shareholder loan'),
('Scott Wallace', 'S. Wallace', 'shareholder_loan', '2663-0000', 'shareholder', TRUE, 'Individual shareholder loan'),
('Kuldip S Bains', 'K.S. Bains', 'shareholder_loan', '2664-0000', 'shareholder', TRUE, 'Individual shareholder loan'),
('Anis Charnia', 'A. Charnia', 'shareholder_loan', '2665-0000', 'shareholder', TRUE, 'Individual shareholder loan'),
('Baldev Singh', 'B. Singh 2', 'shareholder_loan', '2666-0000', 'shareholder', TRUE, 'Individual shareholder loan'),
('Mohinder S Sandhu', 'M.S. Sandhu', 'shareholder_loan', '2667-0000', 'shareholder', TRUE, 'Individual shareholder loan'),
('Harpreet Sandhu', 'H. Sandhu', 'shareholder_loan', '2668-0000', 'shareholder', TRUE, 'Individual shareholder loan'),
('Dr. Jaspaul S Azad', 'Dr. J.S. Azad', 'shareholder_loan', '2669-0000', 'shareholder', TRUE, 'Individual shareholder loan'),
('Dr. I M Azad', 'Dr. I.M. Azad', 'shareholder_loan', '2670-0000', 'shareholder', TRUE, 'Individual shareholder loan'),
('Gagan Bains', 'G. Bains', 'shareholder_loan', '2671-0000', 'shareholder', TRUE, 'Individual shareholder loan')

ON CONFLICT (lender_name) DO UPDATE SET
    lender_short_name = EXCLUDED.lender_short_name,
    lender_type = EXCLUDED.lender_type,
    account_code = EXCLUDED.account_code,
    lender_category = EXCLUDED.lender_category,
    is_active = EXCLUDED.is_active,
    notes = EXCLUDED.notes,
    updated_at = CURRENT_TIMESTAMP;

-- ==============================================================================
-- SUMMARY
-- ==============================================================================

SELECT 
    'Lender Master Data Seeded' as status,
    COUNT(*) as total_lenders,
    COUNT(*) FILTER (WHERE lender_category = 'institutional') as institutional_lenders,
    COUNT(*) FILTER (WHERE lender_category = 'family_trust') as family_trust_lenders,
    COUNT(*) FILTER (WHERE lender_category = 'shareholder') as shareholder_lenders,
    COUNT(*) FILTER (WHERE lender_type = 'mezzanine') as mezzanine_lenders
FROM lenders
WHERE is_active = TRUE;

SELECT 
    lender_category,
    lender_type,
    COUNT(*) as lender_count
FROM lenders
WHERE is_active = TRUE
GROUP BY lender_category, lender_type
ORDER BY lender_category, lender_type;

