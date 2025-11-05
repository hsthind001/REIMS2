#!/usr/bin/env python3
"""
Property Data Verification Script

Verifies that property names in the database match the expected values from PDF documents.
This helps prevent and detect data entry errors.

Usage:
    python backend/scripts/verify_property_data.py
    
Or from Docker:
    docker exec reims-backend python3 scripts/verify_property_data.py
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.property import Property


# Official property names from PDF documents
# Source: Financial statements and official documents
EXPECTED_PROPERTIES = {
    "ESP001": "Eastern Shore Plaza",
    "HMND001": "Hammond Aire Shopping Center",
    "TCSH001": "The Crossings of Spring Hill",
    "WEND001": "Wendover Commons"
}


class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def verify_properties(db: Session) -> bool:
    """
    Check if property names in database match expected values
    
    Args:
        db: Database session
        
    Returns:
        True if all properties are correct, False if issues found
    """
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.BLUE}Property Data Verification{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.ENDC}\n")
    
    issues = []
    correct_count = 0
    missing_count = 0
    
    for code, expected_name in EXPECTED_PROPERTIES.items():
        prop = db.query(Property).filter(Property.property_code == code).first()
        
        if not prop:
            missing_count += 1
            issues.append({
                'type': 'missing',
                'code': code,
                'expected': expected_name
            })
            print(f"{Colors.YELLOW}⚠️  {code}: Property not found in database{Colors.ENDC}")
            print(f"    Expected: '{expected_name}'")
            print()
        elif prop.property_name != expected_name:
            issues.append({
                'type': 'mismatch',
                'code': code,
                'expected': expected_name,
                'actual': prop.property_name
            })
            print(f"{Colors.RED}❌ {code}: Name mismatch{Colors.ENDC}")
            print(f"    Expected: '{expected_name}'")
            print(f"    Actual:   '{prop.property_name}'")
            print()
        else:
            correct_count += 1
            print(f"{Colors.GREEN}✅ {code}: {prop.property_name}{Colors.ENDC}")
    
    # Summary
    print(f"\n{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}Verification Summary:{Colors.ENDC}")
    print(f"  {Colors.GREEN}✅ Correct: {correct_count}{Colors.ENDC}")
    print(f"  {Colors.RED}❌ Mismatches: {len([i for i in issues if i['type'] == 'mismatch'])}{Colors.ENDC}")
    print(f"  {Colors.YELLOW}⚠️  Missing: {missing_count}{Colors.ENDC}")
    print(f"{Colors.BOLD}{'='*60}{Colors.ENDC}\n")
    
    if issues:
        print(f"{Colors.BOLD}{Colors.RED}⚠️  Issues Found!{Colors.ENDC}\n")
        print(f"To fix mismatches, update the database:")
        for issue in issues:
            if issue['type'] == 'mismatch':
                print(f"  UPDATE properties SET property_name = '{issue['expected']}' WHERE property_code = '{issue['code']}';")
        
        print(f"\nTo fix missing properties, run the seed script:")
        print(f"  python backend/scripts/seed_sample_data.py")
        print()
        return False
    else:
        print(f"{Colors.BOLD}{Colors.GREEN}🎉 All property names verified correct!{Colors.ENDC}\n")
        return True


def main():
    """Main function"""
    try:
        db = SessionLocal()
        
        # Check if properties table has data
        count = db.query(Property).count()
        if count == 0:
            print(f"{Colors.YELLOW}No properties found in database.{Colors.ENDC}")
            print(f"Run the seed script to populate properties:")
            print(f"  python backend/scripts/seed_sample_data.py")
            sys.exit(1)
        
        # Verify properties
        success = verify_properties(db)
        
        # Exit with appropriate code
        sys.exit(0 if success else 1)
        
    except Exception as e:
        print(f"{Colors.RED}Error: {str(e)}{Colors.ENDC}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()

