
import sys
import os
sys.path.append(os.getcwd())
from app.db.database import SessionLocal
from app.models.user import User
from app.models.organization import Organization, OrganizationMember
from app.models.property import Property

db = SessionLocal()

print("-" * 50)
print("USERS:")
for u in db.query(User).all():
    print(f"ID: {u.id}, Username: {u.username}, Active: {u.is_active}")

print("-" * 50)
print("ORGANIZATIONS:")
for o in db.query(Organization).all():
    print(f"ID: {o.id}, Name: {o.name}")

print("-" * 50)
print("MEMBERSHIPS:")
for m in db.query(OrganizationMember).all():
    print(f"User {m.user_id} -> Org {m.organization_id} ({m.role})")

print("-" * 50)
print("PROPERTIES:")
for p in db.query(Property).all():
    print(f"ID: {p.id}, Code: {p.property_code}, OrgID: {p.organization_id}")
