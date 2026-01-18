#!/usr/bin/env python3
"""
Admin Script: View All Tenants and Their Subscriptions
This script allows the REIMS platform owner to view all organizations (tenants)
and their subscription status.
"""

from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.user import User
from app.models.organization import Organization, OrganizationMember
from tabulate import tabulate


def view_all_tenants():
    """View all organizations and their subscription details"""
    db = SessionLocal()
    try:
        # Get all organizations with subscription details
        orgs = db.query(Organization).all()
        
        org_data = []
        for org in orgs:
            # Count members in this organization
            member_count = db.query(OrganizationMember).filter(
                OrganizationMember.organization_id == org.id
            ).count()
            
            # Get organization owner (if any)
            owner = db.query(User).join(OrganizationMember).filter(
                OrganizationMember.organization_id == org.id,
                OrganizationMember.role == "owner"
            ).first()
            
            org_data.append({
                "ID": org.id,
                "Name": org.name,
                "Slug": org.slug,
                "Subscription": org.subscription_status,
                "Stripe Customer": org.stripe_customer_id or "N/A",
                "Members": member_count,
                "Owner": owner.username if owner else "N/A",
                "Created": org.created_at.strftime("%Y-%m-%d") if org.created_at else "N/A"
            })
        
        print("\n" + "="*100)
        print("REIMS Platform - All Tenants (Organizations)")
        print("="*100 + "\n")
        
        if org_data:
            print(tabulate(org_data, headers="keys", tablefmt="grid"))
            print(f"\n📊 Total Organizations: {len(org_data)}")
        else:
            print("No organizations found.")
        
        print("\n")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()


def view_all_users():
    """View all users on the platform"""
    db = SessionLocal()
    try:
        users = db.query(User).all()
        
        user_data = []
        for user in users:
            # Get user's organizations
            orgs = db.query(Organization).join(OrganizationMember).filter(
                OrganizationMember.user_id == user.id
            ).all()
            
            org_names = ", ".join([org.name for org in orgs]) if orgs else "None"
            
            user_data.append({
                "ID": user.id,
                "Username": user.username,
                "Email": user.email,
                "Superuser": "✓" if user.is_superuser else "",
                "Active": "✓" if user.is_active else "",
                "Organizations": org_names,
                "Created": user.created_at.strftime("%Y-%m-%d") if user.created_at else "N/A"
            })
        
        print("\n" + "="*100)
        print("REIMS Platform - All Users")
        print("="*100 + "\n")
        
        if user_data:
            print(tabulate(user_data, headers="keys", tablefmt="grid"))
            print(f"\n👥 Total Users: {len(user_data)}")
        else:
            print("No users found.")
        
        print("\n")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()


def main():
    """Main function to display admin dashboard"""
    print("\n" + "🏢 " * 30)
    print("REIMS SaaS Platform - Admin Dashboard")
    print("🏢 " * 30 + "\n")
    
    view_all_tenants()
    view_all_users()


if __name__ == "__main__":
    main()
