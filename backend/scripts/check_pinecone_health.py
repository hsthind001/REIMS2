#!/usr/bin/env python3
"""
Check Pinecone Health Status

Quick script to check if Pinecone is configured and healthy.
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config.pinecone_config import pinecone_config
from app.core.config import settings


def main():
    """Check Pinecone health"""
    print("=" * 60)
    print("Pinecone Health Check")
    print("=" * 60)
    print()
    
    # Check configuration
    print("Configuration:")
    print(f"  API Key: {'✓ Set' if settings.PINECONE_API_KEY else '❌ Not set'}")
    print(f"  Environment: {settings.PINECONE_ENVIRONMENT}")
    print(f"  Index Name: {settings.PINECONE_INDEX_NAME}")
    print(f"  Dimension: {settings.PINECONE_DIMENSION}")
    print(f"  Metric: {settings.PINECONE_METRIC}")
    print()
    
    if not settings.PINECONE_API_KEY:
        print("❌ PINECONE_API_KEY not set. Please configure in .env file.")
        return 1
    
    # Check initialization
    print("Initialization:")
    if not pinecone_config.is_initialized():
        print("  Status: Not initialized")
        print("  Attempting to initialize...")
        
        success = pinecone_config.initialize()
        if not success:
            print("  ❌ Failed to initialize")
            return 1
        print("  ✓ Initialized")
    else:
        print("  ✓ Already initialized")
    
    print()
    
    # Health check
    print("Health Status:")
    health = pinecone_config.health_check()
    
    if health['healthy']:
        print("  ✓ Healthy")
        print()
        print("Statistics:")
        stats = health.get('stats', {})
        print(f"  Total vectors: {stats.get('total_vector_count', 0):,}")
        
        namespaces = stats.get('namespaces', {})
        if namespaces:
            print("  Namespaces:")
            for ns, count in namespaces.items():
                ns_name = ns if ns else '(default)'
                print(f"    - {ns_name}: {count:,} vectors")
        else:
            print("  Namespaces: None")
        
        print()
        print("=" * 60)
        print("✅ Pinecone is healthy and ready to use!")
        print("=" * 60)
        return 0
    else:
        print(f"  ❌ Unhealthy: {health.get('error')}")
        print()
        print("=" * 60)
        print("❌ Pinecone health check failed")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    exit(main())

