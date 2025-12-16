"""Add pgvector extension and optimize embeddings for RAG

Revision ID: XXXX_add_pgvector
Revises: <previous_revision>
Create Date: 2024-01-XX XX:XX:XX.XXXXXX

This migration adds pgvector support for efficient similarity search.
Optional but highly recommended for production performance.

Requirements:
- PostgreSQL 11+
- pgvector extension installed on database server

To install pgvector on PostgreSQL:
  # Ubuntu/Debian
  sudo apt-get install postgresql-XX-pgvector
  
  # Or compile from source
  git clone https://github.com/pgvector/pgvector.git
  cd pgvector
  make
  sudo make install
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'XXXX_add_pgvector'
down_revision = '<previous_revision>'  # Update with actual previous revision
branch_labels = None
depends_on = None


def upgrade():
    """
    Add pgvector extension and optimize embedding column.
    
    Note: This migration is OPTIONAL. The optimized service works without it,
    but performance will be significantly better with pgvector.
    """
    
    # Step 1: Enable pgvector extension
    # This requires superuser privileges
    try:
        op.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        print("✅ pgvector extension enabled")
    except Exception as e:
        print(f"⚠️  Warning: Could not enable pgvector extension: {e}")
        print("   The optimized service will use NumPy fallback for similarity search.")
        print("   To enable pgvector, run as superuser:")
        print("   CREATE EXTENSION IF NOT EXISTS vector;")
        return  # Skip remaining steps if extension not available
    
    # Step 2: Check if embedding column exists and has data
    connection = op.get_bind()
    result = connection.execute(sa.text("""
        SELECT COUNT(*) 
        FROM information_schema.columns 
        WHERE table_name = 'document_chunks' 
        AND column_name = 'embedding'
    """))
    
    if result.scalar() == 0:
        print("⚠️  Embedding column does not exist. Skipping pgvector migration.")
        return
    
    # Step 3: Check current column type
    result = connection.execute(sa.text("""
        SELECT data_type 
        FROM information_schema.columns 
        WHERE table_name = 'document_chunks' 
        AND column_name = 'embedding'
    """))
    
    current_type = result.scalar()
    
    if current_type == 'jsonb' or current_type == 'json':
        # Step 4: Convert JSON array to vector type
        print("Converting embedding column from JSON to vector(1536)...")
        
        # First, ensure all embeddings are valid arrays of length 1536
        connection.execute(sa.text("""
            UPDATE document_chunks 
            SET embedding = NULL 
            WHERE embedding IS NOT NULL 
            AND (
                jsonb_array_length(embedding::jsonb) != 1536
                OR embedding::jsonb IS NULL
            )
        """))
        
        # Convert to vector type
        # Note: This requires the embedding column to be JSON/JSONB
        connection.execute(sa.text("""
            ALTER TABLE document_chunks 
            ALTER COLUMN embedding TYPE vector(1536) 
            USING embedding::jsonb::text::vector
        """))
        
        print("✅ Embedding column converted to vector(1536)")
    elif current_type == 'USER-DEFINED' and 'vector' in str(current_type):
        print("✅ Embedding column already uses vector type")
    else:
        print(f"⚠️  Unexpected column type: {current_type}. Skipping conversion.")
        return
    
    # Step 5: Create index for fast similarity search
    # Using IVFFlat index for approximate nearest neighbor search
    try:
        connection.execute(sa.text("""
            CREATE INDEX IF NOT EXISTS document_chunks_embedding_idx 
            ON document_chunks 
            USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100)
            WHERE embedding IS NOT NULL
        """))
        print("✅ IVFFlat index created for fast similarity search")
    except Exception as e:
        print(f"⚠️  Could not create IVFFlat index: {e}")
        print("   Creating standard index instead...")
        try:
            connection.execute(sa.text("""
                CREATE INDEX IF NOT EXISTS document_chunks_embedding_btree_idx 
                ON document_chunks (embedding)
                WHERE embedding IS NOT NULL
            """))
            print("✅ Standard index created")
        except Exception as e2:
            print(f"⚠️  Could not create index: {e2}")
    
    # Step 6: Create composite index for common filter combinations
    try:
        connection.execute(sa.text("""
            CREATE INDEX IF NOT EXISTS idx_chunks_property_period_type 
            ON document_chunks(property_id, period_id, document_type) 
            WHERE embedding IS NOT NULL
        """))
        print("✅ Composite index created for filtered searches")
    except Exception as e:
        print(f"⚠️  Could not create composite index: {e}")
    
    # Step 7: Analyze table for query planner
    connection.execute(sa.text("ANALYZE document_chunks"))
    print("✅ Table statistics updated")


def downgrade():
    """
    Revert pgvector changes.
    
    Note: This will convert vector column back to JSON.
    Data loss is possible if embeddings were modified.
    """
    connection = op.get_bind()
    
    # Drop indexes
    try:
        connection.execute(sa.text("DROP INDEX IF EXISTS document_chunks_embedding_idx"))
        connection.execute(sa.text("DROP INDEX IF EXISTS idx_chunks_property_period_type"))
        print("✅ Indexes dropped")
    except Exception as e:
        print(f"⚠️  Error dropping indexes: {e}")
    
    # Convert vector back to JSON
    try:
        connection.execute(sa.text("""
            ALTER TABLE document_chunks 
            ALTER COLUMN embedding TYPE jsonb 
            USING embedding::text::jsonb
        """))
        print("✅ Embedding column converted back to JSONB")
    except Exception as e:
        print(f"⚠️  Error converting column: {e}")
    
    # Note: We don't drop the pgvector extension as it might be used by other tables

