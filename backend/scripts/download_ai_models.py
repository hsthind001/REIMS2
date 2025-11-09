#!/usr/bin/env python3
"""
AI Model Download and Caching Script

Downloads and caches AI/ML models for document extraction:
- LayoutLMv3 (microsoft/layoutlmv3-base) - ~1.3 GB
- Models are cached in /app/.cache/huggingface (Docker volume)

This script should be run during Docker build or on first startup.
"""

import os
import sys
from pathlib import Path

def download_layoutlmv3():
    """
    Download and cache Microsoft's LayoutLMv3 model.
    
    Model: microsoft/layoutlmv3-base
    Size: ~1.3 GB
    Use: Document understanding and layout analysis
    """
    print("=" * 80)
    print("📥 Downloading LayoutLMv3 Model")
    print("=" * 80)
    
    try:
        from transformers import LayoutLMv3Processor, LayoutLMv3ForTokenClassification
        
        model_name = "microsoft/layoutlmv3-base"
        cache_dir = os.getenv("TRANSFORMERS_CACHE", "/app/.cache/huggingface")
        
        print(f"Model: {model_name}")
        print(f"Cache directory: {cache_dir}")
        print(f"\nDownloading processor...")
        
        # Download processor (tokenizer + image processor)
        processor = LayoutLMv3Processor.from_pretrained(
            model_name,
            cache_dir=cache_dir
        )
        print("✅ Processor downloaded successfully")
        
        # Download model
        print(f"\nDownloading model (this may take a few minutes)...")
        model = LayoutLMv3ForTokenClassification.from_pretrained(
            model_name,
            cache_dir=cache_dir
        )
        print("✅ Model downloaded successfully")
        
        # Verify model loads
        print(f"\nVerifying model...")
        print(f"   Model config: {model.config.model_type}")
        print(f"   Hidden size: {model.config.hidden_size}")
        print(f"   Number of layers: {model.config.num_hidden_layers}")
        
        print("\n✅ LayoutLMv3 ready for use!")
        return True
        
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("   Please install: pip install transformers torch torchvision")
        return False
        
    except Exception as e:
        print(f"❌ Download failed: {e}")
        print(f"   Error type: {type(e).__name__}")
        return False


def check_disk_space(required_gb=5):
    """
    Check if sufficient disk space available for models.
    
    Args:
        required_gb: Required space in GB (default: 5 GB)
    
    Returns:
        bool: True if sufficient space available
    """
    try:
        import shutil
        
        cache_dir = os.getenv("TRANSFORMERS_CACHE", "/app/.cache/huggingface")
        
        # Create directory if it doesn't exist
        Path(cache_dir).mkdir(parents=True, exist_ok=True)
        
        # Check available space
        total, used, free = shutil.disk_usage(cache_dir)
        free_gb = free / (1024 ** 3)
        
        print(f"\n💾 Disk Space Check")
        print(f"   Location: {cache_dir}")
        print(f"   Available: {free_gb:.2f} GB")
        print(f"   Required: {required_gb} GB")
        
        if free_gb < required_gb:
            print(f"   ⚠️  WARNING: Low disk space!")
            return False
        
        print(f"   ✅ Sufficient space available")
        return True
        
    except Exception as e:
        print(f"   ⚠️  Could not check disk space: {e}")
        return True  # Continue anyway


def verify_model_cached():
    """
    Verify that models are properly cached.
    
    Returns:
        bool: True if models are available in cache
    """
    try:
        cache_dir = os.getenv("TRANSFORMERS_CACHE", "/app/.cache/huggingface")
        cache_path = Path(cache_dir)
        
        if not cache_path.exists():
            print("❌ Cache directory does not exist")
            return False
        
        # Look for model files
        model_files = list(cache_path.rglob("*.bin")) + list(cache_path.rglob("*.safetensors"))
        
        if len(model_files) > 0:
            total_size = sum(f.stat().st_size for f in model_files) / (1024 ** 3)
            print(f"\n✅ Found {len(model_files)} model files in cache")
            print(f"   Total size: {total_size:.2f} GB")
            return True
        else:
            print("❌ No model files found in cache")
            return False
            
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False


def main():
    """Main execution function"""
    print("\n" + "=" * 80)
    print("🤖 AI Model Download Script - Sprint 2")
    print("=" * 80)
    print("\nThis script downloads AI/ML models for document extraction")
    print("Models will be cached for reuse across container restarts\n")
    
    # Check disk space
    if not check_disk_space(required_gb=5):
        print("\n⚠️  WARNING: Low disk space. Continue anyway? (y/n)")
        # Auto-continue in Docker environment
        if os.getenv("DOCKER_ENV"):
            print("   Running in Docker - continuing automatically")
        else:
            response = input("   > ").lower()
            if response != 'y':
                print("❌ Download cancelled")
                return False
    
    # Download LayoutLMv3
    success = download_layoutlmv3()
    
    if not success:
        print("\n❌ Model download failed!")
        sys.exit(1)
    
    # Verify cache
    print("\n" + "-" * 80)
    print("🔍 Verifying Model Cache")
    print("-" * 80)
    
    if verify_model_cached():
        print("\n" + "=" * 80)
        print("✅ All models downloaded and cached successfully!")
        print("=" * 80)
        print("\nModels are ready for use in extraction workflows")
        print("Cache location:", os.getenv("TRANSFORMERS_CACHE", "/app/.cache/huggingface"))
        return True
    else:
        print("\n❌ Model verification failed!")
        sys.exit(1)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

