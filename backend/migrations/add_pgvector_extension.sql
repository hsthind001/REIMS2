-- Add pgvector extension for fast vector similarity search
-- This provides 10-100x faster similarity search compared to Python calculation

-- Install pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Add vector column to document_chunks (if not exists)
-- Note: This assumes embeddings are 1536 dimensions (OpenAI text-embedding-3-large)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'document_chunks' 
        AND column_name = 'embedding_vector'
    ) THEN
        ALTER TABLE document_chunks 
        ADD COLUMN embedding_vector vector(1536);
    END IF;
END $$;

-- Migrate existing embeddings to vector column
-- This may take time for large datasets
UPDATE document_chunks
SET embedding_vector = embedding::vector
WHERE embedding IS NOT NULL 
  AND embedding_vector IS NULL;

-- Create index for fast similarity search
-- Using ivfflat index (Inverted File Index)
-- Lists parameter: adjust based on dataset size (rule of thumb: rows / 1000)
CREATE INDEX IF NOT EXISTS document_chunks_embedding_vector_idx 
ON document_chunks 
USING ivfflat (embedding_vector vector_cosine_ops)
WITH (lists = 100);

-- Note: For very large datasets (>1M vectors), consider HNSW index instead:
-- CREATE INDEX document_chunks_embedding_vector_hnsw_idx 
-- ON document_chunks 
-- USING hnsw (embedding_vector vector_cosine_ops)
-- WITH (m = 16, ef_construction = 64);

-- Analyze table to update statistics
ANALYZE document_chunks;

