-- Script to update existing anomaly detection confidence scores
-- based on extraction confidence from the database.
--
-- This script recalculates confidence for all existing anomalies
-- using the new logic: extraction confidence >= 95% = 100%, otherwise use actual extraction confidence.

-- Update anomalies from income statements
UPDATE anomaly_detections ad
SET confidence = CASE 
    WHEN is_data.avg_confidence >= 95 THEN 1.0
    ELSE is_data.avg_confidence / 100.0
END
FROM (
    SELECT 
        ad_inner.id,
        AVG(isd.extraction_confidence) as avg_confidence
    FROM anomaly_detections ad_inner
    JOIN document_uploads du ON ad_inner.document_id = du.id
    JOIN income_statement_data isd ON isd.upload_id = du.id 
        AND isd.account_code = ad_inner.field_name
        AND isd.extraction_confidence IS NOT NULL
    WHERE du.document_type = 'income_statement'
    GROUP BY ad_inner.id
) is_data
WHERE ad.id = is_data.id;

-- Update anomalies from balance sheets
UPDATE anomaly_detections ad
SET confidence = CASE 
    WHEN bs_data.avg_confidence >= 95 THEN 1.0
    ELSE bs_data.avg_confidence / 100.0
END
FROM (
    SELECT 
        ad_inner.id,
        AVG(bsd.extraction_confidence) as avg_confidence
    FROM anomaly_detections ad_inner
    JOIN document_uploads du ON ad_inner.document_id = du.id
    JOIN balance_sheet_data bsd ON bsd.upload_id = du.id 
        AND bsd.account_code = ad_inner.field_name
        AND bsd.extraction_confidence IS NOT NULL
    WHERE du.document_type = 'balance_sheet'
    GROUP BY ad_inner.id
) bs_data
WHERE ad.id = bs_data.id;

-- Update anomalies from cash flow statements
UPDATE anomaly_detections ad
SET confidence = CASE 
    WHEN cf_data.avg_confidence >= 95 THEN 1.0
    ELSE cf_data.avg_confidence / 100.0
END
FROM (
    SELECT 
        ad_inner.id,
        AVG(cfd.extraction_confidence) as avg_confidence
    FROM anomaly_detections ad_inner
    JOIN document_uploads du ON ad_inner.document_id = du.id
    JOIN cash_flow_data cfd ON cfd.upload_id = du.id 
        AND cfd.account_code = ad_inner.field_name
        AND cfd.extraction_confidence IS NOT NULL
    WHERE du.document_type = 'cash_flow'
    GROUP BY ad_inner.id
) cf_data
WHERE ad.id = cf_data.id;

-- Show summary
SELECT 
    COUNT(*) as total_anomalies,
    COUNT(CASE WHEN confidence = 1.0 THEN 1 END) as confidence_100_percent,
    COUNT(CASE WHEN confidence >= 0.95 THEN 1 END) as confidence_95_plus,
    AVG(confidence) as avg_confidence,
    MIN(confidence) as min_confidence,
    MAX(confidence) as max_confidence
FROM anomaly_detections;

