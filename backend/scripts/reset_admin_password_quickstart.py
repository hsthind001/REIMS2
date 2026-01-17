from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.user import User
from app.core.security import get_password_hash

def reset_admin_password():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == "admin").first()
        if not user:
            print("Admin user not found! run ensure_admin.py first or verify seeds.")
            return

        print("Resetting admin password to 'Admin123!'...")
        user.hashed_password = get_password_hash("Admin123!")
        db.commit()
        print("✅ Password reset successful.")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    reset_admin_password()
