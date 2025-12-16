#!/usr/bin/env python3
"""
Initialize Pinecone Vector Database

This script initializes Pinecone and creates the index if it doesn't exist.
Run this after setting PINECONE_API_KEY in your .env file.
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config.pinecone_config import pinecone_config
from app.core.config import settings


def main():
    """Initialize Pinecone"""
    print("=" * 60)
    print("Pinecone Vector Database Initialization")
    print("=" * 60)
    print()
    
    # Check API key
    if not settings.PINECONE_API_KEY:
        print("❌ ERROR: PINECONE_API_KEY not set in environment variables")
        print()
        print("Please set PINECONE_API_KEY in your .env file:")
        print("  PINECONE_API_KEY=your-api-key-here")
        print()
        print("Get your API key from: https://app.pinecone.io/")
        return 1
    
    print(f"✓ API Key: {'*' * 20}{settings.PINECONE_API_KEY[-4:]}")
    print(f"✓ Environment: {settings.PINECONE_ENVIRONMENT}")
    print(f"✓ Index Name: {settings.PINECONE_INDEX_NAME}")
    print(f"✓ Dimension: {settings.PINECONE_DIMENSION}")
    print(f"✓ Metric: {settings.PINECONE_METRIC}")
    print()
    
    # Initialize Pinecone
    print("Initializing Pinecone...")
    try:
        success = pinecone_config.initialize()
        
        if not success:
            print("❌ Failed to initialize Pinecone")
            return 1
        
        print("✓ Pinecone initialized successfully")
        print()
        
        # Health check
        print("Performing health check...")
        health = pinecone_config.health_check()
        
        if health['healthy']:
            print("✓ Pinecone is healthy")
            print(f"✓ Total vectors: {health.get('stats', {}).get('total_vector_count', 0)}")
            
            namespaces = health.get('stats', {}).get('namespaces', [])
            if namespaces:
                print(f"✓ Namespaces: {', '.join(namespaces)}")
        else:
            print(f"⚠️  Pinecone health check failed: {health.get('error')}")
            return 1
        
        print()
        print("=" * 60)
        print("✅ Pinecone initialization complete!")
        print("=" * 60)
        print()
        print("Next steps:")
        print("  1. Run migration script to sync existing data:")
        print("     python scripts/migrate_to_pinecone.py")
        print()
        
        return 0
        
    except Exception as e:
        print(f"❌ Error initializing Pinecone: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())

