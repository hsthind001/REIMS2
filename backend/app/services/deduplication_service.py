"""
Deduplication Service - Future-Proof Duplicate Prevention

Intelligent deduplication service that prevents unique constraint violations
by deduplicating records before database insertion. Works with any document type
and constraint definition.

This service ensures the system never encounters duplicate key constraint errors
by intelligently selecting the best record when duplicates are found.
"""

from typing import List, Dict, Any, Optional, Tuple
from decimal import Decimal


class DeduplicationService:
    """
    Generic deduplication service for financial document extraction.
    
    Prevents unique constraint violations by intelligently deduplicating records
    based on constraint columns before database insertion.
    """
    
    # Constraint definitions for each document type
    DOCUMENT_TYPE_CONSTRAINTS = {
        'balance_sheet': ['account_code'],
        'income_statement': ['account_code', 'account_name'],
        'cash_flow': ['account_code', 'account_name', 'line_number']
    }
    
    def __init__(self):
        """Initialize the deduplication service"""
        pass
    
    def deduplicate_items(
        self,
        items: List[Dict],
        constraint_columns: List[str],
        selection_strategy: str = 'confidence',
        document_type: Optional[str] = None,
        is_total_or_subtotal: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Intelligently deduplicate items based on constraint columns.
        
        Args:
            items: List of item dictionaries to deduplicate
            constraint_columns: List of column names that form the unique constraint
                               e.g., ['account_code'] or ['account_code', 'account_name']
            selection_strategy: Strategy for selecting best record when duplicates found
                              - 'confidence': Prefer higher confidence (for detail lines)
                              - 'amount': Prefer higher absolute amount (for totals/subtotals)
                              - 'completeness': Prefer record with more non-null fields
            document_type: Optional document type for logging context
            is_total_or_subtotal: Optional function to determine if item is total/subtotal
                                 If provided, uses 'amount' strategy for totals, 'confidence' for details
        
        Returns:
            Dict with:
            - 'deduplicated_items': List of deduplicated items
            - 'statistics': Dict with counts and metrics
            - 'duplicate_details': List of duplicate detection details for logging
        """
        if not items:
            return {
                'deduplicated_items': [],
                'statistics': {
                    'total_items': 0,
                    'duplicates_found': 0,
                    'duplicates_removed': 0,
                    'final_count': 0
                },
                'duplicate_details': []
            }
        
        # Track items by constraint key
        seen_items = {}  # key -> item
        duplicate_details = []
        
        for idx, item in enumerate(items):
            # Generate constraint key from specified columns
            constraint_key = self._generate_constraint_key(item, constraint_columns)
            
            # Skip if key cannot be generated (missing required fields)
            if constraint_key is None:
                continue
            
            # Check if we've seen this key before
            if constraint_key in seen_items:
                existing_item = seen_items[constraint_key]
                
                # Determine selection strategy
                strategy = self._determine_selection_strategy(
                    item,
                    existing_item,
                    selection_strategy,
                    is_total_or_subtotal
                )
                
                # Select best record
                should_replace, reason = self._select_best_record(
                    item,
                    existing_item,
                    strategy
                )
                
                if should_replace:
                    duplicate_details.append({
                        'constraint_key': constraint_key,
                        'action': 'replaced',
                        'reason': reason,
                        'existing_confidence': self._get_confidence(existing_item),
                        'new_confidence': self._get_confidence(item),
                        'existing_amount': self._get_amount(existing_item),
                        'new_amount': self._get_amount(item),
                        'item_index': idx
                    })
                    seen_items[constraint_key] = item
                else:
                    duplicate_details.append({
                        'constraint_key': constraint_key,
                        'action': 'kept_existing',
                        'reason': reason,
                        'existing_confidence': self._get_confidence(existing_item),
                        'new_confidence': self._get_confidence(item),
                        'existing_amount': self._get_amount(existing_item),
                        'new_amount': self._get_amount(item),
                        'item_index': idx
                    })
            else:
                # First occurrence of this constraint key
                seen_items[constraint_key] = item
        
        deduplicated_items = list(seen_items.values())
        duplicates_removed = len(items) - len(deduplicated_items)
        
        # Log duplicate detection if any found
        if duplicates_removed > 0:
            doc_type_str = f" for {document_type}" if document_type else ""
            print(f"⚠️  Found {duplicates_removed} duplicate(s){doc_type_str} - deduplicated to {len(deduplicated_items)} unique records")
            for detail in duplicate_details:
                print(f"   - {detail['action']}: {detail['constraint_key']} ({detail['reason']})")
        
        return {
            'deduplicated_items': deduplicated_items,
            'statistics': {
                'total_items': len(items),
                'duplicates_found': duplicates_removed,
                'duplicates_removed': duplicates_removed,
                'final_count': len(deduplicated_items)
            },
            'duplicate_details': duplicate_details
        }
    
    def _generate_constraint_key(self, item: Dict, constraint_columns: List[str]) -> Optional[str]:
        """
        Generate a unique key from item based on constraint columns.
        
        Returns None if any required column is missing or empty.
        """
        key_parts = []
        
        for col in constraint_columns:
            # Try matched_* first, then regular field
            value = item.get(f"matched_{col}") or item.get(col, "")
            
            # Handle empty strings and None
            if not value or (isinstance(value, str) and not value.strip()):
                # For account_code, allow "UNMATCHED" as valid
                if col == 'account_code' and value == "UNMATCHED":
                    key_parts.append("UNMATCHED")
                else:
                    return None  # Missing required field
            else:
                key_parts.append(str(value).strip())
        
        return "|||".join(key_parts)  # Use ||| as separator (unlikely to appear in data)
    
    def _determine_selection_strategy(
        self,
        item: Dict,
        existing_item: Dict,
        default_strategy: str,
        is_total_or_subtotal: Optional[callable]
    ) -> str:
        """
        Determine which selection strategy to use based on item type.
        """
        if is_total_or_subtotal:
            if is_total_or_subtotal(item) or is_total_or_subtotal(existing_item):
                return 'amount'  # Totals/subtotals: prefer higher amount
            else:
                return 'confidence'  # Detail lines: prefer higher confidence
        
        return default_strategy
    
    def _select_best_record(
        self,
        item: Dict,
        existing_item: Dict,
        strategy: str
    ) -> Tuple[bool, str]:
        """
        Select the best record between item and existing_item.
        
        Returns:
            (should_replace, reason) tuple
        """
        if strategy == 'confidence':
            item_confidence = self._get_confidence(item)
            existing_confidence = self._get_confidence(existing_item)
            
            if item_confidence > existing_confidence:
                return True, f"higher confidence ({existing_confidence:.1f} → {item_confidence:.1f})"
            elif item_confidence == existing_confidence:
                # Tie-breaker: higher amount
                item_amount = abs(self._get_amount(item))
                existing_amount = abs(self._get_amount(existing_item))
                if item_amount > existing_amount:
                    return True, f"same confidence, higher amount ({existing_amount} → {item_amount})"
                else:
                    return False, f"same confidence, same/lower amount"
            else:
                return False, f"lower confidence ({item_confidence:.1f} vs {existing_confidence:.1f})"
        
        elif strategy == 'amount':
            item_amount = abs(self._get_amount(item))
            existing_amount = abs(self._get_amount(existing_item))
            
            if item_amount > existing_amount:
                return True, f"higher amount ({existing_amount} → {item_amount})"
            elif item_amount == existing_amount:
                # Tie-breaker: higher confidence
                item_confidence = self._get_confidence(item)
                existing_confidence = self._get_confidence(existing_item)
                if item_confidence > existing_confidence:
                    return True, f"same amount, higher confidence ({existing_confidence:.1f} → {item_confidence:.1f})"
                else:
                    return False, f"same amount, same/lower confidence"
            else:
                return False, f"lower amount ({item_amount} vs {existing_amount})"
        
        elif strategy == 'completeness':
            item_completeness = self._calculate_completeness(item)
            existing_completeness = self._calculate_completeness(existing_item)
            
            if item_completeness > existing_completeness:
                return True, f"more complete ({existing_completeness} → {item_completeness} fields)"
            else:
                return False, f"less/same completeness ({item_completeness} vs {existing_completeness} fields)"
        
        # Default: keep existing
        return False, "default strategy"
    
    def _get_confidence(self, item: Dict) -> float:
        """Extract confidence score from item"""
        # Try various confidence fields
        confidence = (
            item.get("confidence") or
            item.get("extraction_confidence") or
            item.get("match_confidence") or
            0.0
        )
        return float(confidence) if confidence is not None else 0.0
    
    def _get_amount(self, item: Dict) -> float:
        """Extract amount from item"""
        # Try various amount fields
        amount = (
            item.get("amount") or
            item.get("period_amount") or
            item.get("ytd_amount") or
            0.0
        )
        return float(amount) if amount is not None else 0.0
    
    def _calculate_completeness(self, item: Dict) -> int:
        """Calculate number of non-null, non-empty fields"""
        count = 0
        important_fields = [
            'account_code', 'account_name', 'amount', 'period_amount',
            'extraction_confidence', 'match_confidence', 'line_number',
            'page_number', 'extraction_x0', 'extraction_y0'
        ]
        
        for field in important_fields:
            value = item.get(field) or item.get(f"matched_{field}")
            if value is not None and value != "":
                count += 1
        
        return count
    
    def validate_no_duplicates(
        self,
        items: List[Dict],
        constraint_columns: List[str],
        context: str = "insertion"
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate that items have no duplicate constraint keys.
        
        This is a safety check that should never fail if deduplication worked correctly.
        
        Args:
            items: List of items to validate
            constraint_columns: Constraint column names
            context: Context string for error messages
        
        Returns:
            (is_valid, error_message) tuple
        """
        seen_keys = set()
        
        for idx, item in enumerate(items):
            constraint_key = self._generate_constraint_key(item, constraint_columns)
            
            if constraint_key is None:
                continue  # Skip items with missing fields
            
            if constraint_key in seen_keys:
                return False, (
                    f"Duplicate constraint key detected in {context} at index {idx}: "
                    f"{constraint_key} (columns: {', '.join(constraint_columns)}). "
                    f"This should not happen after deduplication!"
                )
            
            seen_keys.add(constraint_key)
        
        return True, None


# Singleton instance
_deduplication_service = None

def get_deduplication_service() -> DeduplicationService:
    """Get singleton instance of DeduplicationService"""
    global _deduplication_service
    if _deduplication_service is None:
        _deduplication_service = DeduplicationService()
    return _deduplication_service

