import sys
import os
from sqlalchemy import text

# Add the current directory to the path so we can import 'app'
sys.path.append(os.getcwd())

from app.db.database import SessionLocal

def main():
    print("Connecting to database...")
    db = SessionLocal()
    try:
        # Check if user exists
        check_sql = text("SELECT id, username FROM users WHERE id = 5")
        result = db.execute(check_sql).fetchone()
        
        if result:
            print(f"Found user to delete: ID={result[0]}, Username={result[1]}")
            
            # Delete from dependencies first (to be safe, though cascades might handle it)
            # We know OrganizationMember is a dependency
            print("Deleting organization memberships...")
            db.execute(text("DELETE FROM organization_members WHERE user_id = 5"))
            
            # Delete any workflow locks where this user is the locker/unlocker etc
            # This might be where the previous error came from (model load)
            print("Deleting workflow locks checks...")
            db.execute(text("DELETE FROM workflow_locks WHERE locked_by = 5 OR unlocked_by = 5 OR approved_by = 5 OR rejected_by = 5"))
            
            print("Deleting user...")
            db.execute(text("DELETE FROM users WHERE id = 5"))
            
            db.commit()
            print("User deleted successfully via raw SQL.")
        else:
            print("User with ID 5 not found.")
            
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()
