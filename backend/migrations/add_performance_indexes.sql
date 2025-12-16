-- Performance Optimization: Database Indexes for RAG Retrieval
-- Run this migration to improve query performance

-- Indexes for document_chunks table
CREATE INDEX IF NOT EXISTS idx_document_chunks_property_id 
ON document_chunks(property_id);

CREATE INDEX IF NOT EXISTS idx_document_chunks_period_id 
ON document_chunks(period_id);

CREATE INDEX IF NOT EXISTS idx_document_chunks_document_type 
ON document_chunks(document_type);

CREATE INDEX IF NOT EXISTS idx_document_chunks_document_id 
ON document_chunks(document_id);

-- Composite index for common filter combinations
CREATE INDEX IF NOT EXISTS idx_document_chunks_filters 
ON document_chunks(property_id, period_id, document_type) 
WHERE embedding IS NOT NULL;

-- Index for embedding lookup (if not using pgvector)
CREATE INDEX IF NOT EXISTS idx_document_chunks_has_embedding 
ON document_chunks(id) 
WHERE embedding IS NOT NULL;

-- Indexes for related tables (for eager loading)
CREATE INDEX IF NOT EXISTS idx_document_upload_id 
ON document_uploads(id);

CREATE INDEX IF NOT EXISTS idx_property_id 
ON properties(id);

CREATE INDEX IF NOT EXISTS idx_financial_period_id 
ON financial_periods(id);

-- Analyze tables to update statistics
ANALYZE document_chunks;
ANALYZE document_uploads;
ANALYZE properties;
ANALYZE financial_periods;

