#!/usr/bin/env python3
"""
Build BM25 Index Script

Standalone script to build BM25 index from all document chunks.
Can be run manually or scheduled (e.g., nightly cron job).
"""
import sys
import os
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import SessionLocal
from app.services.bm25_search_service import BM25SearchService
from app.config.bm25_config import bm25_config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main function to build BM25 index"""
    logger.info("=" * 60)
    logger.info("BM25 Index Building Script")
    logger.info("=" * 60)
    
    # Initialize database
    db = SessionLocal()
    
    try:
        # Create BM25 service
        service = BM25SearchService(db)
        
        # Get current stats
        stats_before = service.get_index_stats()
        logger.info(f"Current index stats: {stats_before}")
        
        # Build index
        logger.info("Building BM25 index from all document chunks...")
        result = service.build_index(force_rebuild=True)
        
        if result.get("success"):
            logger.info("=" * 60)
            logger.info("✅ BM25 Index Built Successfully")
            logger.info("=" * 60)
            logger.info(f"Chunk count: {result.get('chunk_count')}")
            logger.info(f"Build time: {result.get('build_time_seconds'):.2f} seconds")
            logger.info(f"Cache path: {result.get('cache_path')}")
            
            # Get updated stats
            stats_after = service.get_index_stats()
            logger.info(f"Cache size: {stats_after.get('cache_size_mb')} MB")
            logger.info(f"Index version: {stats_after.get('version')}")
            
            logger.info("=" * 60)
            return 0
        else:
            logger.error("=" * 60)
            logger.error("❌ Failed to build BM25 index")
            logger.error("=" * 60)
            logger.error(f"Error: {result.get('error')}")
            return 1
            
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

