-- Script to manually trigger anomaly detection for cash flow documents
-- This will be done via API call, but first let's verify the data exists

-- Check cash flow data for Tax account
SELECT 
    cfd.period_id,
    fp.period_year,
    fp.period_month,
    cfd.account_code,
    cfd.account_name,
    cfd.period_amount,
    du.id as upload_id,
    du.file_name
FROM cash_flow_data cfd
JOIN financial_periods fp ON cfd.period_id = fp.id
JOIN document_uploads du ON cfd.upload_id = du.id
WHERE cfd.account_name = 'Tax' 
  AND cfd.property_id = (SELECT id FROM properties WHERE property_code = 'WEND001')
ORDER BY fp.period_year, fp.period_month;

-- Check if anomalies exist for cash flow documents
SELECT 
    COUNT(*) as total_anomalies,
    COUNT(DISTINCT ad.field_name) as unique_fields
FROM anomaly_detections ad
JOIN document_uploads du ON ad.document_id = du.id
WHERE du.document_type = 'cash_flow'
  AND du.property_id = (SELECT id FROM properties WHERE property_code = 'WEND001');

