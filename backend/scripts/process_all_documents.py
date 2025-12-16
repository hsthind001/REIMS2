#!/usr/bin/env python3
"""
Batch Process All Documents with Enhanced Processor

Processes all existing documents using the enhanced document processor
to create table-aware chunks with parent-child relationships.

Features:
- Progress tracking with tqdm
- Error handling and retry logic
- Resume capability
- Statistics and reporting
"""
import sys
import os
from typing import Optional

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.document_upload import DocumentUpload
from app.models.document_chunk import DocumentChunk
from app.services.document_processor_enhanced import EnhancedDocumentProcessor
from app.db.minio_client import download_file
from app.core.config import settings

# Try to import tqdm for progress bar
try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False
    print("⚠️  tqdm not available. Install with: pip install tqdm")
    print("   Progress will be shown without progress bar.")


def process_all_documents(
    document_type: Optional[str] = None,
    property_id: Optional[int] = None,
    limit: Optional[int] = None,
    skip_processed: bool = True,
    generate_embeddings: bool = True,
    sync_to_pinecone: bool = True
):
    """
    Process all documents with enhanced processor
    
    Args:
        document_type: Filter by document type (optional)
        property_id: Filter by property ID (optional)
        limit: Maximum number of documents to process (optional)
        skip_processed: Skip documents that already have chunks (default: True)
        generate_embeddings: Generate embeddings for chunks (default: True)
        sync_to_pinecone: Sync to Pinecone (default: True)
    """
    db = SessionLocal()
    
    try:
        # Build query
        query = db.query(DocumentUpload).filter(
            DocumentUpload.extraction_status == "completed"
        )
        
        if document_type:
            query = query.filter(DocumentUpload.document_type == document_type)
        
        if property_id:
            query = query.filter(DocumentUpload.property_id == property_id)
        
        # Filter out documents that already have chunks (if skip_processed)
        if skip_processed:
            # Get document IDs that already have chunks
            processed_ids = db.query(DocumentChunk.document_id).distinct().all()
            processed_ids = [id[0] for id in processed_ids]
            if processed_ids:
                query = query.filter(~DocumentUpload.id.in_(processed_ids))
        
        documents = query.order_by(DocumentUpload.upload_date.desc()).all()
        
        if limit:
            documents = documents[:limit]
        
        total_docs = len(documents)
        
        if total_docs == 0:
            print("No documents to process.")
            return
        
        print("=" * 70)
        print("Enhanced Document Processor - Batch Processing")
        print("=" * 70)
        print(f"Total documents to process: {total_docs}")
        print(f"Generate embeddings: {generate_embeddings}")
        print(f"Sync to Pinecone: {sync_to_pinecone}")
        print()
        
        # Initialize processor
        processor = EnhancedDocumentProcessor(db)
        
        # Statistics
        stats = {
            "total": total_docs,
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "total_chunks": 0,
            "text_chunks": 0,
            "table_chunks": 0,
            "header_chunks": 0,
            "errors": []
        }
        
        # Process documents
        if TQDM_AVAILABLE:
            iterator = tqdm(documents, desc="Processing documents", unit="doc")
        else:
            iterator = documents
        
        for doc in iterator:
            try:
                # Download PDF from MinIO
                if not doc.file_path:
                    stats["skipped"] += 1
                    stats["errors"].append({
                        "document_id": doc.id,
                        "error": "No file path"
                    })
                    continue
                
                pdf_data = download_file(
                    object_name=doc.file_path,
                    bucket_name=settings.MINIO_BUCKET_NAME
                )
                
                if not pdf_data:
                    stats["skipped"] += 1
                    stats["errors"].append({
                        "document_id": doc.id,
                        "error": "Failed to download PDF"
                    })
                    continue
                
                # Process document
                result = processor.process_document(
                    document_id=doc.id,
                    pdf_data=pdf_data,
                    generate_embeddings=generate_embeddings,
                    sync_to_pinecone=sync_to_pinecone
                )
                
                if result.get("success"):
                    stats["successful"] += 1
                    doc_stats = result.get("statistics", {})
                    stats["total_chunks"] += doc_stats.get("total_chunks", 0)
                    stats["text_chunks"] += doc_stats.get("text_chunks", 0)
                    stats["table_chunks"] += doc_stats.get("table_chunks", 0)
                    stats["header_chunks"] += doc_stats.get("header_chunks", 0)
                    
                    if TQDM_AVAILABLE:
                        iterator.set_postfix({
                            "success": stats["successful"],
                            "chunks": stats["total_chunks"]
                        })
                else:
                    stats["failed"] += 1
                    stats["errors"].append({
                        "document_id": doc.id,
                        "error": result.get("error", "Unknown error")
                    })
            
            except KeyboardInterrupt:
                print("\n\n⚠️  Processing interrupted by user")
                break
            except Exception as e:
                stats["failed"] += 1
                stats["errors"].append({
                    "document_id": doc.id,
                    "error": str(e)
                })
                print(f"\n❌ Error processing document {doc.id}: {str(e)}")
        
        # Print summary
        print()
        print("=" * 70)
        print("Processing Summary")
        print("=" * 70)
        print(f"Total documents: {stats['total']}")
        print(f"✅ Successful: {stats['successful']}")
        print(f"❌ Failed: {stats['failed']}")
        print(f"⏭️  Skipped: {stats['skipped']}")
        print()
        print("Chunks Created:")
        print(f"  Total chunks: {stats['total_chunks']}")
        print(f"  Text chunks: {stats['text_chunks']}")
        print(f"  Table chunks: {stats['table_chunks']}")
        print(f"  Header chunks: {stats['header_chunks']}")
        print()
        
        if stats["errors"]:
            print(f"Errors ({len(stats['errors'])}):")
            for error in stats["errors"][:10]:  # Show first 10
                print(f"  - Document {error['document_id']}: {error['error']}")
            if len(stats["errors"]) > 10:
                print(f"  ... and {len(stats['errors']) - 10} more errors")
        
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ Fatal error: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Process all documents with enhanced processor")
    parser.add_argument("--document-type", type=str, help="Filter by document type")
    parser.add_argument("--property-id", type=int, help="Filter by property ID")
    parser.add_argument("--limit", type=int, help="Maximum number of documents to process")
    parser.add_argument("--no-skip-processed", action="store_true", help="Reprocess documents that already have chunks")
    parser.add_argument("--no-embeddings", action="store_true", help="Skip embedding generation")
    parser.add_argument("--no-pinecone", action="store_true", help="Skip Pinecone sync")
    
    args = parser.parse_args()
    
    process_all_documents(
        document_type=args.document_type,
        property_id=args.property_id,
        limit=args.limit,
        skip_processed=not args.no_skip_processed,
        generate_embeddings=not args.no_embeddings,
        sync_to_pinecone=not args.no_pinecone
    )


if __name__ == "__main__":
    main()

