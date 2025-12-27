-- Fix ESP001 Property Misattribution - EXECUTABLE VERSION
--
-- This script corrects 22 documents that were incorrectly uploaded under TCSH001
-- when they actually belong to ESP001 (Eastern Shore Plaza).
--
-- This version will COMMIT the changes.

BEGIN;

-- Create temp table to store corrections
CREATE TEMP TABLE misattributed_docs AS
SELECT
    du.id AS upload_id,
    du.file_name,
    du.file_path,
    du.document_type,
    du.property_id AS wrong_property_id,
    du.period_id AS wrong_period_id,
    p_wrong.property_code AS wrong_property_code,
    p_correct.id AS correct_property_id,
    p_correct.property_code AS correct_property_code,
    fp.period_year,
    fp.period_month,
    du.extraction_status
FROM document_uploads du
JOIN properties p_wrong ON du.property_id = p_wrong.id
JOIN financial_periods fp ON du.period_id = fp.id
CROSS JOIN properties p_correct
WHERE du.file_name ILIKE '%esp%'
  AND p_wrong.property_code = 'TCSH001'
  AND p_correct.property_code = 'ESP001';

-- Get ESP001 property ID
DO $$
DECLARE
    esp_property_id INT;
    tcsh_property_id INT;
    doc RECORD;
    correct_period_id INT;
    rows_updated INT := 0;
BEGIN
    -- Get property IDs
    SELECT id INTO esp_property_id FROM properties WHERE property_code = 'ESP001';
    SELECT id INTO tcsh_property_id FROM properties WHERE property_code = 'TCSH001';

    IF esp_property_id IS NULL THEN
        RAISE EXCEPTION 'ESP001 property not found!';
    END IF;

    RAISE NOTICE '';
    RAISE NOTICE '=== Starting Corrections ===';
    RAISE NOTICE 'ESP001 property_id: %', esp_property_id;
    RAISE NOTICE 'TCSH001 property_id: %', tcsh_property_id;
    RAISE NOTICE '';

    -- For each misattributed document
    FOR doc IN SELECT * FROM misattributed_docs LOOP
        -- Get or create correct ESP001 period
        SELECT id INTO correct_period_id
        FROM financial_periods
        WHERE property_id = esp_property_id
          AND period_year = doc.period_year
          AND period_month = doc.period_month;

        IF correct_period_id IS NULL THEN
            -- Create missing period for ESP001
            INSERT INTO financial_periods (
                property_id,
                period_year,
                period_month,
                period_start_date,
                period_end_date,
                fiscal_year,
                fiscal_quarter,
                is_closed
            ) VALUES (
                esp_property_id,
                doc.period_year,
                doc.period_month,
                DATE(doc.period_year || '-' || LPAD(doc.period_month::text, 2, '0') || '-01'),
                (DATE(doc.period_year || '-' || LPAD(doc.period_month::text, 2, '0') || '-01') + INTERVAL '1 month - 1 day')::DATE,
                doc.period_year,
                ((doc.period_month - 1) / 3) + 1,
                FALSE
            )
            RETURNING id INTO correct_period_id;

            RAISE NOTICE 'Created new period: ESP001 % Month % (period_id: %)', doc.period_year, doc.period_month, correct_period_id;
        END IF;

        -- Update document_uploads record
        UPDATE document_uploads
        SET
            property_id = esp_property_id,
            period_id = correct_period_id,
            notes = COALESCE(notes, '') || E'\n[' || NOW()::DATE || '] Property corrected from TCSH001 to ESP001 (automated fix for misattribution)'
        WHERE id = doc.upload_id;

        rows_updated := rows_updated + 1;

        -- Update related cash_flow_data
        IF doc.document_type = 'cash_flow' THEN
            UPDATE cash_flow_data
            SET
                property_id = esp_property_id,
                period_id = correct_period_id
            WHERE upload_id = doc.upload_id;

            RAISE NOTICE 'Fixed upload_id % (%) - Cash Flow % Month % -> ESP001 period_id %',
                doc.upload_id, doc.file_name, doc.period_year, doc.period_month, correct_period_id;
        END IF;

        -- Update related income_statement_data
        IF doc.document_type = 'income_statement' THEN
            UPDATE income_statement_data
            SET
                property_id = esp_property_id,
                period_id = correct_period_id
            WHERE upload_id = doc.upload_id;

            RAISE NOTICE 'Fixed upload_id % (%) - Income Statement % Month % -> ESP001 period_id %',
                doc.upload_id, doc.file_name, doc.period_year, doc.period_month, correct_period_id;
        END IF;

        -- Update related financial_metrics if exist
        UPDATE financial_metrics
        SET property_id = esp_property_id
        WHERE property_id = tcsh_property_id
          AND period_id = correct_period_id;

    END LOOP;

    RAISE NOTICE '';
    RAISE NOTICE '=== Correction Complete ===';
    RAISE NOTICE 'Total documents corrected: %', rows_updated;
    RAISE NOTICE '';
END $$;

-- COMMIT the changes
COMMIT;

\echo ''
\echo '✅ Transaction COMMITTED - Changes Applied!'
\echo ''
\echo 'Run verification queries to confirm:'
\echo '  SELECT COUNT(*) FROM document_uploads WHERE file_name ILIKE ''%esp%'' AND property_id = (SELECT id FROM properties WHERE property_code = ''ESP001'');'
\echo ''
