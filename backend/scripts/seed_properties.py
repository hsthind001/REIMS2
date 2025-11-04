"""
Property Definitions for Sample Data Loading

Defines the 4 properties found in sample PDFs:
- ESP001: Esplanade Shopping Center
- HMND001: Hammond Aire Shopping Center  
- TCSH001: Town Center Shopping
- WEND001: Wendover Commons
"""

PROPERTIES = [
    {
        "property_code": "ESP001",
        "property_name": "Esplanade Shopping Center",
        "property_type": "retail",
        "address": "1234 Main Street",
        "city": "Phoenix",
        "state": "AZ",
        "zip_code": "85001",
        "country": "USA",
        "total_area_sqft": "125000.50",
        "acquisition_date": "2020-01-15",
        "ownership_structure": "LLC",
        "status": "active",
        "notes": "Premium shopping center in Phoenix metro area"
    },
    {
        "property_code": "HMND001",
        "property_name": "Hammond Aire Shopping Center",
        "property_type": "retail",
        "address": "5678 Commerce Drive",
        "city": "Hammond",
        "state": "IN",
        "zip_code": "46320",
        "country": "USA",
        "total_area_sqft": "98500.00",
        "acquisition_date": "2019-06-01",
        "ownership_structure": "Partnership",
        "status": "active",
        "notes": "Regional shopping center in Hammond, Indiana"
    },
    {
        "property_code": "TCSH001",
        "property_name": "Town Center Shopping",
        "property_type": "retail",
        "address": "9012 Center Boulevard",
        "city": "Town Center",
        "state": "FL",
        "zip_code": "33411",
        "country": "USA",
        "total_area_sqft": "110250.00",
        "acquisition_date": "2021-03-20",
        "ownership_structure": "LLC",
        "status": "active",
        "notes": "Mixed-use retail center in South Florida"
    },
    {
        "property_code": "WEND001",
        "property_name": "Wendover Commons",
        "property_type": "retail",
        "address": "3456 Wendover Avenue",
        "city": "Greensboro",
        "state": "NC",
        "zip_code": "27407",
        "country": "USA",
        "total_area_sqft": "87600.00",
        "acquisition_date": "2018-11-10",
        "ownership_structure": "LLC",
        "status": "active",
        "notes": "Community shopping center in Greensboro, NC"
    }
]


def get_property_by_code(property_code: str):
    """Get property definition by property code"""
    for prop in PROPERTIES:
        if prop["property_code"] == property_code:
            return prop
    return None


def get_all_properties():
    """Get all property definitions"""
    return PROPERTIES

