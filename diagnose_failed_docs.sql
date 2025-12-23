-- Diagnostic Queries for Failed Documents

-- 1. Documents with missing periods
SELECT 
    'Missing Period' as issue_type,
    COUNT(*) as count
FROM document_uploads du
LEFT JOIN financial_periods fp ON du.period_id = fp.id
WHERE du.extraction_status = 'completed'
  AND (du.period_id IS NULL OR fp.id IS NULL);

-- 2. Income statements with no data
SELECT 
    'Income Statement - No Data' as issue_type,
    COUNT(*) as count
FROM document_uploads du
LEFT JOIN income_statement_data isd ON (
    isd.property_id = du.property_id 
    AND isd.period_id = du.period_id
)
WHERE du.document_type = 'income_statement'
  AND du.extraction_status = 'completed'
GROUP BY du.id
HAVING COUNT(isd.id) = 0;

-- 3. Balance sheets with no data
SELECT 
    'Balance Sheet - No Data' as issue_type,
    COUNT(*) as count
FROM document_uploads du
LEFT JOIN balance_sheet_data bsd ON (
    bsd.property_id = du.property_id 
    AND bsd.period_id = du.period_id
)
WHERE du.document_type = 'balance_sheet'
  AND du.extraction_status = 'completed'
GROUP BY du.id
HAVING COUNT(bsd.id) = 0;

-- 4. Cash flow with no data
SELECT 
    'Cash Flow - No Data' as issue_type,
    COUNT(*) as count
FROM document_uploads du
LEFT JOIN cash_flow_data cfd ON (
    cfd.property_id = du.property_id 
    AND cfd.period_id = du.period_id
)
WHERE du.document_type = 'cash_flow'
  AND du.extraction_status = 'completed'
GROUP BY du.id
HAVING COUNT(cfd.id) = 0;

-- 5. Unsupported document types
SELECT 
    'Unsupported Type' as issue_type,
    COUNT(*) as count
FROM document_uploads du
WHERE du.extraction_status = 'completed'
  AND du.document_type IN ('rent_roll', 'mortgage_statement');
