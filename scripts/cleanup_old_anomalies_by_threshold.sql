-- Cleanup script to remove old anomalies that don't meet the new absolute value threshold criteria
-- This removes anomalies created with the old percentage-based logic that wouldn't meet the new threshold

-- First, let's see what we're working with
SELECT 
    COUNT(*) as total_old_anomalies,
    COUNT(DISTINCT ad.field_name) as unique_fields
FROM anomaly_detections ad
JOIN document_uploads du ON ad.document_id = du.id
WHERE ad.anomaly_type = 'percentage_change';

-- Show some examples of anomalies that would be deleted
SELECT 
    ad.id,
    ad.field_name,
    ad.field_value::numeric as current_value,
    ad.expected_value::numeric as expected_value,
    ABS(ad.field_value::numeric - ad.expected_value::numeric) as absolute_difference,
    COALESCE(at.threshold_value, (SELECT config_value::numeric FROM system_config WHERE config_key = 'anomaly_threshold_default')) as threshold,
    ad.detected_at
FROM anomaly_detections ad
JOIN document_uploads du ON ad.document_id = du.id
LEFT JOIN anomaly_thresholds at ON at.account_code = ad.field_name AND at.is_active = true
WHERE ad.anomaly_type = 'percentage_change'
  AND ABS(ad.field_value::numeric - ad.expected_value::numeric) <= 
      COALESCE(at.threshold_value, (SELECT config_value::numeric FROM system_config WHERE config_key = 'anomaly_threshold_default'))
ORDER BY ad.detected_at DESC
LIMIT 20;

-- Delete anomalies that don't meet the new threshold
-- WARNING: This will permanently delete anomalies. Run the SELECT above first to verify.
DELETE FROM anomaly_detections
WHERE id IN (
    SELECT ad.id
    FROM anomaly_detections ad
    JOIN document_uploads du ON ad.document_id = du.id
    LEFT JOIN anomaly_thresholds at ON at.account_code = ad.field_name AND at.is_active = true
    WHERE ad.anomaly_type = 'percentage_change'
      AND ad.field_value IS NOT NULL
      AND ad.expected_value IS NOT NULL
      AND ABS(ad.field_value::numeric - ad.expected_value::numeric) <= 
          COALESCE(at.threshold_value, (SELECT config_value::numeric FROM system_config WHERE config_key = 'anomaly_threshold_default'))
);

-- Show count of remaining anomalies
SELECT 
    COUNT(*) as remaining_anomalies,
    COUNT(DISTINCT ad.field_name) as unique_fields
FROM anomaly_detections ad
JOIN document_uploads du ON ad.document_id = du.id
WHERE ad.anomaly_type = 'percentage_change';

