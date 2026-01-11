# After Cursor Restart - Quick Reference

## ✅ What Was Completed

### 1. MCP Server Configuration
- ✅ Updated `.cursor/mcp.json` with real API keys
- ✅ ANTHROPIC_API_KEY (Claude) configured
- ✅ OPENAI_API_KEY configured
- ✅ Committed to Git (commit: b64611b)

### 2. Recent Enhancements (Last Session)
- ✅ Fixed tenant ID extraction for rent roll (handles multiline)
- ✅ Corrected property names (ESP001, TCSH001)
- ✅ Enhanced review queue with:
  - Source file column
  - Amount display
  - Intelligent "Reason for Review" descriptions
- ✅ All changes committed to Git

### 3. System Status
- ✅ Docker containers running
- ✅ Backend: http://localhost:8000
- ✅ Frontend: http://localhost:5173
- ✅ Database healthy
- ✅ Login working (admin/admin123)

---

## 🚀 What to Do After Restart

### Step 1: Verify MCP Server
Ask the AI assistant:
```
"Can you check if the MCP server is running and what tools are available?"
```

### Step 2: Load Sprint 1 PRD
Ask the AI assistant:
```
"Parse the SPRINT_01_FOUNDATION_PRD.txt file and create tasks"
```

Or manually:
```bash
cd /home/singh/REIMS2
npx task-master-ai parse-prd "PRD files - 09-11-2025/SPRINT_01_FOUNDATION_PRD.txt"
```

### Step 3: View Tasks
Ask the AI assistant:
```
"Show me all current tasks"
```

Or manually:
```bash
npx task-master-ai list
```

### Step 4: Start Development
Ask the AI assistant:
```
"Let's start working on Sprint 1 tasks"
```

---

## 📂 Important Files

### PRD Files Location
```
PRD files - 09-11-2025/
├── SPRINT_01_FOUNDATION_PRD.txt
├── SPRINT_02_INTELLIGENCE_PRD.txt
├── TASKMASTER_CONFIG.yaml
└── ...
```

### Taskmaster Location
```
.taskmaster/
├── config.json (AI model config)
├── state.json (current tag: master)
└── tasks/tasks.json (existing tasks)
```

### Configuration Files
```
.cursor/mcp.json (MCP server config - UPDATED ✅)
.env (API keys - source of truth)
```

---

## 🎯 Next Session Goals

1. **Parse Sprint 1 PRD** - Generate tasks from the foundation sprint
2. **Review Task List** - See all 14 tasks from Sprint 1
3. **Start Implementation** - Begin working through tasks systematically
4. **Test & Validate** - Ensure each task meets acceptance criteria

---

## 📊 Git Status

**Current Branch:** `master`
**Commits Ahead:** 6 commits (not pushed to remote)
**Uncommitted Changes:** File permission changes (safe to ignore/stash)

**Recent Commits:**
- b64611b: MCP server configuration
- 8f7fd5f: Review reason column
- 7b3481e: Review queue enhancements
- 40d6ea5: Property name corrections
- 20bb781: Tenant ID extraction fix

---

## ⚠️ Notes

### API Keys
- Keys are now in `.cursor/mcp.json` (active after restart)
- Source keys remain in `.env` (don't delete)
- MCP server will use keys from `mcp.json`

### Taskmaster CLI
- Use `npx task-master-ai [command]` for CLI access
- MCP server provides same functionality through Cursor
- No need to install globally

### Python `taskmaster-ai`
- ❌ Does NOT exist as PyPI package
- ✅ Using `task-master-ai` (NPM) via MCP instead
- ✅ Provides same functionality

---

## 🔧 If MCP Server Doesn't Start

1. Check Cursor's Output panel (View → Output)
2. Select "Model Context Protocol" from dropdown
3. Look for error messages
4. Verify Node.js is installed: `node --version`
5. Manually test: `npx -y task-master-ai`

---

## 📞 Quick Commands Reference

```bash
# View tasks
npx task-master-ai list

# Show next task
npx task-master-ai next

# View specific task
npx task-master-ai show 1

# Parse PRD
npx task-master-ai parse-prd "file.txt"

# View all tags
npx task-master-ai tags

# Switch tag
npx task-master-ai use-tag master
```

---

**Last Updated:** 2025-11-11
**Session:** Chart of Accounts explanation + MCP configuration
**Next:** Sprint 1 PRD parsing and task execution

