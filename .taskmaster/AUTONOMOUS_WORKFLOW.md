# Autonomous Workflow Guide - Task-Master-AI

## Overview

This guide describes how to use task-master-ai for autonomous task management with minimal user input, leveraging the optimized configuration.

## Workflow Patterns

### Pattern 1: PRD to Implementation (Fully Autonomous)

#### Step 1: Parse PRD with Auto-Expansion
```
"Parse the PRD file and automatically expand any task with complexity > 7"
```

**What Happens**:
1. `parse_prd` - Converts PRD into structured tasks
2. `analyze_project_complexity --research` - Analyzes all tasks
3. `expand_all --research --force` - Expands high-complexity tasks automatically

**Result**: Complete task breakdown ready for implementation

#### Step 2: Sequential Execution
```
"What should I work on next?"
```

**What Happens**:
- `next_task` tool identifies next available task
- Considers dependencies, priority, and status
- Returns ready-to-work task with full context

**Result**: Clear direction without manual task lookup

#### Step 3: Implementation Loop

For each task:
1. **Get Task Details**: `get_task --id="<id>"`
2. **Work on Implementation**: Code, test, verify
3. **Log Progress**: `update_subtask --id="<id>" --prompt="Findings..."`
4. **Mark Complete**: `set_task_status --id="<id>" --status="done"`
5. **Get Next**: `next_task` (returns to step 1)

### Pattern 2: Feature Branch Workflow

#### Step 1: Create Feature Tag
```
"Create a new tag for feature-user-auth from the current git branch"
```

**What Happens**:
- `add_tag --from-branch` creates tag matching branch name
- Isolates feature work from master

#### Step 2: Parse Feature PRD
```
"Parse the feature PRD into the feature-user-auth tag"
```

**What Happens**:
- `parse_prd --tag=feature-user-auth` creates tasks in feature context
- Master tasks remain unchanged

#### Step 3: Work in Feature Context
All operations automatically use feature tag:
- `get_tasks --tag=feature-user-auth`
- `next_task --tag=feature-user-auth`
- `expand_task --tag=feature-user-auth`

#### Step 4: Merge to Master
When feature is complete:
- Review tasks in feature tag
- Move important tasks to master
- Delete feature tag if no longer needed

### Pattern 3: Research-Backed Expansion

#### Step 1: Identify Complex Tasks
```
"Analyze project complexity and show me tasks that need breakdown"
```

**What Happens**:
- `analyze_project_complexity --research`
- Generates complexity report
- Identifies tasks with complexity > 7

#### Step 2: Research-Backed Expansion
```
"Expand task 10 with research on latest best practices"
```

**What Happens**:
- `expand_task --id="10" --research`
- Uses research model (GPT-4o) for up-to-date information
- Generates subtasks with current best practices

#### Step 3: Update Based on Research
```
"Update task 10 based on the research findings"
```

**What Happens**:
- `update_task --id="10" --research --prompt="Research findings..."`
- Incorporates latest information into task details

## Autonomous Commands Reference

### Task Discovery
- `next_task` - Get next available task (automatic dependency resolution)
- `get_tasks --status=pending` - List all pending tasks
- `get_task --id="5"` - Get specific task details

### Task Breakdown
- `analyze_project_complexity --research` - Analyze all tasks
- `expand_task --id="5" --research` - Expand with research
- `expand_all --research` - Expand all pending tasks

### Progress Tracking
- `update_subtask --id="5.2" --prompt="Implementation notes"` - Log progress
- `set_task_status --id="5" --status="done"` - Mark complete
- `set_task_status --id="5" --status="in-progress"` - Start working

### Dependency Management
- `validate_dependencies` - Check for issues
- `fix_dependencies` - Auto-fix problems
- `add_dependency --id="5" --depends-on="3"` - Add dependency

### Research
- `research --query="Latest React patterns" --taskIds="5,6"` - Research with context
- `research --query="Security best practices" --filePaths="src/auth.ts"` - Research with code context

## Example: Complete Autonomous Session

### Initial Setup (One-Time)
```bash
# 1. Parse PRD
parse_prd --input="sprint1-prd.txt" --num-tasks=15

# 2. Analyze complexity
analyze_project_complexity --research

# 3. Expand high-complexity tasks
expand_all --research --force

# 4. Validate dependencies
validate_dependencies
```

### Daily Workflow (Autonomous)
```bash
# Morning: Get next task
next_task
# Returns: Task 5 - "Implement user authentication"

# Work on task...
# Log findings
update_subtask --id="5.2" --prompt="JWT implementation complete, using RS256"

# Mark subtask done
set_task_status --id="5.2" --status="done"

# Get next subtask
next_task
# Returns: Task 5.3 - "Add refresh token support"

# Continue until task complete
set_task_status --id="5" --status="done"

# Get next task automatically
next_task
# Returns: Task 6 - "Implement password reset"
```

## Tips for Minimal Input

### 1. Use Natural Language
Instead of: "Get task with ID 5"
Use: "What should I work on next?"

### 2. Leverage `next_task`
- Automatically finds next available task
- Considers all dependencies
- No need to manually check what's ready

### 3. Batch Operations
- Use `expand_all` instead of expanding one-by-one
- Use `set_task_status` with comma-separated IDs: `--id="5,6,7"`
- Use `get_task` with multiple IDs: `--id="5,6,7"`

### 4. Research When Needed
- Enable `--research` for new technologies
- Use `research` tool for up-to-date information
- Let AI incorporate findings automatically

### 5. Regular Validation
- Run `validate_dependencies` after major changes
- Use `fix_dependencies` to auto-resolve issues
- Prevents problems from accumulating

## Automation Opportunities

### Pre-Implementation Checklist
```bash
# Run before starting work
1. validate_dependencies
2. next_task  # Get current task
3. get_task --id="<next_task_id>"  # Review details
```

### Post-Implementation Checklist
```bash
# Run after completing work
1. update_subtask --id="<id>" --prompt="Implementation complete"
2. set_task_status --id="<id>" --status="done"
3. validate_dependencies  # Ensure no broken dependencies
4. next_task  # Get next task
```

### Weekly Review
```bash
# Run weekly
1. get_tasks --status=all  # Review all tasks
2. analyze_project_complexity  # Check for new high-complexity tasks
3. validate_dependencies  # Ensure dependency graph is clean
4. expand_all --research  # Expand any new high-complexity tasks
```

## Benefits of Autonomous Workflow

✅ **No Manual Task Lookup**: `next_task` finds what to work on  
✅ **Automatic Dependency Resolution**: System ensures correct order  
✅ **Research Integration**: Latest best practices automatically included  
✅ **Progress Tracking**: Subtask updates create implementation log  
✅ **Error Prevention**: Validation prevents dependency issues  
✅ **Context Awareness**: Codebase analysis enables better task generation  

---

**Last Updated**: December 22, 2025  
**Status**: ✅ Optimized for autonomous operation

