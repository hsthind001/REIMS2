# 🔧 MCP Server Activation Guide - task-master-ai

## ✅ **Configuration Complete!**

Your MCP (Model Context Protocol) server for `task-master-ai` is now configured with your API keys.

---

## 📁 **Files Updated**

1. **`~/.cursor/mcp.json`** - Global Cursor configuration
2. **`/home/singh/REIMS2/.cursor/mcp.json`** - Project-specific configuration

Both files now contain:
- ✅ `task-master-ai` server configuration
- ✅ Anthropic API Key (Claude)
- ✅ OpenAI API Key

---

## 🚀 **How to Activate**

### **Step 1: Restart Cursor**

The MCP server loads when Cursor starts. You need to:

1. **Save all files** (Ctrl+S or Cmd+S)
2. **Close Cursor completely** (File → Exit)
3. **Reopen Cursor**
4. **Open the REIMS2 project**

### **Step 2: Verify MCP Server is Running**

After restarting Cursor, you should see:

- A notification that MCP servers are connected
- Or check the status bar at the bottom of Cursor
- Or look for MCP indicator in the bottom right

### **Step 3: Test the Connection**

Try asking me (the AI):

```
"Use task-master-ai to list all tasks"
```

or

```
"Show me the next task from task-master-ai"
```

If MCP is working, I'll be able to call the task-master-ai tools directly.

---

## 🛠️ **Available MCP Tools (After Activation)**

Once the MCP server is active, I'll have access to these tools:

### **Project Management:**
- `initialize_project` - Set up new project
- `parse_prd` - Parse PRD files into tasks

### **Task Viewing:**
- `get_tasks` - List all tasks
- `next_task` - Get next available task
- `get_task` - View specific task details

### **Task Management:**
- `add_task` - Create new task
- `update_task` - Modify existing task
- `update_subtask` - Update subtask details
- `set_task_status` - Change task status
- `remove_task` - Delete a task

### **Task Structure:**
- `expand_task` - Break task into subtasks
- `expand_all` - Expand all pending tasks
- `clear_subtasks` - Remove all subtasks
- `add_subtask` - Add subtask to parent
- `remove_subtask` - Remove specific subtask
- `move_task` - Reorganize task hierarchy

### **Dependencies:**
- `add_dependency` - Add task dependency
- `remove_dependency` - Remove dependency
- `validate_dependencies` - Check for issues
- `fix_dependencies` - Auto-fix dependency problems

### **Analysis:**
- `analyze_project_complexity` - Analyze task complexity
- `complexity_report` - View complexity analysis
- `research` - AI-powered research with context

### **Tag Management:**
- `list_tags` - View all tags
- `add_tag` - Create new tag context
- `delete_tag` - Remove tag
- `use_tag` - Switch active tag
- `rename_tag` - Rename tag
- `copy_tag` - Duplicate tag

### **File Generation:**
- `generate` - Create task markdown files
- `models` - Manage AI model configuration

---

## 🎯 **What You Can Do Now**

### **Before Restart (Current Session):**

You can continue working with me directly! I can:
- ✅ Read and edit files
- ✅ Run commands
- ✅ Implement features
- ✅ Commit to Git
- ✅ Debug issues

Just tell me what you want!

### **After Restart (With MCP Active):**

I'll have **additional powers** through task-master-ai tools:
- ✅ Structured task management
- ✅ Automated task breakdown
- ✅ AI-powered research (with Perplexity)
- ✅ Complexity analysis
- ✅ Multi-context workflows (tags)

---

## 📊 **Current Task Status**

Your `.taskmaster/tasks/tasks.json` shows:

```
Sprint 1: ✅ 14/14 tasks complete (100%)
Sprint 2: ✅ 37/37 tasks complete (100%)
Total:    ✅ 51/51 tasks complete (100%)
```

**All PRD tasks are already implemented!**

---

## 🔄 **MCP vs Direct Work**

### **Without MCP (Current):**
- I interact with files directly
- You tell me what to do
- I implement and commit
- Works great for ad-hoc work

### **With MCP (After Restart):**
- I use structured task management tools
- Better for complex, multi-step projects
- Automatic task tracking and breakdown
- More suitable for team workflows

**Both approaches work!** MCP just adds structure.

---

## ⚙️ **Configuration Details**

Your MCP configuration uses:

```json
{
  "mcpServers": {
    "task-master-ai": {
      "command": "npx",
      "args": ["-y", "task-master-ai"],
      "env": {
        "ANTHROPIC_API_KEY": "sk-ant-api03-...",
        "OPENAI_API_KEY": "sk-proj-...",
        "PERPLEXITY_API_KEY": "",
        "GOOGLE_API_KEY": "",
        ...
      }
    }
  }
}
```

### **How it works:**
1. Cursor launches `npx -y task-master-ai` as a subprocess
2. The subprocess starts an MCP server
3. I (Claude) can call the server's tools
4. The tools use your API keys for AI operations

---

## 🐛 **Troubleshooting**

### **Issue: MCP Server Not Starting**

**Check 1: Node.js/npx Available**
```bash
which npx
npx --version
```

If missing, npx is needed on your system (not just in Docker).

**Check 2: Internet Connection**
The first run downloads `task-master-ai` from npm.

**Check 3: API Keys Valid**
Verify your API keys are active and not expired.

**Check 4: Cursor Logs**
- View → Output → Select "MCP Servers"
- Look for error messages

### **Issue: MCP Tools Not Available**

**Check 1: Verify Server Running**
Look for MCP indicator in Cursor status bar.

**Check 2: Project Context**
Make sure you're in the REIMS2 project folder.

**Check 3: Restart Again**
Sometimes a second restart helps.

### **Issue: "Command not found: npx"**

If npx is not available on your host:

**Option A: Install Node.js globally**
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install nodejs npm

# Verify
npx --version
```

**Option B: Use Docker wrapper** (requires passwordless sudo)
```bash
# Use the docker-npx script we created
cd /home/singh/REIMS2
./docker-npx --version

# Update mcp.json to use docker-npx
# Change "command": "npx" to "command": "/home/singh/REIMS2/docker-npx"
```

---

## 📝 **Next Steps**

### **Recommended: Restart Cursor Now**

1. Save this file
2. Close Cursor
3. Reopen Cursor
4. Open REIMS2 project
5. Check for MCP server indicator
6. Test with: "List all tasks using task-master-ai"

### **Alternative: Continue Without MCP**

You can keep working with me directly! I'm already very capable:

```
"Let's fix the review queue issues"
"Show me the reconciliation logic"
"Add a new feature to export data"
"Help me test the rent roll extraction"
```

---

## 🎉 **Summary**

✅ MCP configuration complete  
✅ API keys added (Claude + OpenAI)  
✅ Both global and project configs updated  
⏳ **Restart Cursor to activate**  

**After restart:**
- MCP server will load automatically
- I'll have access to 30+ task-master-ai tools
- Enhanced task management capabilities

**Before restart:**
- Continue working normally
- I'm fully functional without MCP
- All current features work

---

**Questions?** Just ask!

**Last Updated:** November 11, 2025  
**Status:** ✅ Configured, pending Cursor restart

