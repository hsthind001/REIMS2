"""
MCP Learning Service

Integrates with task-master-ai MCP server for issue tracking and resolution.
"""

import logging
import subprocess
import json
import os
from typing import Dict, Optional, List, Any
from sqlalchemy.orm import Session

from app.models.issue_knowledge_base import IssueKnowledgeBase

logger = logging.getLogger(__name__)


class MCPLearningService:
    """Service for integrating with task-master-ai MCP server"""
    
    def __init__(self, db: Session, project_root: Optional[str] = None):
        self.db = db
        self.project_root = project_root or os.getenv("PROJECT_ROOT", "/home/hsthind/Documents/GitHub/REIMS2")
    
    def create_issue_task(
        self,
        issue_kb_id: int,
        tag: str = "self-learning"
    ) -> Optional[str]:
        """
        Create a task in task-master-ai for an unresolved issue.
        
        Args:
            issue_kb_id: Issue knowledge base ID
            tag: Tag context for the task
        
        Returns:
            str: Task ID if created, None otherwise
        """
        try:
            issue = self.db.query(IssueKnowledgeBase).filter(
                IssueKnowledgeBase.id == issue_kb_id
            ).first()
            
            if not issue:
                return None
            
            # Skip if already has a task
            if issue.mcp_task_id:
                return issue.mcp_task_id
            
            # Create task description
            task_description = f"""
Issue Type: {issue.issue_type}
Category: {issue.issue_category}
Occurrences: {issue.occurrence_count}
Last Occurred: {issue.last_occurred_at}

Error Pattern: {issue.error_message_pattern or 'N/A'}

Context: {json.dumps(issue.context or {}, indent=2)}

This issue has occurred {issue.occurrence_count} times and needs to be resolved.
Please investigate and implement a fix.
"""
            
            # Use task-master CLI to create task
            cmd = [
                "npx", "task-master-ai", "add-task",
                "--prompt", task_description.strip(),
                "--priority", "high",
                "--tag", tag
            ]
            
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                # Parse task ID from output (task-master returns JSON or task ID)
                try:
                    output = result.stdout.strip()
                    # Try to extract task ID from output
                    # Format may vary, but typically includes task ID
                    if "Task" in output and "created" in output.lower():
                        # Extract ID from output (this is a simplified parser)
                        # In practice, task-master may return structured JSON
                        lines = output.split('\n')
                        task_id = None
                        for line in lines:
                            if "ID:" in line or "id:" in line:
                                parts = line.split()
                                for i, part in enumerate(parts):
                                    if part.lower() in ["id:", "task"] and i + 1 < len(parts):
                                        task_id = parts[i + 1]
                                        break
                                if task_id:
                                    break
                        
                        if task_id:
                            # Update issue with task ID
                            issue.mcp_task_id = task_id
                            issue.mcp_task_status = "pending"
                            self.db.commit()
                            
                            logger.info(f"Created MCP task {task_id} for issue {issue_kb_id}")
                            return task_id
                except Exception as e:
                    logger.warning(f"Could not parse task ID from output: {e}")
            
            logger.warning(f"Failed to create MCP task for issue {issue_kb_id}: {result.stderr}")
            return None
            
        except subprocess.TimeoutExpired:
            logger.error(f"Timeout creating MCP task for issue {issue_kb_id}")
            return None
        except Exception as e:
            logger.error(f"Error creating MCP task: {e}")
            return None
    
    def update_task_on_resolution(
        self,
        issue_kb_id: int,
        fix_details: str
    ) -> bool:
        """
        Update MCP task when issue is resolved.
        
        Args:
            issue_kb_id: Issue knowledge base ID
            fix_details: Details of the fix
        
        Returns:
            bool: True if successful
        """
        try:
            issue = self.db.query(IssueKnowledgeBase).filter(
                IssueKnowledgeBase.id == issue_kb_id
            ).first()
            
            if not issue or not issue.mcp_task_id:
                return False
            
            # Update task with fix details
            update_prompt = f"""
Issue resolved!

Fix Applied: {issue.fix_applied or 'N/A'}
Fix Location: {issue.fix_code_location or 'N/A'}

Fix Details:
{fix_details}

The issue has been resolved and prevention rules have been created to prevent recurrence.
"""
            
            # Use task-master CLI to update task
            cmd = [
                "npx", "task-master-ai", "update-subtask",
                "--id", issue.mcp_task_id,
                "--prompt", update_prompt.strip()
            ]
            
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                # Mark task as done
                cmd = [
                    "npx", "task-master-ai", "set-status",
                    "--id", issue.mcp_task_id,
                    "--status", "done"
                ]
                
                result = subprocess.run(
                    cmd,
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0:
                    issue.mcp_task_status = "done"
                    self.db.commit()
                    logger.info(f"Updated MCP task {issue.mcp_task_id} for issue {issue_kb_id}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error updating MCP task: {e}")
            return False
    
    def sync_learned_fixes(
        self,
        tag: str = "self-learning"
    ) -> Dict[str, Any]:
        """
        Sync learned fixes from resolved issues back to knowledge base.
        
        Args:
            tag: Tag context to check
        
        Returns:
            Dict with sync results
        """
        try:
            # Get resolved issues with MCP tasks
            resolved_issues = self.db.query(IssueKnowledgeBase).filter(
                and_(
                    IssueKnowledgeBase.status == "resolved",
                    IssueKnowledgeBase.mcp_task_id.isnot(None),
                    IssueKnowledgeBase.mcp_task_status != "done"
                )
            ).all()
            
            synced_count = 0
            for issue in resolved_issues:
                if self.update_task_on_resolution(issue.id, issue.fix_applied or ""):
                    synced_count += 1
            
            return {
                "synced_count": synced_count,
                "total_resolved": len(resolved_issues)
            }
            
        except Exception as e:
            logger.error(f"Error syncing learned fixes: {e}")
            return {"synced_count": 0, "total_resolved": 0}
    
    def get_active_issues(
        self,
        tag: str = "self-learning"
    ) -> List[Dict[str, Any]]:
        """
        Get active issues from MCP server.
        
        Args:
            tag: Tag context to query
        
        Returns:
            List of active issue tasks
        """
        try:
            # Use task-master CLI to get tasks
            cmd = [
                "npx", "task-master-ai", "list",
                "--tag", tag,
                "--status", "pending,in-progress"
            ]
            
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                # Parse task list from output
                # This is simplified - in practice, task-master may return JSON
                tasks = []
                lines = result.stdout.split('\n')
                for line in lines:
                    if line.strip() and not line.startswith('#'):
                        tasks.append({"description": line.strip()})
                return tasks
            
            return []
            
        except Exception as e:
            logger.error(f"Error getting active issues: {e}")
            return []
    
    def create_tasks_for_critical_issues(
        self,
        min_occurrences: int = 5,
        tag: str = "self-learning"
    ) -> int:
        """
        Create MCP tasks for critical unresolved issues.
        
        Args:
            min_occurrences: Minimum occurrences to consider critical
            tag: Tag context for tasks
        
        Returns:
            int: Number of tasks created
        """
        try:
            # Get active issues with high occurrence count
            critical_issues = self.db.query(IssueKnowledgeBase).filter(
                and_(
                    IssueKnowledgeBase.status == "active",
                    IssueKnowledgeBase.occurrence_count >= min_occurrences,
                    IssueKnowledgeBase.mcp_task_id.is_(None)
                )
            ).all()
            
            created_count = 0
            for issue in critical_issues:
                task_id = self.create_issue_task(issue.id, tag)
                if task_id:
                    created_count += 1
            
            logger.info(f"Created {created_count} MCP tasks for critical issues")
            return created_count
            
        except Exception as e:
            logger.error(f"Error creating tasks for critical issues: {e}")
            return 0

