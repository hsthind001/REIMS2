#!/usr/bin/env python3
"""
Migrate Existing Data to Pinecone

This script syncs all existing document chunks from PostgreSQL to Pinecone.
It maintains dual storage (PostgreSQL + Pinecone) for redundancy.
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import SessionLocal
from app.services.pinecone_sync_service import PineconeSyncService
from app.config.pinecone_config import pinecone_config
from app.core.config import settings


def main():
    """Migrate existing chunks to Pinecone"""
    print("=" * 60)
    print("Pinecone Data Migration")
    print("=" * 60)
    print()
    
    # Check if Pinecone is initialized
    if not pinecone_config.is_initialized():
        print("❌ ERROR: Pinecone not initialized")
        print()
        print("Please run initialization script first:")
        print("  python scripts/init_pinecone.py")
        return 1
    
    # Health check
    health = pinecone_config.health_check()
    if not health['healthy']:
        print(f"❌ ERROR: Pinecone is not healthy: {health.get('error')}")
        return 1
    
    print(f"✓ Pinecone is healthy")
    print(f"✓ Current vectors in index: {health.get('stats', {}).get('total_vector_count', 0)}")
    print()
    
    # Get database session
    db = SessionLocal()
    
    try:
        sync_service = PineconeSyncService(db)
        
        # Check existing chunks
        from app.models.document_chunk import DocumentChunk
        total_chunks = db.query(DocumentChunk).filter(
            DocumentChunk.embedding.isnot(None)
        ).count()
        
        print(f"Found {total_chunks} chunks with embeddings in PostgreSQL")
        print()
        
        if total_chunks == 0:
            print("⚠️  No chunks with embeddings found. Nothing to migrate.")
            print()
            print("To generate embeddings, use the embedding service:")
            print("  from app.services.embedding_service import EmbeddingService")
            print("  embedding_service = EmbeddingService(db)")
            print("  embedding_service.embed_all_chunks()")
            return 0
        
        # Ask for confirmation
        print("This will sync all chunks from PostgreSQL to Pinecone.")
        print("This maintains dual storage - data remains in PostgreSQL.")
        print()
        
        response = input("Continue with migration? (yes/no): ").strip().lower()
        if response not in ['yes', 'y']:
            print("Migration cancelled.")
            return 0
        
        print()
        print("Starting migration...")
        print("-" * 60)
        
        # Sync all chunks
        result = sync_service.sync_all_chunks_to_pinecone(
            batch_size=100,
            force_reembed=False
        )
        
        print("-" * 60)
        print()
        
        if result['success']:
            print("✅ Migration completed successfully!")
            print()
            print(f"Total chunks: {result['total_chunks']}")
            print(f"Synced: {result['synced']}")
            print(f"Failed: {result['failed']}")
            
            if result.get('errors'):
                print()
                print(f"⚠️  {len(result['errors'])} errors occurred:")
                for error in result['errors'][:5]:  # Show first 5 errors
                    print(f"   - {error}")
                if len(result['errors']) > 5:
                    print(f"   ... and {len(result['errors']) - 5} more")
        else:
            print(f"❌ Migration failed: {result.get('error')}")
            return 1
        
        print()
        
        # Verify sync
        print("Verifying sync status...")
        reconciliation = sync_service.reconcile_sync()
        
        print(f"✓ Total chunks in PostgreSQL: {reconciliation['total_chunks']}")
        print(f"✓ Chunks in Pinecone: {reconciliation['in_pinecone']}")
        print(f"✓ Missing in Pinecone: {reconciliation['missing_in_pinecone']}")
        
        if reconciliation['missing_in_pinecone'] > 0:
            print()
            print(f"⚠️  {reconciliation['missing_in_pinecone']} chunks are missing in Pinecone")
            print("   You may want to re-run the migration or sync them individually.")
        
        print()
        print("=" * 60)
        print("✅ Migration complete!")
        print("=" * 60)
        print()
        print("Your RAG system is now using Pinecone for vector search.")
        print("Data is stored in both PostgreSQL (metadata) and Pinecone (vectors).")
        
        return 0
        
    except KeyboardInterrupt:
        print()
        print("\n⚠️  Migration interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Error during migration: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    exit(main())

