-- Complete REIMS Schema from GitHub Models

-- Users
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    is_superuser BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Financial Periods
CREATE TABLE IF NOT EXISTS financial_periods (
    id SERIAL PRIMARY KEY,
    property_id INTEGER REFERENCES properties(id) ON DELETE CASCADE,
    period_year INTEGER NOT NULL,
    period_month INTEGER NOT NULL,
    period_start_date DATE,
    period_end_date DATE,
    is_closed BOOLEAN DEFAULT FALSE,
    UNIQUE(property_id, period_year, period_month)
);

-- Document Uploads
CREATE TABLE IF NOT EXISTS document_uploads (
    id SERIAL PRIMARY KEY,
    property_id INTEGER NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    period_id INTEGER NOT NULL REFERENCES financial_periods(id) ON DELETE CASCADE,
    document_type VARCHAR(50) NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_path VARCHAR(500),
    file_hash VARCHAR(64),
    file_size_bytes BIGINT,
    upload_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    uploaded_by INTEGER,
    extraction_status VARCHAR(50),
    extraction_started_at TIMESTAMP WITH TIME ZONE,
    extraction_completed_at TIMESTAMP WITH TIME ZONE,
    version INTEGER,
    is_active BOOLEAN
);

CREATE INDEX ON document_uploads(property_id);
CREATE INDEX ON document_uploads(extraction_status);

-- Chart of Accounts
CREATE TABLE IF NOT EXISTS chart_of_accounts (
    id SERIAL PRIMARY KEY,
    account_code VARCHAR(50) UNIQUE NOT NULL,
    account_name VARCHAR(255) NOT NULL,
    account_type VARCHAR(50) NOT NULL,
    category VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE
);

-- Extraction Logs
CREATE TABLE IF NOT EXISTS extraction_logs (
    id SERIAL PRIMARY KEY,
    filename VARCHAR NOT NULL,
    document_type VARCHAR,
    total_pages INTEGER,
    confidence_score DOUBLE PRECISION,
    extraction_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Balance Sheet Data (Template v1.0)
CREATE TABLE IF NOT EXISTS balance_sheet_data (
    id SERIAL PRIMARY KEY,
    property_id INTEGER NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    period_id INTEGER NOT NULL REFERENCES financial_periods(id) ON DELETE CASCADE,
    upload_id INTEGER,
    account_code VARCHAR(50) NOT NULL,
    account_name VARCHAR(255) NOT NULL,
    amount DECIMAL(15,2) NOT NULL,
    report_title VARCHAR(100),
    period_ending VARCHAR(50),
    accounting_basis VARCHAR(20),
    page_number INTEGER,
    is_subtotal BOOLEAN DEFAULT FALSE,
    is_total BOOLEAN DEFAULT FALSE,
    account_level INTEGER,
    account_category VARCHAR(100),
    account_subcategory VARCHAR(100),
    extraction_confidence DECIMAL(5,2),
    match_confidence DECIMAL(5,2),
    match_strategy VARCHAR(50),
    needs_review BOOLEAN DEFAULT FALSE,
    reviewed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX ON balance_sheet_data(property_id, period_id);
CREATE INDEX ON balance_sheet_data(account_code);

-- Income Statement Data (Template v1.0)
CREATE TABLE IF NOT EXISTS income_statement_data (
    id SERIAL PRIMARY KEY,
    property_id INTEGER NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    period_id INTEGER NOT NULL REFERENCES financial_periods(id) ON DELETE CASCADE,
    upload_id INTEGER,
    account_code VARCHAR(50) NOT NULL,
    account_name VARCHAR(255) NOT NULL,
    period_amount DECIMAL(15,2) NOT NULL,
    ytd_amount DECIMAL(15,2),
    period_type VARCHAR(20),
    period_start_date VARCHAR(50),
    period_end_date VARCHAR(50),
    accounting_basis VARCHAR(20),
    page_number INTEGER,
    is_subtotal BOOLEAN DEFAULT FALSE,
    is_total BOOLEAN DEFAULT FALSE,
    line_category VARCHAR(100),
    line_subcategory VARCHAR(100),
    line_number INTEGER,
    account_level INTEGER,
    extraction_confidence DECIMAL(5,2),
    match_confidence DECIMAL(5,2),
    needs_review BOOLEAN DEFAULT FALSE,
    reviewed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX ON income_statement_data(property_id, period_id);

-- Cash Flow Data (Template v1.0)
CREATE TABLE IF NOT EXISTS cash_flow_data (
    id SERIAL PRIMARY KEY,
    property_id INTEGER NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    period_id INTEGER NOT NULL REFERENCES financial_periods(id) ON DELETE CASCADE,
    upload_id INTEGER,
    account_code VARCHAR(50) NOT NULL,
    account_name VARCHAR(255) NOT NULL,
    period_amount DECIMAL(15,2) NOT NULL,
    ytd_amount DECIMAL(15,2),
    line_section VARCHAR(50),
    line_category VARCHAR(100),
    line_subcategory VARCHAR(100),
    line_number INTEGER,
    is_subtotal BOOLEAN DEFAULT FALSE,
    is_total BOOLEAN DEFAULT FALSE,
    page_number INTEGER,
    extraction_confidence DECIMAL(5,2),
    match_confidence DECIMAL(5,2),
    needs_review BOOLEAN DEFAULT FALSE,
    reviewed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX ON cash_flow_data(property_id, period_id);

-- Rent Roll Data (Template v2.0)
CREATE TABLE IF NOT EXISTS rent_roll_data (
    id SERIAL PRIMARY KEY,
    property_id INTEGER NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    period_id INTEGER NOT NULL REFERENCES financial_periods(id) ON DELETE CASCADE,
    upload_id INTEGER,
    unit_number VARCHAR(50) NOT NULL,
    tenant_name VARCHAR(255) NOT NULL,
    lease_start_date DATE,
    lease_end_date DATE,
    unit_area_sqft DECIMAL(10,2),
    monthly_rent DECIMAL(12,2),
    annual_rent DECIMAL(12,2),
    security_deposit DECIMAL(12,2),
    tenancy_years DECIMAL(5,2),
    annual_recoveries_per_sf DECIMAL(10,4),
    is_gross_rent_row BOOLEAN DEFAULT FALSE,
    notes TEXT,
    occupancy_status VARCHAR(50) DEFAULT 'occupied',
    extraction_confidence DECIMAL(5,2),
    validation_score DECIMAL(5,2),
    validation_flags_json TEXT,
    critical_flag_count INTEGER DEFAULT 0,
    warning_flag_count INTEGER DEFAULT 0,
    needs_review BOOLEAN DEFAULT FALSE,
    reviewed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX ON rent_roll_data(property_id, period_id);
CREATE INDEX ON rent_roll_data(lease_end_date);

-- Seed properties
INSERT INTO properties (property_code, property_name, property_type, city, state, total_area_sqft) VALUES
('ESP001', 'Eastern Shore Plaza', 'retail', 'Phoenix', 'AZ', 125000.50),
('HMND001', 'Hammond Aire Shopping Center', 'retail', 'Hammond', 'IN', 98500.00),
('TCSH001', 'The Crossings of Spring Hill', 'retail', 'Town Center', 'FL', 110250.00),
('WEND001', 'Wendover Commons', 'retail', 'Greensboro', 'NC', 87600.00),
('TEST001', 'Test Property', 'multifamily', 'Test City', 'TS', NULL)
ON CONFLICT (property_code) DO NOTHING;

