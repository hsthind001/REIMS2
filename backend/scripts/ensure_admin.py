from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.user import User
from app.models.organization import Organization, OrganizationMember
from app.core.security import get_password_hash

def ensure_admin():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == "admin").first()
        if not user:
            print("Creating admin user...")
            user = User(
                username="admin",
                email="admin@example.com",
                hashed_password=get_password_hash("admin"),
                is_active=True,
                is_superuser=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            print("Admin user created.")
        else:
            print("Admin user exists. Resetting password...")
            user.hashed_password = get_password_hash("admin")
            user.is_active = True
            db.commit()
            print("Password reset to 'admin'.")

        # Ensure Organization
        org = db.query(Organization).first()
        if not org:
            print("Creating default organization...")
            org = Organization(name="Default Org", slug="default-org")
            db.add(org)
            db.commit()
            db.refresh(org)
            print("Default organization created.")
        
        # Ensure Membership
        member = db.query(OrganizationMember).filter(
            OrganizationMember.user_id == user.id,
            OrganizationMember.organization_id == org.id
        ).first()

        if not member:
            print("Adding admin to organization...")
            member = OrganizationMember(
                user_id=user.id,
                organization_id=org.id,
                role="admin"
            )
            db.add(member)
            db.commit()
            print("Admin added to organization.")
        
        print("✅ Admin user and organization setup complete.")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    ensure_admin()
