# Connect Claude Code Extension with Your Account

## Quick Steps

1. **Open Claude Code Panel in Cursor:**
   - Press `Ctrl+Shift+P` (or `Cmd+Shift+P` on Mac) to open Command Palette
   - Type "Claude Code: Open in Side Bar" and select it
   - OR click the Spark icon (✨) in the Editor Toolbar (top-right corner when a file is open)

2. **Sign In:**
   - When the Claude Code panel opens, you'll see a sign-in prompt
   - Click "Sign In" or "Log In"
   - Enter your email: **tera.nimana007@gmail.com**
   - Complete the authentication flow (browser may open for OAuth)

3. **Verify Connection:**
   - Once signed in, you should see your account information
   - You can start using Claude Code immediately

## Alternative Methods to Open Claude Code

### Method 1: Command Palette
- Press `Ctrl+Shift+P` (Windows/Linux) or `Cmd+Shift+P` (Mac)
- Type "Claude Code" and select:
  - "Claude Code: Open in Side Bar" (left sidebar)
  - "Claude Code: Open in New Tab" (new editor tab)
  - "Claude Code: Open in Terminal" (terminal mode)

### Method 2: Editor Toolbar Icon
- Open any file in Cursor
- Look for the Spark icon (✨) in the top-right corner of the editor
- Click it to open Claude Code

### Method 3: Activity Bar
- After running "Open in Side Bar" once, a Spark icon will appear in the left Activity Bar
- Click it anytime to open Claude Code

## Keyboard Shortcuts

- `Ctrl+Esc` (Windows/Linux) or `Cmd+Esc` (Mac): Focus Claude input
- `Ctrl+Shift+Esc` (Windows/Linux) or `Cmd+Shift+Esc` (Mac): Open new conversation tab
- `Ctrl+N` (Windows/Linux) or `Cmd+N` (Mac): New conversation (when Claude is focused)

## Troubleshooting

### If you don't see the sign-in prompt:
1. Try opening a new conversation: `Ctrl+N` or `Cmd+N`
2. Check if you're already signed in (look for account info in the panel)
3. Use the "Logout" command from Command Palette, then sign in again

### If sign-in doesn't work:
1. Check your internet connection
2. Ensure you have a valid Anthropic account
3. Try the CLI method: Open terminal and run `claude` to authenticate there

### If the Spark icon isn't visible:
1. Open a file (not just a folder)
2. Run "Claude Code: Open in Side Bar" from Command Palette
3. Restart Cursor if needed

## Verify Authentication

After signing in, you can verify by:
- Looking for your account email in the Claude Code panel
- Running a test prompt to see if Claude responds
- Checking the Command Palette for "Claude Code: Logout" (only appears when signed in)

## Next Steps

Once authenticated:
- Start using Claude Code for coding assistance
- Configure settings via `Cmd+,` (Mac) or `Ctrl+,` (Windows/Linux) → Extensions → Claude Code
- Set up MCP servers if needed (requires CLI configuration)
- Explore slash commands by typing `/` in the Claude input

