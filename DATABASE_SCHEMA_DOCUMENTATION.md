# REIMS2 Database Schema Documentation

## Overview

This document provides a comprehensive overview of all database tables, their structure, relationships, and usage in the REIMS2 (Real Estate Investment Management System) implementation.

**Database:** PostgreSQL  
**Total Tables:** 52  
**ORM:** SQLAlchemy  
**Migrations:** Alembic

---

## Table of Contents

1. [Core Tables](#1-core-tables)
2. [Financial Data Tables](#2-financial-data-tables)
3. [Document Management Tables](#3-document-management-tables)
4. [Extraction & Quality Tables](#4-extraction--quality-tables)
5. [Risk Management Tables](#5-risk-management-tables)
6. [AI & Intelligence Tables](#6-ai--intelligence-tables)
7. [Reconciliation Tables](#7-reconciliation-tables)
8. [User & Access Control Tables](#8-user--access-control-tables)
9. [System Configuration Tables](#9-system-configuration-tables)
10. [API Management Tables](#10-api-management-tables)

---

## 1. Core Tables

### 1.1 `properties`

**Purpose:** Master property information for all real estate assets.

**Columns:**
- `id` (Integer, PK): Primary key
- `property_code` (String(50), Unique, Indexed): Unique property identifier (e.g., "HMND001")
- `property_name` (String(255)): Full property name
- `property_type` (String(50)): Type (Retail, Office, Mixed-Use)
- `address`, `city`, `state`, `zip_code`, `country`: Location information
- `total_area_sqft` (DECIMAL(12,2)): Total leasable area
- `acquisition_date` (Date): Property acquisition date
- `ownership_structure` (String(100)): Legal structure
- `status` (String(50), Indexed): active, sold, under_contract
- `notes` (Text): Additional notes
- `created_at`, `updated_at` (DateTime): Timestamps
- `created_by` (Integer, FK → users.id): Creator user ID

**Relationships:**
- Has many: `financial_periods`, `document_uploads`, `balance_sheet_data`, `income_statement_data`, `cash_flow_data`, `rent_roll_data`, `financial_metrics`
- Has many: `committee_alerts`, `workflow_locks`
- Has many: `property_research`, `tenant_recommendations`, `tenant_performance_history`

**Indexes:**
- `property_code` (unique)
- `status`

---

### 1.2 `users`

**Purpose:** System user accounts and authentication.

**Columns:**
- `id` (Integer, PK): Primary key
- `email` (String, Unique, Indexed): User email address
- `username` (String, Unique, Indexed): Username
- `hashed_password` (String): Encrypted password
- `is_active` (Boolean): Account active status
- `is_superuser` (Boolean): Superuser flag
- `created_at`, `updated_at` (DateTime): Timestamps

**Relationships:**
- Has many: `nlq_queries`, `audit_trail` entries
- Referenced by: `properties.created_by`, `financial_periods.closed_by`, etc.

---

### 1.3 `financial_periods`

**Purpose:** Monthly reporting periods for properties.

**Columns:**
- `id` (Integer, PK): Primary key
- `property_id` (Integer, FK → properties.id, Indexed): Property reference
- `period_year` (Integer, Indexed): Year (e.g., 2024)
- `period_month` (Integer): Month (1-12)
- `period_start_date` (Date): Period start date
- `period_end_date` (Date): Period end date
- `fiscal_year` (Integer): Fiscal year
- `fiscal_quarter` (Integer): Quarter (1-4)
- `is_closed` (Boolean): Period locked for editing
- `closed_date` (DateTime): When period was closed
- `closed_by` (Integer, FK → users.id): User who closed period
- `created_at` (DateTime): Creation timestamp

**Unique Constraint:**
- `(property_id, period_year, period_month)` - One period per property per month

**Relationships:**
- Belongs to: `property`
- Has many: `document_uploads`, `balance_sheet_data`, `income_statement_data`, `cash_flow_data`, `rent_roll_data`, `financial_metrics`

---

### 1.4 `chart_of_accounts`

**Purpose:** Master chart of accounts template for all financial line items.

**Columns:**
- `id` (Integer, PK): Primary key
- `account_code` (String(50), Unique, Indexed): Account code (e.g., "0122-0000")
- `account_name` (String(255)): Account name (e.g., "Cash - Operating")
- `account_type` (String(50), Indexed): asset, liability, equity, income, expense
- `category` (String(100), Indexed): current_asset, long_term_liability, etc.
- `subcategory` (String(100)): cash, accounts_receivable, utilities, etc.
- `parent_account_code` (String(50)): Parent account for hierarchy
- `document_types` (ARRAY(Text)): ["balance_sheet", "cash_flow"]
- `is_calculated` (Boolean): Is this a total/subtotal?
- `calculation_formula` (Text): Formula for calculated accounts
- `display_order` (Integer): Order in reports
- `is_active` (Boolean): Active status
- `created_at`, `updated_at` (DateTime): Timestamps

**Relationships:**
- Has many: `balance_sheet_data`, `income_statement_data`, `cash_flow_data` (via account_id)

---

### 1.5 `lenders`

**Purpose:** Lender reference data for long-term debt tracking.

**Columns:**
- `id` (Integer, PK): Primary key
- `lender_name` (String(255), Unique, Indexed): Full lender name
- `lender_short_name` (String(100)): Short name (e.g., "CIBC", "Wells Fargo")
- `lender_type` (String(50)): mortgage, mezzanine, shareholder_loan
- `account_code` (String(50), Indexed): Associated chart of accounts code
- `lender_category` (String(50)): institutional, family_trust, shareholder
- `is_active` (Boolean, Indexed): Active status
- `notes` (Text): Additional notes
- `created_at`, `updated_at` (DateTime): Timestamps

---

## 2. Financial Data Tables

### 2.1 `income_statement_data`

**Purpose:** Monthly income statement (P&L) line items - Template v1.0 compliant.

**Columns:**
- `id` (Integer, PK): Primary key
- `header_id` (Integer, FK → income_statement_headers.id): Header reference
- `property_id` (Integer, FK → properties.id, Indexed): Property reference
- `period_id` (Integer, FK → financial_periods.id, Indexed): Period reference
- `upload_id` (Integer, FK → document_uploads.id): Upload reference
- `account_id` (Integer, FK → chart_of_accounts.id): Account reference (nullable)
- `account_code` (String(50), Indexed): Account code
- `account_name` (String(255)): Account name
- `period_amount` (DECIMAL(15,2)): Period to Date amount
- `ytd_amount` (DECIMAL(15,2)): Year to Date amount
- `period_percentage` (DECIMAL(5,2)): % of revenue
- `ytd_percentage` (DECIMAL(5,2)): YTD % of revenue
- `is_subtotal` (Boolean, Indexed): Is subtotal line
- `is_total` (Boolean, Indexed): Is total line
- `line_category` (String(100)): INCOME, OPERATING_EXPENSE, etc.
- `line_subcategory` (String(100)): Utility, Contracted, R&M, etc.
- `line_number` (Integer): Order in statement
- `account_level` (Integer): Hierarchy depth (1-4)
- `is_income` (Boolean): TRUE for income, FALSE for expense
- `is_below_the_line` (Boolean): TRUE for depreciation, amortization, mortgage interest
- `is_calculated` (Boolean): Is calculated/total line
- `extraction_confidence` (DECIMAL(5,2)): 0-100 from PDF extraction
- `match_confidence` (DECIMAL(5,2)): 0-100 from account matching
- `extraction_method` (String(50)): table, text, template
- `needs_review` (Boolean, Indexed): Review flag
- `reviewed` (Boolean): Review status
- `reviewed_by` (Integer, FK → users.id): Reviewer
- `reviewed_at` (DateTime): Review timestamp
- `review_notes` (Text): Review notes
- `extraction_x0`, `extraction_y0`, `extraction_x1`, `extraction_y1` (DECIMAL(10,2)): PDF coordinates
- `created_at`, `updated_at` (DateTime): Timestamps

**Indexes:**
- `ix_is_property_period` (property_id, period_id)
- `ix_is_property_period_account` (property_id, period_id, account_code)
- `ix_is_review_queue` (needs_review, property_id)

**Relationships:**
- Belongs to: `property`, `period`, `upload`, `header`, `account`

---

### 2.2 `income_statement_headers`

**Purpose:** Income statement header metadata with comprehensive summary metrics.

**Columns:**
- `id` (Integer, PK): Primary key
- `property_id` (Integer, FK → properties.id, Indexed): Property reference
- `period_id` (Integer, FK → financial_periods.id, Indexed): Period reference
- `upload_id` (Integer, FK → document_uploads.id): Upload reference
- `property_name`, `property_code` (String): Property identification
- `report_period_start`, `report_period_end` (Date): Period dates
- `period_type` (String(20)): Monthly, Annual, Quarterly
- `accounting_basis` (String(50)): Accrual, Cash
- `report_generation_date` (Date): Report generation date
- **Income Totals:**
  - `total_income` (DECIMAL(15,2))
  - `base_rentals` (DECIMAL(15,2))
  - `total_recovery_income` (DECIMAL(15,2))
  - `total_other_income` (DECIMAL(15,2))
- **Expense Totals:**
  - `total_operating_expenses` (DECIMAL(15,2))
  - `total_property_expenses` (DECIMAL(15,2))
  - `total_utility_expenses` (DECIMAL(15,2))
  - `total_contracted_expenses` (DECIMAL(15,2))
  - `total_rm_expenses` (DECIMAL(15,2))
  - `total_admin_expenses` (DECIMAL(15,2))
  - `total_additional_operating_expenses` (DECIMAL(15,2))
  - `total_management_fees` (DECIMAL(15,2))
  - `total_leasing_costs` (DECIMAL(15,2))
  - `total_ll_expenses` (DECIMAL(15,2))
  - `total_expenses` (DECIMAL(15,2))
- **Performance Metrics:**
  - `net_operating_income` (DECIMAL(15,2)): NOI
  - `noi_percentage` (DECIMAL(5,2)): NOI / Total Income * 100
  - `mortgage_interest` (DECIMAL(15,2))
  - `depreciation` (DECIMAL(15,2))
  - `amortization` (DECIMAL(15,2))
  - `total_other_income_expense` (DECIMAL(15,2))
  - `net_income` (DECIMAL(15,2))
  - `net_income_percentage` (DECIMAL(5,2))
- `extraction_confidence` (DECIMAL(5,2)): Overall confidence
- `validation_passed` (Boolean): All validations passed
- `needs_review`, `reviewed` (Boolean): Review workflow
- `reviewed_by` (Integer, FK → users.id)
- `reviewed_at` (DateTime)
- `created_at`, `updated_at` (DateTime): Timestamps

**Relationships:**
- Belongs to: `property`, `period`, `upload`
- Has many: `line_items` (IncomeStatementData)

---

### 2.3 `balance_sheet_data`

**Purpose:** Monthly balance sheet line items - Template v1.0 compliant.

**Columns:**
- `id` (Integer, PK): Primary key
- `property_id` (Integer, FK → properties.id, Indexed): Property reference
- `period_id` (Integer, FK → financial_periods.id, Indexed): Period reference
- `upload_id` (Integer, FK → document_uploads.id): Upload reference
- `account_id` (Integer, FK → chart_of_accounts.id): Account reference (nullable)
- `account_code` (String(50), Indexed): Account code
- `account_name` (String(255)): Account name
- `amount` (DECIMAL(15,2)): Current balance
- `is_debit` (Boolean): TRUE for debit accounts (assets, expenses)
- `is_contra_account` (Boolean): Accumulated depreciation, distributions
- `expected_sign` (String(10)): positive, negative, either
- `is_subtotal` (Boolean, Indexed): Is subtotal line
- `is_total` (Boolean, Indexed): Is total line
- `account_level` (Integer): Hierarchy depth (1-4)
- `account_category` (String(100)): ASSETS, LIABILITIES, CAPITAL
- `account_subcategory` (String(100)): Current Assets, Long Term Liabilities
- `is_calculated` (Boolean): Is calculated/total line
- `parent_account_code` (String(50)): Parent in hierarchy
- `extraction_confidence` (DECIMAL(5,2)): 0-100 from PDF extraction
- `match_confidence` (DECIMAL(5,2)): 0-100 from account matching
- `extraction_method` (String(50)): table, text, template
- `needs_review` (Boolean, Indexed): Review flag
- `reviewed` (Boolean): Review status
- `reviewed_by` (Integer, FK → users.id)
- `reviewed_at` (DateTime)
- `review_notes` (Text)
- `extraction_x0`, `extraction_y0`, `extraction_x1`, `extraction_y1` (DECIMAL(10,2)): PDF coordinates
- `line_number` (Integer): Row position in table
- `report_title` (String(100)): Document title
- `period_ending` (String(50)): Period ending date string
- `accounting_basis` (String(20)): Accrual or Cash
- `report_date` (DateTime): Report generation date
- `page_number` (Integer): Page number
- `created_at`, `updated_at` (DateTime): Timestamps

**Indexes:**
- `ix_bs_property_period` (property_id, period_id)
- `ix_bs_property_period_account` (property_id, period_id, account_code)
- `ix_bs_review_queue` (needs_review, property_id)

**Relationships:**
- Belongs to: `property`, `period`, `upload`, `account`

---

### 2.4 `cash_flow_data`

**Purpose:** Cash flow statement line items with multi-column support.

**Columns:**
- `id` (Integer, PK): Primary key
- `header_id` (Integer, FK → cash_flow_headers.id): Header reference
- `property_id` (Integer, FK → properties.id, Indexed): Property reference
- `period_id` (Integer, FK → financial_periods.id, Indexed): Period reference
- `upload_id` (Integer, FK → document_uploads.id): Upload reference
- `account_id` (Integer, FK → chart_of_accounts.id): Account reference (nullable)
- `account_code` (String(50)): Account code
- `account_name` (String(255)): Account name
- `period_amount` (DECIMAL(15,2)): Period to Date amount
- `ytd_amount` (DECIMAL(15,2)): Year to Date amount
- `period_percentage` (DECIMAL(5,2)): % of total income
- `ytd_percentage` (DECIMAL(5,2)): YTD % of total income
- `line_section` (String(50), Indexed): INCOME, OPERATING_EXPENSE, ADDITIONAL_EXPENSE, PERFORMANCE_METRICS
- `line_category` (String(100), Indexed): Base Rental Income, Property Expenses, etc.
- `line_subcategory` (String(100)): Tax Recovery, Electricity, Gas, etc.
- `line_number` (Integer): Sequential line number
- `is_subtotal` (Boolean): Is subtotal line
- `is_total` (Boolean): Is total line
- `parent_line_id` (Integer, FK → cash_flow_data.id): Link to parent subtotal/total
- `cash_flow_category` (String(50), Indexed): operating, investing, financing (legacy)
- `is_inflow` (Boolean): TRUE for cash in, FALSE for cash out
- `is_calculated` (Boolean): TRUE for NOI, Net Income (derived values)
- `parent_account_code` (String(50)): Legacy field
- `extraction_confidence` (DECIMAL(5,2)): Extraction confidence
- `needs_review`, `reviewed` (Boolean): Review workflow
- `reviewed_by` (Integer, FK → users.id)
- `reviewed_at` (DateTime)
- `review_notes` (Text)
- `page_number` (Integer): Page number in source PDF
- `extraction_x0`, `extraction_y0`, `extraction_x1`, `extraction_y1` (DECIMAL(10,2)): PDF coordinates
- `created_at`, `updated_at` (DateTime): Timestamps

**Unique Constraint:**
- `(property_id, period_id, account_code, line_number)` - One entry per account per line

**Relationships:**
- Belongs to: `property`, `period`, `upload`, `header`, `account`
- Self-referencing: `parent_line` → `child_lines`

---

### 2.5 `cash_flow_headers`

**Purpose:** Cash flow statement header metadata with summary totals.

**Columns:**
- `id` (Integer, PK): Primary key
- `property_id` (Integer, FK → properties.id, Indexed): Property reference
- `period_id` (Integer, FK → financial_periods.id, Indexed): Period reference
- `upload_id` (Integer, FK → document_uploads.id): Upload reference
- `property_name`, `property_code` (String): Property identification
- `report_period_start`, `report_period_end` (Date): Period dates
- `accounting_basis` (String(50)): Accrual, Cash
- `report_generation_date` (Date): Report generation date
- **Income Totals:** `total_income`, `base_rentals`, `total_recovery_income`, `total_other_income`
- **Expense Totals:** `total_operating_expenses`, `total_property_expenses`, `total_utility_expenses`, `total_contracted_expenses`, `total_rm_expenses`, `total_admin_expenses`, `total_additional_operating_expenses`, `total_management_fees`, `total_ll_expenses`, `total_expenses`
- **Performance Metrics:** `net_operating_income`, `noi_percentage`, `mortgage_interest`, `depreciation`, `amortization`, `total_other_income_expense`, `net_income`, `net_income_percentage`
- **Cash Flow:** `total_adjustments`, `cash_flow`, `cash_flow_percentage`, `beginning_cash_balance`, `ending_cash_balance`, `cash_difference`
- `extraction_confidence` (DECIMAL(5,2)): Overall confidence
- `validation_passed` (Boolean): All validations passed
- `needs_review`, `reviewed` (Boolean): Review workflow
- `reviewed_by` (Integer, FK → users.id)
- `reviewed_at` (DateTime)
- `created_at`, `updated_at` (DateTime): Timestamps

**Relationships:**
- Belongs to: `property`, `period`, `upload`
- Has many: `line_items` (CashFlowData), `adjustments` (CashFlowAdjustment), `cash_accounts` (CashAccountReconciliation)

---

### 2.6 `cash_flow_adjustments`

**Purpose:** Adjustments to cash flow statements.

**Columns:**
- `id` (Integer, PK): Primary key
- `header_id` (Integer, FK → cash_flow_headers.id): Header reference
- `property_id` (Integer, FK → properties.id): Property reference
- `period_id` (Integer, FK → financial_periods.id): Period reference
- `upload_id` (Integer, FK → document_uploads.id): Upload reference
- `adjustment_type` (String(50)): Type of adjustment
- `adjustment_amount` (DECIMAL(15,2)): Adjustment amount
- `description` (Text): Adjustment description
- `created_at`, `updated_at` (DateTime): Timestamps

**Relationships:**
- Belongs to: `property`, `period`, `upload`, `header`

---

### 2.7 `rent_roll_data`

**Purpose:** Tenant lease information from rent roll documents.

**Columns:**
- `id` (Integer, PK): Primary key
- `property_id` (Integer, FK → properties.id, Indexed): Property reference
- `period_id` (Integer, FK → financial_periods.id, Indexed): Period reference
- `upload_id` (Integer, FK → document_uploads.id): Upload reference
- `unit_number` (String(50)): Unit identifier (e.g., "B-101")
- `tenant_name` (String(255), Indexed): Tenant name
- `tenant_code` (String(50)): Internal tenant ID
- `lease_type` (String(50)): Retail NNN, Office Gross
- `lease_start_date` (Date): Lease start date
- `lease_end_date` (Date, Indexed): Lease end date
- `lease_term_months` (Integer): Lease term in months
- `remaining_lease_years` (DECIMAL(5,2)): Remaining lease years
- `unit_area_sqft` (DECIMAL(10,2)): Unit area in square feet
- `monthly_rent` (DECIMAL(12,2)): Monthly rent
- `monthly_rent_per_sqft` (DECIMAL(10,4)): Monthly rent per sqft
- `annual_rent` (DECIMAL(12,2)): Annual rent
- `annual_rent_per_sqft` (DECIMAL(10,4)): Annual rent per sqft
- `gross_rent` (DECIMAL(12,2)): Including CAM, tax, insurance
- `security_deposit` (DECIMAL(12,2)): Security deposit
- `loc_amount` (DECIMAL(12,2)): Letter of Credit amount
- `annual_cam_reimbursement` (DECIMAL(12,2)): CAM reimbursement
- `annual_tax_reimbursement` (DECIMAL(12,2)): Tax reimbursement
- `annual_insurance_reimbursement` (DECIMAL(12,2)): Insurance reimbursement
- **Template v2.0 fields:**
  - `tenancy_years` (DECIMAL(5,2)): Years from lease start to report date
  - `annual_recoveries_per_sf` (DECIMAL(10,4)): CAM + tax + insurance per SF
  - `annual_misc_per_sf` (DECIMAL(10,4)): Misc charges per SF
  - `is_gross_rent_row` (Boolean, Indexed): Flag for gross rent calculation rows
  - `parent_row_id` (Integer, FK → rent_roll_data.id): Link gross rent to parent
  - `notes` (Text): Extraction notes, validation flags
- `occupancy_status` (String(50), Indexed): occupied, vacant, notice
- `lease_status` (String(50)): active, expired, terminated
- `extraction_confidence` (DECIMAL(5,2)): Extraction confidence
- `page_number` (Integer): Page number
- `extraction_x0`, `extraction_y0`, `extraction_x1`, `extraction_y1` (DECIMAL(10,2)): PDF coordinates
- `needs_review`, `reviewed` (Boolean): Review workflow
- `reviewed_by` (Integer, FK → users.id)
- `reviewed_at` (DateTime)
- `review_notes` (Text)
- `created_at`, `updated_at` (DateTime): Timestamps

**Unique Constraint:**
- `(property_id, period_id, unit_number)` - One entry per unit per period

**Indexes:**
- `ix_rr_property_period` (property_id, period_id)
- `ix_rr_lease_expiry` (property_id, lease_end_date)
- `ix_rr_occupancy` (property_id, occupancy_status)

**Relationships:**
- Belongs to: `property`, `period`, `upload`
- Self-referencing: `parent` → `gross_rent_rows`

---

### 2.8 `financial_metrics`

**Purpose:** Pre-calculated KPIs for fast reporting - Template v1.0 Enhanced.

**Columns:**
- `id` (Integer, PK): Primary key
- `property_id` (Integer, FK → properties.id, Indexed): Property reference
- `period_id` (Integer, FK → financial_periods.id, Indexed): Period reference
- **Balance Sheet Totals:**
  - `total_assets`, `total_current_assets`, `total_property_equipment`, `total_other_assets`
  - `total_liabilities`, `total_current_liabilities`, `total_long_term_liabilities`
  - `total_equity`
- **Liquidity Metrics:**
  - `current_ratio`, `quick_ratio`, `cash_ratio`, `working_capital`
- **Leverage Metrics:**
  - `debt_to_assets_ratio`, `debt_to_equity_ratio`, `equity_ratio`, `ltv_ratio`
- **Property Metrics:**
  - `gross_property_value`, `accumulated_depreciation`, `net_property_value`, `depreciation_rate`
  - `land_value`, `building_value_net`, `improvements_value_net`
- **Cash Position:**
  - `operating_cash`, `restricted_cash`, `total_cash_position`
- **Receivables:**
  - `tenant_receivables`, `intercompany_receivables`, `other_receivables`, `total_receivables`, `ar_percentage_of_assets`
- **Debt Analysis:**
  - `short_term_debt`, `institutional_debt`, `mezzanine_debt`, `shareholder_loans`, `long_term_debt`, `total_debt`
- **Equity Analysis:**
  - `partners_contribution`, `beginning_equity`, `partners_draw`, `distributions`, `current_period_earnings`, `ending_equity`, `equity_change`
- **Income Statement Metrics:**
  - `total_revenue`, `total_expenses`, `net_operating_income`, `net_income`
  - `operating_margin`, `profit_margin`
- **Cash Flow Metrics:**
  - `operating_cash_flow`, `investing_cash_flow`, `financing_cash_flow`, `net_cash_flow`
  - `beginning_cash_balance`, `ending_cash_balance`
- **Rent Roll Metrics:**
  - `total_units`, `occupied_units`, `vacant_units`, `occupancy_rate`
  - `total_leasable_sqft`, `occupied_sqft`, `total_monthly_rent`, `total_annual_rent`, `avg_rent_per_sqft`
- **Property Performance:**
  - `noi_per_sqft`, `revenue_per_sqft`, `expense_ratio`
- `calculated_at`, `created_at`, `updated_at` (DateTime): Timestamps

**Unique Constraint:**
- `(property_id, period_id)` - One metrics record per property per period

**Relationships:**
- Belongs to: `property`, `period`

---

### 2.9 `budgets`

**Purpose:** Budgeted financial data at the account level.

**Columns:**
- `id` (Integer, PK): Primary key
- `property_id` (Integer, FK → properties.id, Indexed): Property reference
- `period_id` (Integer, FK → financial_periods.id, Indexed): Period reference
- `account_code` (String(50)): Account code
- `account_name` (String(255)): Account name
- `budget_amount` (DECIMAL(15,2)): Budgeted amount
- `budget_type` (String(50)): annual, quarterly, monthly
- `created_at`, `updated_at` (DateTime): Timestamps

**Relationships:**
- Belongs to: `property`, `period`

---

### 2.10 `forecasts`

**Purpose:** Forecasted financial data (rolling forecasts, reforecasts).

**Columns:**
- `id` (Integer, PK): Primary key
- `property_id` (Integer, FK → properties.id, Indexed): Property reference
- `period_id` (Integer, FK → financial_periods.id, Indexed): Period reference
- `account_code` (String(50)): Account code
- `account_name` (String(255)): Account name
- `forecast_amount` (DECIMAL(15,2)): Forecasted amount
- `forecast_type` (String(50)): rolling, reforecast
- `created_at`, `updated_at` (DateTime): Timestamps

**Relationships:**
- Belongs to: `property`, `period`

---

## 3. Document Management Tables

### 3.1 `document_uploads`

**Purpose:** Tracks all uploaded financial PDFs.

**Columns:**
- `id` (Integer, PK): Primary key
- `property_id` (Integer, FK → properties.id, Indexed): Property reference
- `period_id` (Integer, FK → financial_periods.id, Indexed): Period reference
- `document_type` (String(50), Indexed): balance_sheet, income_statement, cash_flow, rent_roll
- `file_name` (String(255)): Original filename
- `file_path` (String(500)): S3/MinIO path
- `file_hash` (String(64)): MD5/SHA256 for deduplication
- `file_size_bytes` (BigInteger): File size
- `upload_date` (DateTime): Upload timestamp
- `uploaded_by` (Integer, FK → users.id): Uploader user ID
- `extraction_status` (String(50), Indexed): pending, processing, completed, failed
- `extraction_started_at` (DateTime): Extraction start time
- `extraction_completed_at` (DateTime): Extraction completion time
- `extraction_id` (Integer, FK → extraction_logs.id): Link to extraction quality tracking
- `version` (Integer): Document version
- `is_active` (Boolean): Latest version flag
- `notes` (Text): Additional notes

**Unique Constraint:**
- `(property_id, period_id, document_type, version)` - One document per property/period/type/version

**Relationships:**
- Belongs to: `property`, `period`, `extraction_log`
- Has many: `balance_sheet_data`, `income_statement_data`, `cash_flow_data`, `rent_roll_data`, `validation_results`, `chunks`, `concordance_records`

---

### 3.2 `document_chunks`

**Purpose:** Document chunks with embeddings for RAG (Retrieval Augmented Generation).

**Columns:**
- `id` (Integer, PK): Primary key
- `document_id` (Integer, FK → document_uploads.id, Indexed): Document reference
- `extraction_log_id` (Integer, FK → extraction_logs.id): Extraction log reference
- `chunk_index` (Integer): Order of chunk in document
- `chunk_text` (Text): The actual text content
- `chunk_size` (Integer): Character count
- `embedding` (JSON): Vector embedding as JSON array
- `embedding_model` (String(100)): Model name (e.g., 'text-embedding-3-small')
- `embedding_dimension` (Integer): Dimension of embedding vector
- `chunk_metadata` (JSON): Additional metadata (page numbers, section, etc.)
- `property_id` (Integer, FK → properties.id, Indexed): Property reference
- `period_id` (Integer, FK → financial_periods.id, Indexed): Period reference
- `document_type` (String(50), Indexed): Document type for faster filtering
- `created_at`, `updated_at` (DateTime): Timestamps

**Indexes:**
- `idx_chunk_document_index` (document_id, chunk_index)
- `idx_chunk_property_period` (property_id, period_id)

**Relationships:**
- Belongs to: `document`, `extraction_log`, `property`, `period`

---

### 3.3 `document_summaries`

**Purpose:** AI-generated summaries of property documents.

**Columns:**
- `id` (Integer, PK): Primary key
- `property_id` (Integer, FK → properties.id, Indexed): Property reference
- `document_id` (Integer, FK → document_uploads.id): Document reference
- `summary_type` (String(50)): lease, operating_manual, etc.
- `summary_text` (Text): Generated summary
- `confidence_score` (DECIMAL(5,2)): Confidence in summary
- `generated_at` (DateTime): Generation timestamp
- `created_at`, `updated_at` (DateTime): Timestamps

**Relationships:**
- Belongs to: `property`, `document`

---

## 4. Extraction & Quality Tables

### 4.1 `extraction_logs`

**Purpose:** Track PDF extraction quality and results.

**Columns:**
- `id` (Integer, PK): Primary key
- `filename` (String): Original filename
- `file_size` (Integer): File size in bytes
- `file_hash` (String, Indexed): MD5 or SHA256 hash
- `document_type` (String): digital, scanned, mixed, etc.
- `total_pages` (Integer): Number of pages
- `strategy_used` (String): auto, fast, accurate, multi_engine
- `engines_used` (JSON): List of engines used
- `primary_engine` (String): Primary extraction engine
- `confidence_score` (Float): 0-100 overall confidence
- `quality_level` (String): excellent, good, acceptable, poor, failed
- `passed_checks` (Integer): Number of passed quality checks
- `total_checks` (Integer): Total quality checks
- `processing_time_seconds` (Float): Processing time
- `extraction_timestamp` (DateTime): Extraction timestamp
- `validation_issues` (JSON): List of issues found
- `validation_warnings` (JSON): List of warnings
- `recommendations` (JSON): List of recommendations
- `extracted_text` (Text): Full extracted text (optional)
- `text_preview` (String(500)): First 500 characters
- `total_words` (Integer): Word count
- `total_chars` (Integer): Character count
- `tables_found` (Integer): Number of tables found
- `images_found` (Integer): Number of images found
- `needs_review` (Boolean): Review flag
- `reviewed` (Boolean): Review status
- `reviewed_by` (String): Reviewer
- `reviewed_at` (DateTime): Review timestamp
- `review_notes` (Text): Review notes
- `custom_metadata` (JSON): Additional custom metadata
- `created_at`, `updated_at` (DateTime): Timestamps

**Relationships:**
- Has many: `document_uploads` (via extraction_id), `document_chunks`

---

### 4.2 `extraction_field_metadata`

**Purpose:** Stores field-level confidence scores and metadata for all extracted data.

**Columns:**
- `id` (Integer, PK): Primary key
- `document_id` (Integer, FK → document_uploads.id, Indexed): Document reference
- `field_name` (String(255), Indexed): Field identifier
- `field_type` (String(50)): Field type
- `extracted_value` (Text): Extracted value
- `confidence_score` (DECIMAL(5,2)): Field-level confidence (0-100)
- `extraction_method` (String(50)): Method used
- `needs_review` (Boolean, Indexed): Review flag
- `reviewed` (Boolean): Review status
- `created_at`, `updated_at` (DateTime): Timestamps

**Relationships:**
- Belongs to: `document`

---

### 4.3 `extraction_corrections`

**Purpose:** Extraction corrections for active learning.

**Columns:**
- `id` (Integer, PK): Primary key
- `field_metadata_id` (Integer, FK → extraction_field_metadata.id): Field metadata reference
- `original_value` (Text): Original extracted value
- `corrected_value` (Text): Corrected value
- `correction_type` (String(50)): Type of correction
- `corrected_by` (Integer, FK → users.id): User who made correction
- `corrected_at` (DateTime): Correction timestamp
- `confidence_before` (DECIMAL(5,4)): Confidence before correction
- `pattern_detected` (JSONB): Detected pattern
- `applied_to_future` (Boolean): Applied to future extractions
- `created_at` (DateTime): Creation timestamp

**Indexes:**
- `idx_corrections_type` (correction_type)
- `idx_corrections_pattern` (pattern_detected) - GIN index
- `idx_corrections_user` (corrected_by)

**Relationships:**
- Belongs to: `field_metadata`, `user` (corrected_by)

---

### 4.4 `extraction_templates`

**Purpose:** Extraction templates for document parsing.

**Columns:**
- `id` (Integer, PK): Primary key
- `template_name` (String(255)): Template name
- `document_type` (String(50)): Document type
- `template_config` (JSON): Template configuration
- `is_active` (Boolean): Active status
- `created_at`, `updated_at` (DateTime): Timestamps

---

### 4.5 `validation_rules`

**Purpose:** Validation rules for data quality checks.

**Columns:**
- `id` (Integer, PK): Primary key
- `rule_name` (String(255)): Rule name
- `rule_type` (String(50)): Rule type
- `rule_config` (JSON): Rule configuration
- `is_active` (Boolean): Active status
- `created_at`, `updated_at` (DateTime): Timestamps

---

### 4.6 `validation_results`

**Purpose:** Results of validation rule execution.

**Columns:**
- `id` (Integer, PK): Primary key
- `upload_id` (Integer, FK → document_uploads.id): Upload reference
- `rule_id` (Integer, FK → validation_rules.id): Rule reference
- `validation_status` (String(50)): passed, failed, warning
- `validation_message` (Text): Validation message
- `validated_at` (DateTime): Validation timestamp
- `created_at` (DateTime): Creation timestamp

**Relationships:**
- Belongs to: `upload`, `rule`

---

## 5. Risk Management Tables

### 5.1 `anomaly_detections`

**Purpose:** Statistical anomaly detection results.

**Columns:**
- `id` (Integer, PK): Primary key
- `document_id` (Integer, FK → document_uploads.id, Indexed): Document reference
- `field_name` (String(255), Indexed): Field/account code
- `field_value` (DECIMAL(15,2)): Current value
- `expected_value` (DECIMAL(15,2)): Expected value
- `anomaly_type` (String(50)): percentage_change, absolute_value_change, z_score, etc.
- `severity` (String(50)): critical, high, medium, low
- `confidence` (DECIMAL(5,4)): Confidence score (0-1)
- `z_score` (DECIMAL(10,4)): Z-score if applicable
- `percentage_change` (DECIMAL(10,4)): Percentage change
- `detected_at` (DateTime, Indexed): Detection timestamp
- `resolved` (Boolean): Resolution status
- `resolved_at` (DateTime): Resolution timestamp
- `created_at` (DateTime): Creation timestamp

**Indexes:**
- `document_id`, `field_name`, `detected_at`

**Relationships:**
- Belongs to: `document` (via document_id)

---

### 5.2 `anomaly_thresholds`

**Purpose:** Store absolute value thresholds for anomaly detection per account code.

**Columns:**
- `id` (Integer, PK): Primary key
- `account_code` (String(50), Unique, Indexed): Account code (e.g., "5400-0002")
- `account_name` (String(255)): Account name (e.g., "Salaries Expense")
- `threshold_value` (DECIMAL(15,2)): Absolute value threshold
- `is_active` (Boolean, Indexed): Active status
- `created_at`, `updated_at` (DateTime): Timestamps

**Relationships:**
- Optional relationship to `chart_of_accounts` via account_code

---

### 5.3 `system_config`

**Purpose:** Store system-wide configuration values.

**Columns:**
- `id` (Integer, PK): Primary key
- `config_key` (String(100), Unique, Indexed): Config key (e.g., "anomaly_threshold_default")
- `config_value` (String(500)): Config value (stored as string)
- `description` (String(500)): Config description
- `created_at`, `updated_at` (DateTime): Timestamps

---

### 5.4 `committee_alerts`

**Purpose:** Tracks risk alerts that require committee review/approval.

**Columns:**
- `id` (Integer, PK): Primary key
- `property_id` (Integer, FK → properties.id, Indexed): Property reference
- `financial_period_id` (Integer, FK → financial_periods.id): Period reference
- `alert_type` (Enum, Indexed): DSCR_BREACH, OCCUPANCY_WARNING, OCCUPANCY_CRITICAL, LTV_BREACH, COVENANT_VIOLATION, VARIANCE_BREACH, ANOMALY_DETECTED, FINANCIAL_THRESHOLD
- `severity` (Enum): INFO, WARNING, CRITICAL, URGENT
- `status` (Enum, Indexed): ACTIVE, ACKNOWLEDGED, RESOLVED, DISMISSED
- `title` (String(200)): Alert title
- `description` (Text): Alert description
- `threshold_value` (Numeric(15,4)): Threshold value
- `actual_value` (Numeric(15,4)): Actual value
- `threshold_unit` (String(50)): ratio, percentage, dollars
- `assigned_committee` (Enum): FINANCE_SUBCOMMITTEE, OCCUPANCY_SUBCOMMITTEE, RISK_COMMITTEE, EXECUTIVE_COMMITTEE
- `requires_approval` (Boolean): Requires approval flag
- `triggered_at` (DateTime, Indexed): Trigger timestamp
- `acknowledged_at` (DateTime): Acknowledgment timestamp
- `resolved_at` (DateTime): Resolution timestamp
- `dismissed_at` (DateTime): Dismissal timestamp
- `acknowledged_by` (Integer, FK → users.id): Acknowledger
- `resolved_by` (Integer, FK → users.id): Resolver
- `dismissed_by` (Integer, FK → users.id): Dismisser
- `resolution_notes` (Text): Resolution notes
- `dismissal_reason` (Text): Dismissal reason
- `alert_metadata` (JSONB): Alert-specific data
- `related_metric` (String(100)): Related metric (e.g., "DSCR", "Occupancy Rate")
- `br_id` (String(20)): Business Requirement ID
- `created_at`, `updated_at` (DateTime): Timestamps

**Relationships:**
- Belongs to: `property`, `financial_period`
- Has many: `workflow_locks`

---

### 5.5 `workflow_locks`

**Purpose:** Enforces workflow pauses and governance controls.

**Columns:**
- `id` (Integer, PK): Primary key
- `property_id` (Integer, FK → properties.id, Indexed): Property reference
- `alert_id` (Integer, FK → committee_alerts.id, Indexed): Alert reference
- `lock_reason` (Enum): DSCR_BREACH, OCCUPANCY_THRESHOLD, COVENANT_VIOLATION, COMMITTEE_REVIEW, FINANCIAL_ANOMALY, VARIANCE_BREACH, MANUAL_HOLD, DATA_QUALITY_ISSUE
- `lock_scope` (Enum): PROPERTY_ALL, FINANCIAL_UPDATES, REPORTING_ONLY, TRANSACTION_APPROVAL, DATA_ENTRY
- `status` (Enum, Indexed): ACTIVE, PENDING_APPROVAL, APPROVED, REJECTED, RELEASED
- `title` (String(200)): Lock title
- `description` (Text): Lock description
- `requires_committee_approval` (Boolean): Requires approval flag
- `approval_committee` (String(100)): Which committee must approve
- `locked_at` (DateTime, Indexed): Lock timestamp
- `unlocked_at` (DateTime): Unlock timestamp
- `approved_at` (DateTime): Approval timestamp
- `rejected_at` (DateTime): Rejection timestamp
- `locked_by` (Integer, FK → users.id): User who created lock
- `unlocked_by` (Integer, FK → users.id): User who unlocked
- `approved_by` (Integer, FK → users.id): User who approved
- `rejected_by` (Integer, FK → users.id): User who rejected
- `resolution_notes` (Text): Resolution notes
- `rejection_reason` (Text): Rejection reason
- `auto_release_conditions` (JSONB): Conditions for auto-unlock
- `auto_released` (Boolean): Auto-released flag
- `lock_metadata` (JSONB): Additional metadata
- `br_id` (String(20)): Business Requirement ID
- `created_at`, `updated_at` (DateTime): Timestamps

**Relationships:**
- Belongs to: `property`, `alert`
- Has many user relationships: `locked_by_user`, `unlocked_by_user`, `approved_by_user`, `rejected_by_user`

---

### 5.6 `alerts`

**Purpose:** General alert system (legacy/complementary to committee_alerts).

**Columns:**
- `id` (Integer, PK): Primary key
- `property_id` (Integer, FK → properties.id): Property reference
- `alert_type` (String(50)): Alert type
- `severity` (String(50)): Alert severity
- `message` (Text): Alert message
- `created_at` (DateTime): Creation timestamp

---

### 5.7 `alert_rules`

**Purpose:** Alert rule definitions.

**Columns:**
- `id` (Integer, PK): Primary key
- `rule_name` (String(255)): Rule name
- `rule_type` (String(50)): Rule type
- `rule_config` (JSON): Rule configuration
- `is_active` (Boolean): Active status
- `created_at`, `updated_at` (DateTime): Timestamps

---

## 6. AI & Intelligence Tables

### 6.1 `nlq_queries`

**Purpose:** Natural Language Query log and cache.

**Columns:**
- `id` (Integer, PK): Primary key
- `user_id` (Integer, FK → users.id, Indexed): User reference
- `question` (Text): User's natural language question
- `intent` (JSONB): Detected intent and entities
- `answer` (Text): Generated answer
- `data_retrieved` (JSONB): Data retrieved from database
- `citations` (JSONB): Citations/sources for answer
- `confidence_score` (Numeric(5,4)): Confidence in answer (0-1)
- `sql_query` (Text): SQL query executed (for transparency)
- `execution_time_ms` (Integer): Query execution time in milliseconds
- `created_at` (DateTime, Indexed): Creation timestamp

**Indexes:**
- `idx_nlq_user` (user_id)
- `idx_nlq_date` (created_at)

**Relationships:**
- Belongs to: `user`

---

### 6.2 `concordance_tables`

**Purpose:** Field-by-field comparison of extraction results across all models.

**Columns:**
- `id` (Integer, PK): Primary key
- `upload_id` (Integer, FK → document_uploads.id, Indexed): Upload reference
- `property_id` (Integer, FK → properties.id, Indexed): Property reference
- `period_id` (Integer, FK → financial_periods.id, Indexed): Period reference
- `document_type` (String(50), Indexed): balance_sheet, income_statement, etc.
- `field_name` (String(255)): Field identifier (e.g., "account_4010", "total_revenue")
- `field_display_name` (String(255)): Display name (e.g., "Base Rentals", "Total Revenue")
- `account_code` (String(50), Indexed): Account code if applicable
- `model_values` (JSON): Values from each model {"pymupdf": "$215,671.29", "pdfplumber": "$215,671.29", ...}
- `normalized_value` (String(255)): Normalized value for comparison
- `agreement_count` (Integer): Number of models that agree
- `total_models` (Integer): Total models that extracted this field
- `agreement_percentage` (DECIMAL(5,2)): Agreement percentage (0-100)
- `has_consensus` (Boolean): True if agreement >= 75%
- `is_perfect_agreement` (Boolean): True if 100% agreement
- `conflicting_models` (JSON): List of model names that disagree
- `final_value` (String(255)): Final agreed-upon value
- `final_model` (String(50)): Model that provided final value (or "ensemble")
- `created_at`, `updated_at` (DateTime): Timestamps

**Indexes:**
- `ix_concordance_upload_field` (upload_id, field_name)
- `ix_concordance_agreement` (has_consensus, agreement_percentage)

**Relationships:**
- Belongs to: `upload`, `property`, `period`

---

### 6.3 `property_research`

**Purpose:** Comprehensive market intelligence from M1 Retriever Agent.

**Columns:**
- `id` (Integer, PK): Primary key
- `property_id` (Integer, FK → properties.id, Indexed): Property reference
- `research_date` (Date, Indexed): Research date
- `demographics_data` (JSONB): Demographics data from Census Bureau
- `employment_data` (JSONB): Employment data
- `developments_data` (JSONB): Development data
- `market_data` (JSONB): Market data
- `sources` (JSONB): Data sources
- `confidence_score` (Numeric(5,4)): Confidence score
- `created_at`, `updated_at` (DateTime): Timestamps

**Indexes:**
- `idx_research_property` (property_id)
- `idx_research_date` (research_date)
- `idx_research_demographics` (demographics_data) - GIN index

**Relationships:**
- Belongs to: `property`

---

### 6.4 `tenant_recommendations`

**Purpose:** AI-powered tenant recommendations for vacant spaces.

**Columns:**
- `id` (Integer, PK): Primary key
- `property_id` (Integer, FK → properties.id, Indexed): Property reference
- `unit_identifier` (String(100)): Unit/space identifier
- `space_sqft` (Integer): Space size in square feet
- `recommendation_date` (Date, Indexed): Recommendation date
- `recommendations` (JSONB): Array of recommendation objects
- `demographics_used` (JSONB): Demographics data used
- `tenant_mix_used` (JSONB): Tenant mix data used
- `created_at` (DateTime): Creation timestamp

**Indexes:**
- `idx_tenant_rec_property` (property_id)
- `idx_tenant_rec_date` (recommendation_date)

**Relationships:**
- Belongs to: `property`

---

### 6.5 `tenant_performance_history`

**Purpose:** Historical tenant data for ML training.

**Columns:**
- `id` (Integer, PK): Primary key
- `property_id` (Integer, FK → properties.id, Indexed): Property reference
- `tenant_name` (String(200)): Tenant name
- `tenant_category` (String(100), Indexed): Category (retail, restaurant, service, etc.)
- `lease_start_date` (Date): Lease start date
- `lease_end_date` (Date): Lease end date
- `monthly_rent` (Numeric(12,2)): Monthly rent
- `space_sqft` (Integer): Space size
- `performance_score` (Numeric(5,2)): Performance score
- `renewals_count` (Integer): Number of renewals
- `still_operating` (Boolean): Still operating flag
- `demographics_at_lease` (JSONB): Demographics at lease time
- `tenant_mix_at_lease` (JSONB): Tenant mix at lease time
- `created_at` (DateTime): Creation timestamp

**Indexes:**
- `idx_tenant_perf_property` (property_id)
- `idx_tenant_perf_category` (tenant_category)

**Relationships:**
- Belongs to: `property`

---

### 6.6 `report_audits`

**Purpose:** M3 Auditor verification results for generated reports.

**Columns:**
- `id` (Integer, PK): Primary key
- `report_id` (Integer): Reference to generated report
- `report_type` (String(100)): Report type
- `audit_date` (DateTime): Audit timestamp
- `issues_found` (JSONB): Issues found
- `factual_accuracy` (Numeric(5,4)): Factual accuracy score
- `citation_coverage` (Numeric(5,4)): Citation coverage score
- `hallucination_score` (Numeric(5,4)): Hallucination score
- `overall_quality` (String(10)): Overall quality rating
- `audited_by` (String(100)): Auditor name (default: 'M3-Auditor')
- `approved` (Boolean): Approval status
- `approved_by` (Integer, FK → users.id): Approver user ID
- `approved_at` (DateTime): Approval timestamp
- `created_at`, `updated_at` (DateTime): Timestamps

**Indexes:**
- `idx_audits_report` (report_id, report_type)
- `idx_audits_quality` (overall_quality)

**Relationships:**
- Belongs to: `user` (approved_by)

---

## 7. Reconciliation Tables

### 7.1 `reconciliation_sessions`

**Purpose:** Cash account reconciliation sessions.

**Columns:**
- `id` (Integer, PK): Primary key
- `property_id` (Integer, FK → properties.id): Property reference
- `period_id` (Integer, FK → financial_periods.id): Period reference
- `session_name` (String(255)): Session name
- `status` (String(50)): Session status
- `created_at`, `updated_at` (DateTime): Timestamps

**Relationships:**
- Belongs to: `property`, `period`
- Has many: `reconciliation_differences`

---

### 7.2 `reconciliation_differences`

**Purpose:** Differences found during reconciliation.

**Columns:**
- `id` (Integer, PK): Primary key
- `session_id` (Integer, FK → reconciliation_sessions.id): Session reference
- `difference_type` (String(50)): Type of difference
- `difference_amount` (DECIMAL(15,2)): Difference amount
- `description` (Text): Difference description
- `created_at` (DateTime): Creation timestamp

**Relationships:**
- Belongs to: `session`
- Has many: `reconciliation_resolutions`

---

### 7.3 `reconciliation_resolutions`

**Purpose:** Resolutions for reconciliation differences.

**Columns:**
- `id` (Integer, PK): Primary key
- `difference_id` (Integer, FK → reconciliation_differences.id): Difference reference
- `resolution_type` (String(50)): Resolution type
- `resolution_amount` (DECIMAL(15,2)): Resolution amount
- `description` (Text): Resolution description
- `resolved_by` (Integer, FK → users.id): Resolver user ID
- `resolved_at` (DateTime): Resolution timestamp
- `created_at` (DateTime): Creation timestamp

**Relationships:**
- Belongs to: `difference`, `user` (resolved_by)

---

### 7.4 `cash_account_reconciliations`

**Purpose:** Cash account reconciliation records.

**Columns:**
- `id` (Integer, PK): Primary key
- `header_id` (Integer, FK → cash_flow_headers.id): Header reference
- `property_id` (Integer, FK → properties.id): Property reference
- `period_id` (Integer, FK → financial_periods.id): Period reference
- `upload_id` (Integer, FK → document_uploads.id): Upload reference
- `account_code` (String(50)): Cash account code
- `account_name` (String(255)): Cash account name
- `beginning_balance` (DECIMAL(15,2)): Beginning balance
- `ending_balance` (DECIMAL(15,2)): Ending balance
- `reconciled` (Boolean): Reconciliation status
- `created_at`, `updated_at` (DateTime): Timestamps

**Relationships:**
- Belongs to: `property`, `period`, `upload`, `header`

---

## 8. User & Access Control Tables

### 8.1 `roles`

**Purpose:** User roles for RBAC.

**Columns:**
- `id` (Integer, PK): Primary key
- `role_name` (String(100), Unique): Role name (e.g., "Supervisor", "Analyst", "Viewer")
- `role_description` (Text): Role description
- `is_active` (Boolean): Active status
- `created_at`, `updated_at` (DateTime): Timestamps

**Relationships:**
- Has many: `user_roles`, `role_permissions`

---

### 8.2 `user_roles`

**Purpose:** User-role assignments.

**Columns:**
- `id` (Integer, PK): Primary key
- `user_id` (Integer, FK → users.id): User reference
- `role_id` (Integer, FK → roles.id): Role reference
- `assigned_at` (DateTime): Assignment timestamp
- `assigned_by` (Integer, FK → users.id): Assigner user ID

**Relationships:**
- Belongs to: `user`, `role`, `user` (assigned_by)

---

### 8.3 `permissions`

**Purpose:** System permissions.

**Columns:**
- `id` (Integer, PK): Primary key
- `permission_name` (String(100), Unique): Permission name
- `permission_description` (Text): Permission description
- `resource` (String(100)): Resource name
- `action` (String(50)): Action (read, write, delete, etc.)
- `created_at`, `updated_at` (DateTime): Timestamps

---

### 8.4 `role_permissions`

**Purpose:** Role-permission assignments.

**Columns:**
- `id` (Integer, PK): Primary key
- `role_id` (Integer, FK → roles.id): Role reference
- `permission_id` (Integer, FK → permissions.id): Permission reference
- `granted_at` (DateTime): Grant timestamp

**Relationships:**
- Belongs to: `role`, `permission`

---

### 8.5 `audit_trail`

**Purpose:** System audit trail for user actions.

**Columns:**
- `id` (Integer, PK): Primary key
- `user_id` (Integer, FK → users.id): User reference
- `action` (String(100)): Action performed
- `resource_type` (String(100)): Resource type
- `resource_id` (Integer): Resource ID
- `details` (JSONB): Action details
- `ip_address` (String(50)): IP address
- `user_agent` (String(255)): User agent
- `created_at` (DateTime, Indexed): Action timestamp

**Indexes:**
- `user_id`, `created_at`

**Relationships:**
- Belongs to: `user`

---

## 9. System Configuration Tables

### 9.1 `notifications`

**Purpose:** System notifications.

**Columns:**
- `id` (Integer, PK): Primary key
- `user_id` (Integer, FK → users.id): User reference
- `notification_type` (String(50)): Notification type
- `title` (String(255)): Notification title
- `message` (Text): Notification message
- `read` (Boolean): Read status
- `read_at` (DateTime): Read timestamp
- `created_at` (DateTime): Creation timestamp

**Relationships:**
- Belongs to: `user`

---

## 10. API Management Tables

### 10.1 `api_keys`

**Purpose:** API key management for external integrations.

**Columns:**
- `id` (Integer, PK): Primary key
- `key_name` (String(255)): Key name/identifier
- `api_key` (String(255), Unique): API key value
- `is_active` (Boolean): Active status
- `created_at`, `updated_at` (DateTime): Timestamps

---

### 10.2 `api_usage_logs`

**Purpose:** API usage tracking and logging.

**Columns:**
- `id` (Integer, PK): Primary key
- `api_key_id` (Integer, FK → api_keys.id): API key reference
- `endpoint` (String(255)): API endpoint
- `method` (String(10)): HTTP method
- `status_code` (Integer): HTTP status code
- `response_time_ms` (Integer): Response time
- `ip_address` (String(50)): Client IP address
- `created_at` (DateTime, Indexed): Request timestamp

**Relationships:**
- Belongs to: `api_key`

---

### 10.3 `webhooks`

**Purpose:** Webhook configurations.

**Columns:**
- `id` (Integer, PK): Primary key
- `webhook_url` (String(500)): Webhook URL
- `event_type` (String(100)): Event type
- `is_active` (Boolean): Active status
- `created_at`, `updated_at` (DateTime): Timestamps

---

### 10.4 `webhook_deliveries`

**Purpose:** Webhook delivery logs.

**Columns:**
- `id` (Integer, PK): Primary key
- `webhook_id` (Integer, FK → webhooks.id): Webhook reference
- `status` (String(50)): Delivery status
- `status_code` (Integer): HTTP status code
- `response_body` (Text): Response body
- `delivered_at` (DateTime): Delivery timestamp
- `created_at` (DateTime): Creation timestamp

**Relationships:**
- Belongs to: `webhook`

---

## Database Views

The system also includes several database views for reporting and analytics:

- **Financial Summary Views**: Aggregated financial data across properties
- **Anomaly Summary Views**: Aggregated anomaly detection results
- **Metrics Views**: Pre-calculated metrics for dashboards

---

## Indexes Summary

### Common Index Patterns

1. **Foreign Key Indexes**: All foreign keys are indexed for join performance
2. **Composite Indexes**: Property + Period combinations for time-series queries
3. **Status Indexes**: Active/inactive flags for filtering
4. **Date Indexes**: Created_at, updated_at for temporal queries
5. **GIN Indexes**: JSONB columns for efficient JSON queries

### Key Composite Indexes

- `(property_id, period_id)` - Most financial data tables
- `(property_id, period_id, account_code)` - Account-level queries
- `(needs_review, property_id)` - Review queue queries
- `(document_id, chunk_index)` - Document chunk ordering
- `(upload_id, field_name)` - Concordance table lookups

---

## Relationships Summary

### Core Hierarchy

```
properties
  ├── financial_periods
  │   ├── document_uploads
  │   │   ├── balance_sheet_data
  │   │   ├── income_statement_data
  │   │   ├── cash_flow_data
  │   │   ├── rent_roll_data
  │   │   ├── document_chunks
  │   │   └── concordance_tables
  │   ├── financial_metrics
  │   ├── budgets
  │   └── forecasts
  ├── committee_alerts
  │   └── workflow_locks
  ├── property_research
  ├── tenant_recommendations
  └── tenant_performance_history
```

### User Hierarchy

```
users
  ├── nlq_queries
  ├── audit_trail
  └── user_roles
      └── roles
          └── role_permissions
              └── permissions
```

---

## Data Types Reference

### Common Data Types

- **Integer**: IDs, counts, months
- **String(n)**: Text fields with length limits
- **Text**: Unlimited text fields
- **DECIMAL(p,s)**: Financial amounts (precision, scale)
  - `DECIMAL(15,2)`: Large amounts (up to 999,999,999,999,999.99)
  - `DECIMAL(12,2)`: Medium amounts
  - `DECIMAL(10,4)`: Ratios, percentages
  - `DECIMAL(5,2)`: Small amounts, percentages
- **Boolean**: True/false flags
- **Date**: Date only (no time)
- **DateTime**: Date and time with timezone
- **JSON/JSONB**: Structured data (JSONB preferred for PostgreSQL)
- **ARRAY(Text)**: Array of text values

---

## Constraints Summary

### Unique Constraints

- `properties.property_code` - Unique property codes
- `users.email`, `users.username` - Unique user identifiers
- `financial_periods(property_id, period_year, period_month)` - One period per property per month
- `document_uploads(property_id, period_id, document_type, version)` - One document per property/period/type/version
- `financial_metrics(property_id, period_id)` - One metrics record per property per period
- `rent_roll_data(property_id, period_id, unit_number)` - One entry per unit per period
- `cash_flow_data(property_id, period_id, account_code, line_number)` - One entry per account per line
- `anomaly_thresholds.account_code` - One threshold per account code
- `system_config.config_key` - One config value per key

### Foreign Key Constraints

All foreign keys use `ON DELETE CASCADE` or `ON DELETE SET NULL` as appropriate:
- **CASCADE**: Child records deleted when parent is deleted (e.g., financial data when property is deleted)
- **SET NULL**: Foreign key set to NULL when parent is deleted (e.g., upload_id when document is deleted)

---

## Migration History

All schema changes are managed through Alembic migrations located in `backend/alembic/versions/`:

- **Initial Schema**: `20251103_1259_61e979087abb_initial_financial_schema_with_13_tables.py`
- **Next Level Features**: `20251114_next_level_features.py` (NLQ, Property Research, Tenant Recommendations)
- **Risk Management**: `20251114_risk_management_tables.py` (Committee Alerts, Workflow Locks)
- **Concordance Tables**: `20251124_add_concordance_tables.py`
- **Anomaly Thresholds**: `20251125_add_anomaly_thresholds_table.py`
- And many more incremental migrations...

---

## Notes

1. **Template Compliance**: Financial data tables (Income Statement, Balance Sheet, Cash Flow) follow Template v1.0 specifications with comprehensive field coverage.

2. **Extraction Coordinates**: Most financial data tables include `extraction_x0`, `extraction_y0`, `extraction_x1`, `extraction_y1` for PDF source navigation.

3. **Review Workflow**: Most data tables include `needs_review`, `reviewed`, `reviewed_by`, `reviewed_at`, `review_notes` for quality control.

4. **Confidence Scores**: Extraction confidence scores (0-100) are stored in `extraction_confidence` fields.

5. **JSONB Usage**: PostgreSQL JSONB is used for flexible data storage (intents, metadata, configurations).

6. **Timezone Awareness**: All DateTime columns use timezone-aware timestamps.

7. **Soft Deletes**: Some tables use `is_active` flags instead of hard deletes for data retention.

---

## Database Statistics

- **Total Tables**: 52
- **Total Indexes**: ~150+ (including composite indexes)
- **Total Foreign Keys**: ~80+
- **Total Unique Constraints**: ~15
- **Primary Keys**: 52 (one per table)

---

*Last Updated: November 25, 2025*  
*Database Version: PostgreSQL (version managed via Alembic)*

