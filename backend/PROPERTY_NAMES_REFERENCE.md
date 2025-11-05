# Official Property Names

## Source of Truth

Property names are extracted from the actual PDF financial documents. This document serves as the authoritative reference for correct property names to prevent data entry errors.

## Property Reference Table

| Code | Official Name | Source Document | Notes |
|------|---------------|-----------------|-------|
| ESP001 | Eastern Shore Plaza | ESP 2023 Cash Flow Statement.pdf | **Previously incorrect**: Was listed as "Esplanade Shopping Center" in seed data |
| HMND001 | Hammond Aire Shopping Center | Hammond Aire 2023 Balance Sheet.pdf | ✅ Correct from initial seeding |
| TCSH001 | The Crossings of Spring Hill | TCSH 2024 Balance Sheet.pdf | **Previously incomplete**: Was listed as "Town Center Shopping" |
| WEND001 | Wendover Commons | Wendover Commons 2023 Balance Sheet.pdf | ✅ Correct from initial seeding |

## Data Entry Guidelines

### When Adding New Properties:

1. **Always refer to official documents** (financial statements, legal documents, lease agreements)
2. **Use the full legal name** of the property as it appears in financial statements
3. **Verify spelling** by checking multiple documents
4. **Document the source** in the property notes field

### Property Name Format:

- Use proper title case (e.g., "Eastern Shore Plaza" not "EASTERN SHORE PLAZA")
- Include full names, not abbreviations (unless abbreviation is the official name)
- Do not include property codes in the name field
- Avoid using location descriptors unless part of the official name

## Common Mistakes to Avoid

❌ **Don't guess** or make up property names  
❌ **Don't use short names** when the official name is longer  
❌ **Don't rely on old seed data** without verification  
❌ **Don't skip validation** when entering property data  

✅ **Do reference** PDF financial documents  
✅ **Do use full legal names** as they appear in documents  
✅ **Do verify** against multiple sources when possible  
✅ **Do update** this reference when adding new properties  

## Change History

| Date | Property Code | Old Name | New Name | Reason |
|------|---------------|----------|----------|--------|
| 2025-11-05 | ESP001 | Esplanade Shopping Center | Eastern Shore Plaza | Corrected to match PDF documents |
| 2025-11-05 | TCSH001 | Town Center Shopping | The Crossings of Spring Hill | Updated to full legal name |

## Verification Process

Before deploying or seeding property data:

1. Run the verification script: `python backend/scripts/verify_property_data.py`
2. Check that all property names match this reference
3. Review any discrepancies with source documents
4. Update this reference if new official documents show different names

## Contact

For questions about property names or to report discrepancies, please:
- Review the source PDF documents in the sample data folder
- Check the audit trail for any property name changes
- Consult with property management team for legal names

