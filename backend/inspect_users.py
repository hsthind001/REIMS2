import sys
import os

# Add the current directory to the path so we can import 'app'
sys.path.append(os.getcwd())

from app.db.database import SessionLocal
from app.models.user import User

def main():
    print("Connecting to database...")
    try:
        db = SessionLocal()
        users = db.query(User).all()
        print(f"Found {len(users)} users:")
        for u in users:
            print(f"- ID: {u.id}")
            print(f"  Username: {u.username}")
            print(f"  Email: {u.email}")
            print(f"  Is Active: {u.is_active}")
            print(f"  Is Superuser: {u.is_superuser}")
            print("-" * 20)
        db.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
