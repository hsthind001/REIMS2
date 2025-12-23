"""
Pre-Flight Check Service

Checks for known issues before operations and applies preventive fixes.
"""

import logging
import re
from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.issue_knowledge_base import IssueKnowledgeBase
from app.models.prevention_rule import PreventionRule

logger = logging.getLogger(__name__)


class PreflightCheckService:
    """Service for pre-flight checks and preventive fixes"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def check_before_upload(
        self,
        document_type: Optional[str] = None,
        property_code: Optional[str] = None,
        filename: Optional[str] = None,
        file_size: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Check for known issues before document upload.
        
        Args:
            document_type: Document type
            property_code: Property code
            filename: Filename
            file_size: File size in bytes
            context: Additional context
        
        Returns:
            Dict with:
                - warnings: List of warning messages
                - auto_fixes: List of auto-fixes to apply
                - should_proceed: Whether to proceed with upload
        """
        result = {
            "warnings": [],
            "auto_fixes": [],
            "should_proceed": True,
            "prevention_rules_applied": []
        }
        
        try:
            # Get active prevention rules for upload operations
            rules = self._get_applicable_rules(
                operation="upload",
                document_type=document_type,
                property_code=property_code,
                file_size=file_size,
                context=context
            )
            
            for rule in rules:
                if self._rule_condition_matches(rule.rule_condition, {
                    "document_type": document_type,
                    "property_code": property_code,
                    "filename": filename,
                    "file_size": file_size,
                    **(context or {})
                }):
                    # Apply rule action
                    action_result = self._apply_rule_action(rule, {
                        "document_type": document_type,
                        "property_code": property_code,
                        "filename": filename,
                        "file_size": file_size,
                        **(context or {})
                    })
                    
                    if action_result.get("warning"):
                        result["warnings"].append(action_result["warning"])
                    
                    if action_result.get("auto_fix"):
                        result["auto_fixes"].append(action_result["auto_fix"])
                    
                    if action_result.get("block_operation"):
                        result["should_proceed"] = False
                    
                    result["prevention_rules_applied"].append({
                        "rule_id": rule.id,
                        "rule_type": rule.rule_type,
                        "action": action_result
                    })
                    
                    # Update rule statistics
                    rule.success_count += 1
                    rule.last_applied_at = datetime.now()
            
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Error in pre-flight check: {e}")
            self.db.rollback()
        
        return result
    
    def check_before_extraction(
        self,
        upload_id: int,
        document_type: Optional[str] = None,
        extraction_engine: Optional[str] = None,
        file_size: Optional[int] = None,
        page_count: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Check for known issues before extraction.
        
        Args:
            upload_id: Document upload ID
            document_type: Document type
            extraction_engine: Extraction engine to use
            file_size: File size in bytes
            page_count: Number of pages
            context: Additional context
        
        Returns:
            Dict with warnings, auto_fixes, and recommended extraction strategy
        """
        result = {
            "warnings": [],
            "auto_fixes": [],
            "recommended_engine": extraction_engine,
            "recommended_strategy": "auto",
            "should_proceed": True,
            "prevention_rules_applied": []
        }
        
        try:
            # Get active prevention rules for extraction operations
            rules = self._get_applicable_rules(
                operation="extraction",
                document_type=document_type,
                extraction_engine=extraction_engine,
                file_size=file_size,
                page_count=page_count,
                context=context
            )
            
            for rule in rules:
                if self._rule_condition_matches(rule.rule_condition, {
                    "document_type": document_type,
                    "extraction_engine": extraction_engine,
                    "file_size": file_size,
                    "page_count": page_count,
                    **(context or {})
                }):
                    action_result = self._apply_rule_action(rule, {
                        "document_type": document_type,
                        "extraction_engine": extraction_engine,
                        "file_size": file_size,
                        "page_count": page_count,
                        **(context or {})
                    })
                    
                    if action_result.get("warning"):
                        result["warnings"].append(action_result["warning"])
                    
                    if action_result.get("auto_fix"):
                        result["auto_fixes"].append(action_result["auto_fix"])
                    
                    # Update recommended engine/strategy
                    if action_result.get("recommended_engine"):
                        result["recommended_engine"] = action_result["recommended_engine"]
                    if action_result.get("recommended_strategy"):
                        result["recommended_strategy"] = action_result["recommended_strategy"]
                    
                    if action_result.get("block_operation"):
                        result["should_proceed"] = False
                    
                    result["prevention_rules_applied"].append({
                        "rule_id": rule.id,
                        "rule_type": rule.rule_type,
                        "action": action_result
                    })
                    
                    rule.success_count += 1
                    rule.last_applied_at = datetime.now()
            
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Error in extraction pre-flight check: {e}")
            self.db.rollback()
        
        return result
    
    def apply_preventive_fixes(
        self,
        operation: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Apply preventive fixes based on learned patterns.
        
        Args:
            operation: Operation type ('upload', 'extraction', 'validation')
            context: Operation context
        
        Returns:
            Dict with applied fixes and modified context
        """
        result = {
            "fixes_applied": [],
            "modified_context": context.copy()
        }
        
        try:
            rules = self._get_applicable_rules(
                operation=operation,
                **context
            )
            
            for rule in rules:
                if rule.rule_type == "auto_fix":
                    if self._rule_condition_matches(rule.rule_condition, context):
                        fix_result = self._apply_auto_fix(rule.rule_action, context)
                        if fix_result.get("success"):
                            result["fixes_applied"].append({
                                "rule_id": rule.id,
                                "fix": fix_result
                            })
                            result["modified_context"].update(fix_result.get("modified_context", {}))
                            
                            rule.success_count += 1
                            rule.last_applied_at = datetime.now()
            
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Error applying preventive fixes: {e}")
            self.db.rollback()
        
        return result
    
    def get_warnings(
        self,
        operation: str,
        context: Dict[str, Any]
    ) -> List[str]:
        """
        Get warnings for potential issues.
        
        Args:
            operation: Operation type
            context: Operation context
        
        Returns:
            List of warning messages
        """
        warnings = []
        
        try:
            rules = self._get_applicable_rules(operation=operation, **context)
            
            for rule in rules:
                if rule.rule_type == "warning":
                    if self._rule_condition_matches(rule.rule_condition, context):
                        action = rule.rule_action
                        if action.get("warning_message"):
                            warnings.append(action["warning_message"])
            
        except Exception as e:
            logger.error(f"Error getting warnings: {e}")
        
        return warnings
    
    def _get_applicable_rules(
        self,
        operation: str,
        **kwargs
    ) -> List[PreventionRule]:
        """Get applicable prevention rules for an operation"""
        try:
            # Get active rules
            query = self.db.query(PreventionRule).join(IssueKnowledgeBase).filter(
                and_(
                    PreventionRule.is_active == True,
                    IssueKnowledgeBase.status == 'active'
                )
            )
            
            # Order by priority (higher first)
            rules = query.order_by(PreventionRule.priority.desc()).all()
            
            return rules
            
        except Exception as e:
            logger.error(f"Error getting applicable rules: {e}")
            return []
    
    def _rule_condition_matches(
        self,
        condition: Dict[str, Any],
        context: Dict[str, Any]
    ) -> bool:
        """Check if rule condition matches context"""
        if not condition:
            return True
        
        # Check document type
        if 'document_type' in condition:
            if context.get('document_type') != condition['document_type']:
                return False
        
        # Check property code pattern
        if 'property_code_pattern' in condition:
            property_code = context.get('property_code', '')
            if not re.search(condition['property_code_pattern'], property_code, re.IGNORECASE):
                return False
        
        # Check file size range
        if 'file_size_min' in condition or 'file_size_max' in condition:
            file_size = context.get('file_size', 0)
            if 'file_size_min' in condition and file_size < condition['file_size_min']:
                return False
            if 'file_size_max' in condition and file_size > condition['file_size_max']:
                return False
        
        # Check extraction engine
        if 'extraction_engine' in condition:
            if context.get('extraction_engine') != condition['extraction_engine']:
                return False
        
        # Check keywords
        if 'has_keywords' in condition:
            text = (context.get('filename', '') + ' ' + str(context.get('context', ''))).lower()
            keywords = condition['has_keywords']
            if not any(keyword.lower() in text for keyword in keywords):
                return False
        
        return True
    
    def _apply_rule_action(
        self,
        rule: PreventionRule,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply a rule action"""
        action = rule.rule_action
        action_type = action.get("action_type")
        
        result = {}
        
        if action_type == "skip_validation":
            result["auto_fix"] = {
                "type": "skip_validation",
                "validation_rule": action.get("validation_rule")
            }
        
        elif action_type == "auto_fix":
            fix_result = self._apply_auto_fix(action, context)
            result.update(fix_result)
        
        elif action_type == "warning":
            result["warning"] = action.get("warning_message", "Potential issue detected")
        
        elif action_type == "block":
            result["block_operation"] = True
            result["reason"] = action.get("reason", "Operation blocked by prevention rule")
        
        elif action_type == "use_extraction_strategy":
            result["recommended_strategy"] = action.get("strategy", "auto")
            result["recommended_engine"] = action.get("engine")
        
        return result
    
    def _apply_auto_fix(
        self,
        action: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply an auto-fix"""
        fix_method = action.get("fix_method")
        result = {"success": False, "modified_context": {}}
        
        if fix_method == "use_statement_date":
            # Auto-fix: Use statement date for period detection
            result["success"] = True
            result["modified_context"]["use_statement_date"] = True
            result["modified_context"]["priority"] = action.get("parameters", {}).get("priority", "statement_date")
        
        elif fix_method == "skip_validation":
            # Auto-fix: Skip specific validation
            validation_rule = action.get("validation_rule")
            result["success"] = True
            result["modified_context"]["skip_validations"] = result["modified_context"].get("skip_validations", [])
            result["modified_context"]["skip_validations"].append(validation_rule)
        
        elif fix_method == "use_fast_engine":
            # Auto-fix: Use faster extraction engine for large files
            result["success"] = True
            result["modified_context"]["extraction_engine"] = "fast"
            result["modified_context"]["extraction_strategy"] = "fast"
        
        return result

