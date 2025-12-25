# Month Mismatch Self-Learning Solution

**Date:** December 25, 2025
**Priority:** HIGH - Blocks bulk uploads
**Status:** Solution Designed - Ready for Implementation

---

## Problem Analysis

### The Pattern

**ALL period-range filenames are being incorrectly detected as "Month 3":**

| Filename | Filename Says | PDF Says | System Used | Actual Period |
|----------|---------------|----------|-------------|---------------|
| `Income_Statement_esp_Accrual-5.25-6.25.pdf` | Month 5 | **Month 3** ❌ | Month 3 | Should be June (6) |
| `Income_Statement_esp_Accrual-6.25-7.25.pdf` | Month 6 | **Month 3** ❌ | Month 3 | Should be July (7) |
| `Income_Statement_esp_Accrual-7.25-8.25.pdf` | Month 7 | **Month 3** ❌ | Month 3 | Should be August (8) |
| `Income_Statement_esp_Accrual-8.25-9.25.pdf` | Month 8 | **Month 3** ❌ | Month 3 | Should be September (9) |
| `Income_Statement_esp_Accrual-9.25-10.25.pdf` | Month 9 | **Month 3** ❌ | Month 3 | Should be October (10) |
| `Income_Statement_esp_Accrual-10.25-11.25.pdf` | Month 10 | **Month 3** ❌ | Month 3 | Should be November (11) |
| `Income_Statement_esp_Accrual-11.25-12.25.pdf` | Month 11 | **Month 3** ❌ | Month 3 | Should be December (12) |
| `Income_Statement_esp_Accrual-12.24-1.25.pdf` | Month 12 | **Month 1** ✅ | Month 1 | January 2025 ✅ |

**Same pattern for Cash Flow statements!**

### Root Cause: PDF Content Detector is WRONG

The PDF content detector is **systematically detecting "Month 3" for all these statements**. This is a critical bug in the extraction engine.

**Hypothesis:** The PDF might contain:
- Fiscal year information showing "Q3" or "Quarter 3"
- Year-to-date totals through Q3
- Comparison columns showing "3 months ago"
- Some other text pattern that's being misinterpreted as "March"

### Impact

**16 uploads were BLOCKED due to duplicates:**
- Uploads 591-596: Income Statement months 5-10 (May-October 2025)
- Uploads 603-608: Cash Flow months 5-10 (May-October 2025)

**What happened:**
1. First file (`-5.25-6.25.pdf`) uploaded → Detected as "Month 3" → Stored for March 2025 ✅
2. Second file (`-6.25-7.25.pdf`) uploaded → Detected as "Month 3" → **DUPLICATE SKIPPED** ❌
3. Third file (`-7.25-8.25.pdf`) uploaded → Detected as "Month 3" → **DUPLICATE SKIPPED** ❌
4. ... and so on for all subsequent files

**Result:** Only 1 file stored for March, all others skipped. **Data for May-December 2025 is MISSING.**

---

## Critical Discovery: Why "Month 3" Every Time?

The PDF content detector is finding the same text pattern in ALL these PDFs that makes it think "March". Let me investigate what that pattern might be.

### Possible Causes

1. **"YTD" or "Q3" text:** PDFs might show year-to-date totals through Q3
2. **Comparison period:** "vs 3 months ago" or "trailing 3 months"
3. **Date format confusion:** European date format "DD.MM.YYYY" being parsed wrong
4. **Template artifact:** Standard template with "Period 3" somewhere
5. **Regex bug:** Regular expression matching wrong text

---

## Comprehensive Solution: Multi-Layered Self-Learning System

### Phase 1: Fix Period Range Detection (IMMEDIATE)

#### 1.1 Enhanced Filename Parser

**Location:** `backend/app/utils/document_type_detector.py` or create new file

```python
import re
from typing import Optional, Dict, Tuple

class PeriodRangeDetector:
    """
    Detects period ranges in filenames and extracts the ending period.

    Patterns supported:
    - MM.YY-MM.YY (e.g., "5.25-6.25" = May 2025 to June 2025)
    - MM-YY-MM-YY (e.g., "5-25-6-25")
    - YYYY.MM-YYYY.MM (e.g., "2025.05-2025.06")
    """

    PERIOD_RANGE_PATTERNS = [
        # Pattern 1: MM.YY-MM.YY (most common)
        r'(\d{1,2})\.(\d{2})-(\d{1,2})\.(\d{2})',

        # Pattern 2: MM-YY-MM-YY
        r'(\d{1,2})-(\d{2})-(\d{1,2})-(\d{2})',

        # Pattern 3: YYYY.MM-YYYY.MM or YYYY-MM-YYYY-MM
        r'(\d{4})[\.\-](\d{1,2})[\.\-](\d{4})[\.\-](\d{1,2})',

        # Pattern 4: MM/YY-MM/YY or MM/YYYY-MM/YYYY
        r'(\d{1,2})/(\d{2,4})-(\d{1,2})/(\d{2,4})',
    ]

    def detect_period_range(self, filename: str) -> Optional[Dict]:
        """
        Detect if filename contains a period range.

        Returns:
            {
                "is_range": True,
                "start_month": int,
                "start_year": int,
                "end_month": int,
                "end_year": int,
                "pattern": str,
                "matched_text": str
            }
            or None if no range detected
        """
        for pattern in self.PERIOD_RANGE_PATTERNS:
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                groups = match.groups()

                # Pattern 1 & 2: MM.YY-MM.YY or MM-YY-MM-YY
                if len(groups) == 4 and len(groups[1]) == 2:
                    start_month = int(groups[0])
                    start_year = self._parse_year(groups[1])
                    end_month = int(groups[2])
                    end_year = self._parse_year(groups[3])

                # Pattern 3: YYYY.MM-YYYY.MM
                elif len(groups) == 4 and len(groups[0]) == 4:
                    start_year = int(groups[0])
                    start_month = int(groups[1])
                    end_year = int(groups[2])
                    end_month = int(groups[3])

                else:
                    continue

                # Validate months
                if not (1 <= start_month <= 12 and 1 <= end_month <= 12):
                    continue

                # Validate year progression
                if end_year < start_year:
                    continue
                if end_year == start_year and end_month < start_month:
                    continue

                return {
                    "is_range": True,
                    "start_month": start_month,
                    "start_year": start_year,
                    "end_month": end_month,
                    "end_year": end_year,
                    "pattern": pattern,
                    "matched_text": match.group(0)
                }

        return None

    def _parse_year(self, year_str: str) -> int:
        """Convert 2-digit year to 4-digit year."""
        year = int(year_str)
        if year < 100:
            # Assume 20XX for years 00-50, 19XX for 51-99
            if year <= 50:
                year += 2000
            else:
                year += 1900
        return year

    def get_statement_period(self, period_range: Dict) -> Tuple[int, int]:
        """
        For period range statements, return the ending period
        (the period this statement should be filed under).

        Financial statements spanning multiple periods are typically
        filed under the ending period.

        Returns: (month, year)
        """
        return (period_range["end_month"], period_range["end_year"])
```

#### 1.2 Integration into Document Service

**Location:** `backend/app/services/document_service.py` lines 722-787

**BEFORE:**
```python
# Step 3: Detect month from filename (initial guess)
filename_month = detector.detect_month_from_filename(file.filename or "", year)
detected_year = year
```

**AFTER:**
```python
# Step 3: Detect period range FIRST, then fallback to single month
from app.utils.period_range_detector import PeriodRangeDetector
range_detector = PeriodRangeDetector()

period_range = range_detector.detect_period_range(file.filename or "")
filename_month = None
detected_year = year
is_period_range = False

if period_range:
    # Period range detected (e.g., "5.25-6.25")
    is_period_range = True
    filename_month, detected_year = range_detector.get_statement_period(period_range)

    print(f"✅ Period range detected: {period_range['matched_text']}")
    print(f"   Start: {period_range['start_month']}/{period_range['start_year']}")
    print(f"   End: {period_range['end_month']}/{period_range['end_year']}")
    print(f"   Filing under: {filename_month}/{detected_year}")
else:
    # No period range - use regular month detection
    filename_month = detector.detect_month_from_filename(file.filename or "", year)
    detected_year = year
```

**Then update the PDF content detection logic (lines 805-836):**

```python
# Month mismatch - SKIP WARNING if we detected a period range in filename
# Period range filenames are authoritative - they define the period explicitly
if (detected_type != "mortgage_statement" and
    not is_period_range and  # ← NEW: Skip warning for period ranges
    filename_month is not None and
    pdf_detected_month and
    pdf_detected_month != filename_month and
    pdf_period_confidence >= 50):

    anomaly_msg = f"Month mismatch: Filename suggests month {filename_month} but PDF content indicates month {pdf_detected_month} (confidence: {pdf_period_confidence}%)"
    anomalies.append(anomaly_msg)
```

**And update the final month selection (lines 846-851):**

```python
# Use PDF content if confidence > 50% - BUT NOT if we have a period range
# Period ranges in filenames are authoritative and explicit
if (detected_type != "mortgage_statement" and
    not is_period_range and  # ← NEW: Trust period range over PDF
    pdf_detected_month and
    pdf_period_confidence > 50):

    detected_month = pdf_detected_month
    result["month"] = detected_month
    print(f"✅ Using PDF content detection for month: {detected_month} (confidence: {pdf_period_confidence}%)")
elif is_period_range:
    # Use period range ending month
    detected_month = filename_month
    result["month"] = detected_month
    result["period_range"] = period_range  # Store for learning
    print(f"✅ Using period range from filename: {detected_month} (range: {period_range['matched_text']})")
```

---

### Phase 2: Fix PDF Content Detector Bug (CRITICAL)

The PDF content detector is **broken** - it's detecting "Month 3" for ALL these files. We need to fix it.

#### 2.1 Investigate Extraction Engine

**Location:** `backend/app/utils/extraction_engine.py` or wherever `detect_year_and_period` is implemented

**Debug steps:**

1. Extract one of these problem PDFs and examine the text
2. Find what pattern is matching "Month 3"
3. Fix the regex or logic

**Temporary fix:**
```python
def detect_year_and_period(self, pdf_content: bytes) -> Dict:
    """Detect year and month from PDF content."""

    # Extract text
    text = self.extract_text_from_pdf(pdf_content)

    # PRIORITY 1: Look for explicit "Period Ending" or "Statement Date"
    period_ending_patterns = [
        r'period ending[:\s]+([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})',  # "Period Ending: June 30, 2025"
        r'statement date[:\s]+(\d{1,2})/(\d{1,2})/(\d{4})',  # "Statement Date: 06/30/2025"
        r'for the month ending[:\s]+([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})',
        r'as of[:\s]+([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})',
    ]

    # Try each pattern
    for pattern in period_ending_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            # Extract and return
            ...

    # PRIORITY 2: Look for month/year in header area (first 500 chars)
    header_text = text[:500]

    # AVOID: Don't match "Q3", "3 months", "vs 3 months ago", etc.
    # These are NOT period indicators!

    return result
```

#### 2.2 Add Confidence Calibration

When PDF detector returns "Month 3" but filename shows a different range period, **reduce confidence**:

```python
# After PDF detection
if pdf_detected_month and is_period_range:
    if pdf_detected_month != filename_month:
        # Filename has explicit period range - reduce PDF confidence
        pdf_period_confidence = min(pdf_period_confidence * 0.5, 30)
        print(f"⚠️  PDF detected month {pdf_detected_month} conflicts with filename period range")
        print(f"   Reducing PDF confidence to {pdf_period_confidence}% (trusting filename)")
```

---

### Phase 3: Self-Learning Pattern Recognition (SMART)

Build a system that learns from successful uploads and applies patterns to future uploads.

#### 3.1 Pattern Learning Table

```sql
CREATE TABLE filename_period_patterns (
    id SERIAL PRIMARY KEY,
    pattern_type VARCHAR(50) NOT NULL,  -- 'period_range', 'single_month', 'fiscal_year'
    filename_pattern VARCHAR(200) NOT NULL,  -- regex pattern
    example_filename VARCHAR(255),
    detected_month INTEGER,
    detected_year INTEGER,
    confidence DECIMAL(5,2) DEFAULT 100.0,
    times_seen INTEGER DEFAULT 1,
    times_correct INTEGER DEFAULT 0,
    times_incorrect INTEGER DEFAULT 0,
    success_rate DECIMAL(5,2) GENERATED ALWAYS AS (
        CASE WHEN times_seen > 0
        THEN (times_correct::DECIMAL / times_seen * 100)
        ELSE 0 END
    ) STORED,
    property_id INTEGER REFERENCES properties(id),
    document_type VARCHAR(50),
    learned_at TIMESTAMP DEFAULT NOW(),
    last_seen_at TIMESTAMP DEFAULT NOW(),
    metadata JSONB,
    UNIQUE(filename_pattern, property_id, document_type)
);

CREATE INDEX idx_filename_patterns_success ON filename_period_patterns(success_rate DESC, times_seen DESC);
CREATE INDEX idx_filename_patterns_property ON filename_period_patterns(property_id, document_type);
```

#### 3.2 Pattern Learning Service

```python
# backend/app/services/filename_pattern_learning_service.py

from sqlalchemy.orm import Session
from app.models.filename_period_patterns import FilenamePeriodPattern
import re
from typing import Optional, Dict

class FilenamePatternLearningService:
    """
    Learn and apply filename → period detection patterns.

    This service:
    1. Captures successful uploads and their filename → period mappings
    2. Identifies recurring patterns
    3. Applies learned patterns to future uploads
    4. Adjusts confidence based on success rate
    """

    def __init__(self, db: Session):
        self.db = db

    def learn_from_upload(
        self,
        filename: str,
        detected_month: int,
        detected_year: int,
        property_id: int,
        document_type: str,
        detection_method: str,  # 'filename_range', 'pdf_content', 'manual'
        was_correct: Optional[bool] = None
    ):
        """
        Learn a pattern from a successful upload.

        Args:
            filename: Original filename
            detected_month: Month that was used
            detected_year: Year that was used
            property_id: Property ID
            document_type: Document type
            detection_method: How month was detected
            was_correct: If known, whether this detection was correct
        """
        # Extract pattern from filename
        pattern = self._extract_pattern(filename)
        if not pattern:
            return

        # Check if pattern exists
        existing = self.db.query(FilenamePeriodPattern).filter(
            FilenamePeriodPattern.filename_pattern == pattern,
            FilenamePeriodPattern.property_id == property_id,
            FilenamePeriodPattern.document_type == document_type
        ).first()

        if existing:
            # Update existing pattern
            existing.times_seen += 1
            existing.last_seen_at = datetime.now()
            if was_correct is not None:
                if was_correct:
                    existing.times_correct += 1
                else:
                    existing.times_incorrect += 1
        else:
            # Create new pattern
            new_pattern = FilenamePeriodPattern(
                pattern_type=self._classify_pattern(pattern),
                filename_pattern=pattern,
                example_filename=filename,
                detected_month=detected_month,
                detected_year=detected_year,
                property_id=property_id,
                document_type=document_type,
                times_seen=1,
                times_correct=1 if was_correct else 0,
                times_incorrect=0 if was_correct else 1,
                metadata={
                    "detection_method": detection_method,
                    "first_seen_filename": filename
                }
            )
            self.db.add(new_pattern)

        self.db.commit()

    def apply_learned_pattern(
        self,
        filename: str,
        property_id: int,
        document_type: str
    ) -> Optional[Dict]:
        """
        Try to apply a learned pattern to this filename.

        Returns:
            {
                "month": int,
                "year": int,
                "confidence": float,
                "pattern": str,
                "success_rate": float,
                "times_seen": int
            }
            or None if no pattern matches
        """
        pattern = self._extract_pattern(filename)
        if not pattern:
            return None

        # Find matching pattern
        learned = self.db.query(FilenamePeriodPattern).filter(
            FilenamePeriodPattern.filename_pattern == pattern,
            FilenamePeriodPattern.property_id == property_id,
            FilenamePeriodPattern.document_type == document_type,
            FilenamePeriodPattern.success_rate >= 70,  # Only use reliable patterns
            FilenamePeriodPattern.times_seen >= 2  # Must be seen at least twice
        ).order_by(
            FilenamePeriodPattern.success_rate.desc(),
            FilenamePeriodPattern.times_seen.desc()
        ).first()

        if learned:
            # Calculate confidence based on success rate and times seen
            confidence = min(learned.success_rate, 95)
            if learned.times_seen >= 10:
                confidence = min(confidence + 5, 99)

            return {
                "month": learned.detected_month,
                "year": learned.detected_year,
                "confidence": float(confidence),
                "pattern": learned.filename_pattern,
                "success_rate": float(learned.success_rate),
                "times_seen": learned.times_seen,
                "source": "learned_pattern"
            }

        return None

    def _extract_pattern(self, filename: str) -> Optional[str]:
        """
        Extract a reusable pattern from filename.

        Examples:
        - "Income_Statement_esp_Accrual-5.25-6.25.pdf" → "Income_Statement_*_Accrual-{M}.{YY}-{M}.{YY}.pdf"
        - "Cash_Flow_esp_Accrual-12.24-1.25.pdf" → "Cash_Flow_*_Accrual-{M}.{YY}-{M}.{YY}.pdf"
        - "RentRoll-1.25.pdf" → "RentRoll-{M}.{YY}.pdf"
        """
        # Replace property code with wildcard
        pattern = re.sub(r'_[A-Z]{3,10}\d{3}_', '_*_', filename, flags=re.IGNORECASE)

        # Replace period range with tokens
        pattern = re.sub(r'\d{1,2}\.\d{2}-\d{1,2}\.\d{2}', '{M}.{YY}-{M}.{YY}', pattern)

        # Replace single month-year
        pattern = re.sub(r'\d{1,2}\.\d{2,4}', '{M}.{YY}', pattern)
        pattern = re.sub(r'\d{1,2}/\d{2,4}', '{M}/{YY}', pattern)

        return pattern

    def _classify_pattern(self, pattern: str) -> str:
        """Classify pattern type."""
        if '{M}.{YY}-{M}.{YY}' in pattern or '{M}/{YY}-{M}/{YY}' in pattern:
            return 'period_range'
        elif '{M}.{YY}' in pattern or '{M}/{YY}' in pattern:
            return 'single_month'
        else:
            return 'unknown'
```

#### 3.3 Integration into Upload Flow

**Location:** `backend/app/services/document_service.py` around line 730

```python
# NEW: Try to apply learned pattern first
from app.services.filename_pattern_learning_service import FilenamePatternLearningService
learning_service = FilenamePatternLearningService(self.db)

learned_pattern = learning_service.apply_learned_pattern(
    filename=file.filename,
    property_id=property_obj.id,
    document_type=detected_type
)

if learned_pattern and learned_pattern["confidence"] >= 80:
    # Use learned pattern
    filename_month = learned_pattern["month"]
    detected_year = learned_pattern["year"]

    print(f"✅ Applied learned pattern: {learned_pattern['pattern']}")
    print(f"   Month: {filename_month}, Year: {detected_year}")
    print(f"   Confidence: {learned_pattern['confidence']}% (seen {learned_pattern['times_seen']} times, {learned_pattern['success_rate']}% success)")

    # Skip PDF content detection - trust the learned pattern
    skip_pdf_detection = True
else:
    # Use regular detection logic
    skip_pdf_detection = False

    # Detect period range
    period_range = range_detector.detect_period_range(file.filename or "")
    if period_range:
        filename_month, detected_year = range_detector.get_statement_period(period_range)
    else:
        filename_month = detector.detect_month_from_filename(file.filename or "", year)
```

**After successful upload (around line 1044):**

```python
# Learn from this upload
try:
    learning_service.learn_from_upload(
        filename=file.filename,
        detected_month=detected_month,
        detected_year=detected_year,
        property_id=property_obj.id,
        document_type=detected_type,
        detection_method='period_range' if is_period_range else 'filename',
        was_correct=None  # Will be updated by user feedback
    )
except Exception as e:
    print(f"⚠️  Failed to learn pattern: {e}")
```

---

### Phase 4: User Feedback Loop

Allow users to confirm or correct period detection, feeding back into the learning system.

#### 4.1 Add Correction API

```python
# backend/app/api/v1/documents.py

@router.post("/documents/uploads/{upload_id}/correct-period")
async def correct_upload_period(
    upload_id: int,
    correct_month: int,
    correct_year: int,
    db: Session = Depends(get_db)
):
    """
    User confirms or corrects the detected period for an upload.
    This feeds into the learning system.
    """
    upload = db.query(DocumentUpload).filter(DocumentUpload.id == upload_id).first()
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")

    # Get current period
    current_period = db.query(FinancialPeriod).filter(
        FinancialPeriod.id == upload.period_id
    ).first()

    was_correct = (
        current_period.period_month == correct_month and
        current_period.period_year == correct_year
    )

    # Update learning system
    from app.services.filename_pattern_learning_service import FilenamePatternLearningService
    learning_service = FilenamePatternLearningService(db)

    learning_service.learn_from_upload(
        filename=upload.file_name,
        detected_month=correct_month,
        detected_year=correct_year,
        property_id=upload.property_id,
        document_type=upload.document_type,
        detection_method='user_correction',
        was_correct=was_correct
    )

    if not was_correct:
        # Period was wrong - need to move upload to correct period
        correct_period = get_or_create_period(upload.property_id, correct_year, correct_month)

        # Move upload
        upload.period_id = correct_period.id
        upload.notes = f"Period corrected by user from {current_period.period_month}/{current_period.period_year} to {correct_month}/{correct_year}"
        db.commit()

    return {"success": True, "was_correct": was_correct}
```

#### 4.2 UI for Period Correction

Add a "Correct Period" button in the upload list UI that shows:
- Detected period
- Option to select correct period
- Submits correction to API

---

## Implementation Priority

### Phase 1: IMMEDIATE (Fix Current Issue) - 2 hours
1. ✅ Create `PeriodRangeDetector` class
2. ✅ Integrate into `document_service.py`
3. ✅ Test with problem files
4. ✅ Deploy

**Expected outcome:** Filenames like "5.25-6.25" will be correctly parsed as "June 2025" (ending period)

### Phase 2: URGENT (Fix PDF Detector) - 3 hours
1. 🔍 Debug extraction engine
2. 🔧 Fix "Month 3" bug
3. ✅ Add confidence calibration
4. ✅ Test and deploy

**Expected outcome:** PDF content detector stops incorrectly detecting "Month 3"

### Phase 3: HIGH PRIORITY (Self-Learning) - 4 hours
1. ✅ Create database table
2. ✅ Implement `FilenamePatternLearningService`
3. ✅ Integrate into upload flow
4. ✅ Test pattern learning
5. ✅ Deploy

**Expected outcome:** System learns from ESP001 patterns and auto-applies to future uploads

### Phase 4: MEDIUM PRIORITY (User Feedback) - 2 hours
1. ✅ Add correction API endpoint
2. ✅ Add UI for period correction
3. ✅ Wire up feedback loop

**Expected outcome:** Users can correct wrong detections, system learns from corrections

---

## Immediate Action Required

### 1. Reprocess Failed Uploads

The 16 skipped uploads (591-596, 603-608) need to be reprocessed with the period range detection fix.

**Option A: Delete duplicates and re-upload**
```sql
-- Delete the wrong uploads (stored as March)
DELETE FROM document_uploads WHERE id IN (
    SELECT id FROM document_uploads
    WHERE property_id = 1
    AND period_id = 28  -- March 2025
    AND document_type IN ('income_statement', 'cash_flow')
    AND file_name LIKE '%25-%.25%'
);
```

Then re-upload all files.

**Option B: Manual correction**

Use the correction API for each upload once implemented.

### 2. Verify PDF Detector

Extract one of the problem PDFs and examine what text is causing "Month 3" detection:

```python
# Debug script
from app.utils.extraction_engine import MultiEngineExtractor

extractor = MultiEngineExtractor()
with open('/path/to/Income_Statement_esp_Accrual-5.25-6.25.pdf', 'rb') as f:
    pdf_content = f.read()

detection = extractor.detect_year_and_period(pdf_content)
print(f"Detected: {detection}")

# Also print the extracted text to see what it's matching
text = extractor.extract_text(pdf_content)
print(f"PDF Text (first 1000 chars):")
print(text[:1000])
```

---

## Testing Plan

### Test Case 1: Period Range Detection

```python
def test_period_range_detection():
    detector = PeriodRangeDetector()

    # Test MM.YY-MM.YY format
    result = detector.detect_period_range("Income_Statement_esp_Accrual-5.25-6.25.pdf")
    assert result["end_month"] == 6
    assert result["end_year"] == 2025

    # Test year rollover
    result = detector.detect_period_range("Income_Statement_esp_Accrual-12.24-1.25.pdf")
    assert result["end_month"] == 1
    assert result["end_year"] == 2025

    # Test no match
    result = detector.detect_period_range("RentRoll-6.25.pdf")
    assert result is None
```

### Test Case 2: Pattern Learning

```python
def test_pattern_learning():
    service = FilenamePatternLearningService(db)

    # Learn pattern
    service.learn_from_upload(
        filename="Income_Statement_esp_Accrual-5.25-6.25.pdf",
        detected_month=6,
        detected_year=2025,
        property_id=1,
        document_type="income_statement",
        detection_method="period_range",
        was_correct=True
    )

    # Apply pattern
    result = service.apply_learned_pattern(
        filename="Income_Statement_esp_Accrual-7.25-8.25.pdf",
        property_id=1,
        document_type="income_statement"
    )

    assert result["month"] == 8  # Should detect ending period
    assert result["confidence"] >= 70
```

---

## Success Metrics

### Immediate (Phase 1 & 2)
- ✅ 0 month mismatch warnings for period range filenames
- ✅ 100% of period range files uploaded successfully
- ✅ Correct period assigned (ending period of range)

### Short-term (Phase 3)
- ✅ 90%+ of subsequent uploads use learned patterns
- ✅ Pattern learning database populated with 10+ patterns
- ✅ Confidence scores calibrated correctly

### Long-term (Phase 4)
- ✅ User corrections feed back into system
- ✅ System accuracy improves over time
- ✅ Fewer manual interventions needed

---

## Conclusion

This is a **critical bug** that's blocking bulk uploads. The solution involves:

1. **Fix period range detection** (filename parsing)
2. **Fix PDF content detector** (extraction engine bug)
3. **Build self-learning system** (pattern recognition)
4. **Add user feedback loop** (continuous improvement)

With these enhancements, the system will:
- ✅ Correctly handle period range filenames
- ✅ Learn from patterns and apply to future uploads
- ✅ Improve accuracy over time through user feedback
- ✅ Eliminate month mismatch warnings

**Estimated Total Effort:** 11 hours (1-2 days)
**Priority:** HIGH - Blocks production use
**Impact:** Enables fully automated bulk uploads

---

**Document Created:** December 25, 2025
**Status:** Ready for Implementation
