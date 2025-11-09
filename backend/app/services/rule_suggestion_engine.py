"""
Rule Suggestion Engine
Analyzes correction patterns and generates extraction rule suggestions.
"""

from typing import List, Dict, Any
from collections import Counter
import re


class RuleSuggestionEngine:
    """Generate extraction rule suggestions from correction patterns."""
    
    def analyze_patterns(self, corrections: List[Dict]) -> List[Dict]:
        """Analyze correction patterns to identify recurring issues."""
        patterns = []
        
        # Group by field name
        field_corrections = {}
        for corr in corrections:
            field = corr.get("field_name")
            if field not in field_corrections:
                field_corrections[field] = []
            field_corrections[field].append(corr)
        
        # Identify repeated corrections
        for field, corr_list in field_corrections.items():
            if len(corr_list) >= 3:  # At least 3 corrections
                suggestion = self._generate_suggestion(field, corr_list)
                if suggestion:
                    patterns.append(suggestion)
        
        return patterns
    
    def _generate_suggestion(
        self,
        field: str,
        corrections: List[Dict]
    ) -> Optional[Dict]:
        """Generate regex or template suggestion."""
        originals = [c["original_value"] for c in corrections]
        corrected = [c["corrected_value"] for c in corrections]
        
        # Simple pattern detection
        if all(self._is_number(o) for o in originals):
            return {
                "field": field,
                "type": "numeric_format",
                "suggestion": "Apply number normalization",
                "confidence": 0.8
            }
        
        return None
    
    def _is_number(self, value: str) -> bool:
        """Check if value is numeric."""
        try:
            float(value.replace(",", "").replace("$", ""))
            return True
        except:
            return False

