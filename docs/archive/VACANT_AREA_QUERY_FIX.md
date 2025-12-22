# Vacant Area Query Fix

## Issue
Query "How much is the area vacant for property ESP" was returning "Error: No data found for query" even though:
- Rent roll data exists (30,910 sq ft vacant area for ESP001)
- Property code matching works (ESP → ESP001)
- Data is in the database

## Root Cause
The keyword matching logic only looked for exact phrases like "vacant area" but the user's question was "area vacant" (words in different order). The system didn't recognize this as a rent roll query.

## Fix Applied

**File**: `backend/app/services/nlq_service.py`

### 1. Enhanced Keyword Detection (Line ~399)
Changed from simple phrase matching to also detect word combinations:
```python
# OLD:
rent_roll_keywords = ['rent roll', 'occupied area', 'vacant area', 'lease area', 'total area']
if any(keyword in question.lower() for keyword in rent_roll_keywords):

# NEW:
rent_roll_keywords = ['rent roll', 'occupied area', 'vacant area', 'lease area', 'total area']
rent_roll_word_combos = [
    ('area', 'vacant'), ('vacant', 'area'), ('area', 'occupied'), ('occupied', 'area'),
    ('vacant', 'space'), ('empty', 'area'), ('unoccupied', 'area')
]
is_rent_roll_query = (
    any(keyword in question_lower for keyword in rent_roll_keywords) or
    any(word1 in question_lower and word2 in question_lower for word1, word2 in rent_roll_word_combos)
)
```

### 2. Enhanced Answer Generation (Line ~1429)
Applied the same logic to the answer generation function so it uses the specialized rent roll answer formatter.

## How It Works Now

1. User asks: "How much is the area vacant for property ESP"
2. System detects both "area" and "vacant" in the question
3. Routes to `_query_rent_roll_metrics()` function
4. Finds ESP001 property using partial code matching
5. Queries rent roll data and calculates:
   - Total area: 270,105 sq ft
   - Vacant area: 30,910 sq ft
   - Occupancy rate: ~88.6%
6. Returns formatted answer with actual data

## Supported Query Variations

Now works with:
- "How much is the area vacant"
- "What is the vacant area"
- "Show me vacant space"
- "How much empty area"
- "Unoccupied area"
- "Vacant area" (original phrase)

## Testing

Try these queries:
- "How much is the area vacant for property ESP"
- "What is the vacant area for Eastern Shore Plaza"
- "Show me occupied area for ESP"
- "Total area for property ESP"

## Status
✅ **Fixed** - Enhanced keyword matching for rent roll queries
✅ **Backend** - Restarted with fix
✅ **Data Verified** - ESP001 has 30,910 sq ft vacant area

