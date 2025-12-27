-- Fix ESP001 Property Misattribution - Version 2 (Handle Version Conflicts)
--
-- This script corrects 22 documents that were incorrectly uploaded under TCSH001
-- when they actually belong to ESP001 (Eastern Shore Plaza).
--
-- Handles unique constraint on (property_id, period_id, document_type, version)

BEGIN;

-- Get ESP001 and TCSH001 property IDs
DO $$
DECLARE
    esp_property_id INT;
    tcsh_property_id INT;
    doc RECORD;
    correct_period_id INT;
    next_version INT;
    rows_updated INT := 0;
    existing_doc_id INT;
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
    FOR doc IN
        SELECT
            du.id AS upload_id,
            du.file_name,
            du.file_path,
            du.document_type,
            du.property_id AS wrong_property_id,
            du.period_id AS wrong_period_id,
            fp.period_year,
            fp.period_month,
            du.version,
            du.extraction_status
        FROM document_uploads du
        JOIN properties p_wrong ON du.property_id = p_wrong.id
        JOIN financial_periods fp ON du.period_id = fp.id
        WHERE du.file_name ILIKE '%esp%'
          AND p_wrong.property_code = 'TCSH001'
        ORDER BY du.id
    LOOP
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

        -- Check if ESP001 already has a document for this period/type
        SELECT id INTO existing_doc_id
        FROM document_uploads
        WHERE property_id = esp_property_id
          AND period_id = correct_period_id
          AND document_type = doc.document_type
          AND is_active = true
          AND id != doc.upload_id;

        IF existing_doc_id IS NOT NULL THEN
            -- Conflict: ESP001 already has this document type for this period
            -- Mark the misattributed TCSH001 document as inactive (superseded)
            RAISE NOTICE 'CONFLICT: ESP001 already has % for % Month % (upload_id: %)',
                doc.document_type, doc.period_year, doc.period_month, existing_doc_id;
            RAISE NOTICE '  → Marking misattributed TCSH001 document (upload_id: %) as INACTIVE',
                doc.upload_id;

            UPDATE document_uploads
            SET
                is_active = false,
                notes = COALESCE(notes, '') || E'\n[' || NOW()::DATE || '] Marked inactive - duplicate of ESP001 upload_id ' || existing_doc_id || ' (was misattributed to TCSH001)'
            WHERE id = doc.upload_id;

            rows_updated := rows_updated + 1;
            CONTINUE;
        END IF;

        -- Get next version for ESP001 period/type
        SELECT COALESCE(MAX(version), 0) + 1 INTO next_version
        FROM document_uploads
        WHERE property_id = esp_property_id
          AND period_id = correct_period_id
          AND document_type = doc.document_type;

        -- Update document_uploads record with new version
        UPDATE document_uploads
        SET
            property_id = esp_property_id,
            period_id = correct_period_id,
            version = next_version,
            notes = COALESCE(notes, '') || E'\n[' || NOW()::DATE || '] Property corrected from TCSH001 to ESP001 (automated fix, version changed from ' || doc.version || ' to ' || next_version || ')'
        WHERE id = doc.upload_id;

        rows_updated := rows_updated + 1;

        -- Update related cash_flow_data
        IF doc.document_type = 'cash_flow' THEN
            UPDATE cash_flow_data
            SET
                property_id = esp_property_id,
                period_id = correct_period_id
            WHERE upload_id = doc.upload_id;

            RAISE NOTICE 'Fixed upload_id % (%) - Cash Flow % Month % -> ESP001 period_id % (version: %)',
                doc.upload_id, doc.file_name, doc.period_year, doc.period_month, correct_period_id, next_version;
        END IF;

        -- Update related income_statement_data
        IF doc.document_type = 'income_statement' THEN
            UPDATE income_statement_data
            SET
                property_id = esp_property_id,
                period_id = correct_period_id
            WHERE upload_id = doc.upload_id;

            RAISE NOTICE 'Fixed upload_id % (%) - Income Statement % Month % -> ESP001 period_id % (version: %)',
                doc.upload_id, doc.file_name, doc.period_year, doc.period_month, correct_period_id, next_version;
        END IF;

    END LOOP;

    RAISE NOTICE '';
    RAISE NOTICE '=== Correction Complete ===';
    RAISE NOTICE 'Total documents processed: %', rows_updated;
    RAISE NOTICE '';
END $$;

-- Verification queries
\echo ''
\echo '=== Verification: ESP001 Documents ==='
\echo ''

SELECT
    du.id,
    du.file_name,
    p.property_code,
    fp.period_year,
    fp.period_month,
    du.document_type,
    du.version,
    du.is_active,
    du.extraction_status
FROM document_uploads du
JOIN properties p ON du.property_id = p.id
JOIN financial_periods fp ON du.period_id = fp.id
WHERE du.file_name ILIKE '%esp%'
ORDER BY p.property_code, fp.period_year, fp.period_month, du.document_type;

\echo ''
\echo '=== Summary ==='
\echo ''

SELECT
    'Total ESP documents' as metric,
    COUNT(*)::text as value
FROM document_uploads
WHERE file_name ILIKE '%esp%'
UNION ALL
SELECT
    'Under ESP001',
    COUNT(*)::text
FROM document_uploads du
JOIN properties p ON du.property_id = p.id
WHERE du.file_name ILIKE '%esp%'
  AND p.property_code = 'ESP001'
UNION ALL
SELECT
    'Under TCSH001',
    COUNT(*)::text
FROM document_uploads du
JOIN properties p ON du.property_id = p.id
WHERE du.file_name ILIKE '%esp%'
  AND p.property_code = 'TCSH001'
UNION ALL
SELECT
    'Active ESP001 documents',
    COUNT(*)::text
FROM document_uploads du
JOIN properties p ON du.property_id = p.id
WHERE du.file_name ILIKE '%esp%'
  AND p.property_code = 'ESP001'
  AND du.is_active = true;

-- COMMIT the changes
COMMIT;

\echo ''
\echo '✅ Transaction COMMITTED - All Changes Applied!'
\echo ''
