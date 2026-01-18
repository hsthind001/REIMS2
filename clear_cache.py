
import sys
import os

# Add backend directory to sys.path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.core.redis_client import invalidate_portfolio_cache

def clear_cache():
    print("Clearing portfolio cache...")
    count = invalidate_portfolio_cache()
    print(f"Cache cleared. {count} keys invalidated (approximate).")

if __name__ == "__main__":
    clear_cache()
