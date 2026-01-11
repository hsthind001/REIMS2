# REIMS2 User Guide

**Version**: 2.0  
**Last Updated**: November 4, 2025

---

## Getting Started

### Access the System

1. Open your web browser
2. Navigate to: `http://localhost:5173`
3. You'll see the REIMS login screen

### First Time Setup

#### 1. Register Your Account
- Click "Register" in the top right
- Fill in the form:
  - Email: Your email address
  - Username: Choose a username (3+ characters, alphanumeric)
  - Password: At least 8 characters with uppercase, lowercase, and digit
  - Confirm Password: Re-enter password
- Click "Register"
- You'll be automatically logged in

#### 2. Login
- If you already have an account, click "Login"
- Enter username and password
- Click "Login"
- You'll be redirected to the dashboard

---

## Main Features

### Dashboard

The dashboard provides an overview of your system:

- **Summary Cards**: Total properties, documents uploaded, completed extractions, pending reviews
- **Property Cards**: Visual cards for each property with status
- **Recent Uploads**: Table showing the 10 most recent document uploads

**Tips**:
- Use the dashboard to get a quick snapshot of system status
- Click on properties to see more details (coming soon)
- Monitor extraction progress from recent uploads

---

### Properties Management

#### View Properties
1. Click "Properties" in the sidebar
2. See all properties in a table format
3. Columns: Code, Name, Type, Location, Area, Status

#### Add a New Property
1. Click "+ Add Property" button
2. Fill in the form:
   - **Property Code** (Required): e.g., "ESP001" - Letters + 3 digits
   - **Property Name** (Required): e.g., "Esplanade Shopping Center"
   - **Property Type**: Retail, Office, Industrial, Mixed Use, Multifamily
   - **Total Area**: Square footage
   - **Address, City, State, ZIP**: Location information
   - **Acquisition Date**: When property was acquired
   - **Ownership Structure**: LLC, Partnership, etc.
   - **Status**: Active, Sold, Under Contract
   - **Notes**: Any additional information
3. Click "Create"

**Note**: Property Code cannot be changed after creation (unique identifier)

#### Edit a Property
1. Find the property in the list
2. Click "Edit" button
3. Modify any field (except Property Code)
4. Click "Update"

#### Delete a Property
1. Click "Delete" button
2. Confirm deletion
3. **Warning**: This will delete ALL financial data for this property!

---

### Document Upload & Management

#### Upload a Financial Document

1. Navigate to "Documents" page
2. In the upload section:
   - **Select Property**: Choose from dropdown
   - **Select Document Type**: Balance Sheet, Income Statement, Cash Flow, or Rent Roll
   - **Select Period**: Year and Month
   - **Upload File**: 
     - Drag and drop PDF file into the box
     - OR click the box to browse for file
     - Must be PDF format
     - Maximum 50MB

3. Click "Upload Document"
4. Wait for upload to complete
5. The document will appear in the list below with status "pending"

#### Monitor Extraction Status

After upload, the system automatically extracts data:
- **Pending**: Queued for extraction
- **Processing**: Currently extracting data
- **Completed**: Extraction successful (ready to review)
- **Failed**: Extraction failed (check logs or re-upload)

#### Filter Documents

Use the filter controls to find specific documents:
- **Property**: Filter by property code
- **Document Type**: Filter by statement type
- **Status**: Filter by extraction status
- Click "Apply Filters" to refresh list

#### Download Documents

1. Find document in the list
2. Click "Download" button
3. PDF will open in new tab or download

---

### Review Queue & Reports

#### Access Review Queue

1. Navigate to "Reports" page
2. The top section shows "Review Queue"
3. Lists all data items that need manual review
4. Typically items with confidence < 85%

#### Review Process

1. Find item in review queue
2. Check: Property, Period, Account, Confidence score
3. Options:
   - **Approve**: Click "Approve" if data looks correct
   - **Edit**: Click "Edit" to make corrections (feature coming soon)

#### View Financial Reports

1. Select a property from the dropdown
2. Choose report type:
   - Balance Sheet
   - Income Statement
   - Cash Flow Statement
3. View or export data

---

## Export Data

### Using API Endpoints

#### Export Balance Sheet to Excel
```
GET http://localhost:8000/api/v1/exports/balance-sheet/excel?property_code=ESP001&year=2024&month=12
```

#### Export Income Statement to Excel
```
GET http://localhost:8000/api/v1/exports/income-statement/excel?property_code=ESP001&year=2024&month=12
```

#### Export to CSV
```
GET http://localhost:8000/api/v1/exports/csv?property_code=ESP001&year=2024&month=12&document_type=balance_sheet
```

**Note**: You must be logged in to export data (session cookie required)

### Using Browser
1. Open API docs: http://localhost:8000/docs
2. Click "Authorize" and login
3. Find export endpoint
4. Enter parameters (property_code, year, month)
5. Click "Execute"
6. Download file from response

---

## Tips & Best Practices

### Document Naming
- Use consistent naming: `PropertyCode_Year_Month_Type.pdf`
- Example: `ESP001_2024_12_Balance_Sheet.pdf`
- Helps with organization and tracking

### Monthly Workflow
1. Upload Balance Sheet for period
2. Upload Income Statement
3. Upload Cash Flow Statement
4. (Optional) Upload Rent Roll
5. Wait for extraction to complete
6. Review any flagged items (confidence < 85%)
7. Approve or correct data
8. Export to Excel for analysis

### Data Quality
- The system extracts data with 95-98% accuracy
- Items with confidence < 85% are automatically flagged for review
- Always review flagged items before using data for decisions
- Re-upload if extraction quality is poor

### Performance
- Upload during off-peak hours for large batches
- System can handle 100+ documents simultaneously
- Extraction takes 30-60 seconds per document
- Use filters to find documents quickly

---

## Troubleshooting

### Can't Login
- Check username and password (case-sensitive)
- Ensure caps lock is off
- Password must be exactly as registered
- Try registering a new account if you forgot credentials

### Upload Fails
- Check file is PDF format
- Check file size < 50MB
- Ensure property exists
- Ensure period is valid (month 1-12)

### Extraction Stuck in "Processing"
- Wait 2-3 minutes (normal processing time)
- If stuck > 5 minutes, check Celery worker logs
- Contact admin if persists

### Data Looks Wrong
- Check if document was scanned (OCR) vs digital PDF
- OCR accuracy may vary
- Use review queue to correct values
- Can re-upload document if needed

### Can't Export
- Ensure you're logged in
- Check property and period exist
- Check data has been extracted for that period
- Try API docs interface if browser download fails

---

## Keyboard Shortcuts

- `Esc`: Close modal/form
- `Ctrl + S`: Submit form (when focused)
- `Tab`: Navigate form fields

---

## Getting Help

### Log Files
- Backend: `docker logs reims-backend`
- Celery: `docker logs reims-celery-worker`
- Frontend: `docker logs reims-frontend`

### API Documentation
- Interactive docs: http://localhost:8000/docs
- OpenAPI spec: http://localhost:8000/api/v1/openapi.json

### Admin Contact
- For system issues, contact your administrator
- Provide: property code, document ID, timestamp of error

---

## Appendix: Document Types

### Balance Sheet
- Shows: Assets, Liabilities, Equity
- Frequency: Monthly or Quarterly
- Key fields: Total Assets, Total Liabilities, Total Equity
- Validation: Assets = Liabilities + Equity

### Income Statement
- Shows: Revenue, Expenses, Net Income
- Frequency: Monthly with YTD
- Key fields: Total Revenue, Total Expenses, NOI, Net Income
- Validation: Net Income = Revenue - Expenses

### Cash Flow Statement
- Shows: Operating, Investing, Financing cash flows
- Frequency: Monthly or Quarterly
- Key fields: Operating CF, Investing CF, Financing CF, Net CF
- Validation: Ending Cash = Beginning Cash + Net CF

### Rent Roll
- Shows: Tenant leases, occupancy, rent
- Frequency: Monthly
- Key fields: Unit, Tenant, Lease dates, Rent, Occupancy
- Validation: Occupancy rate 0-100%, Total rent = Sum of tenant rents

---

**End of User Guide**  
For technical documentation, see `ADMIN_GUIDE.md`

