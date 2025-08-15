# 🚀 Polarion MCP Server - User Guide

## Quick Setup (30 seconds)

### Step 1: Add to your mcp.json

**Option A: With Persistent Token Storage (Recommended)**
```json
{
  "mcpServers": {
    "polarion": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-v", "polarion-tokens:/app/tokens",
        "ghcr.io/sdunga1/polarion-mcp:latest"
      ]
    }
  }
}
```

**Option B: With Environment Variable Token**
```json
{
  "mcpServers": {
    "polarion": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "ghcr.io/sdunga1/polarion-mcp:latest"],
      "env": {
        "POLARION_TOKEN": "your-token-here"
      }
    }
  }
}
```

**Option C: Basic (Token re-entry required each session)**
```json
{
  "mcpServers": {
    "polarion": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "ghcr.io/sdunga1/polarion-mcp:latest"]
    }
  }
}
```

### Step 2: Restart Cursor

Close and reopen Cursor IDE.

### Step 3: Authenticate

In Cursor chat, run:

1. `Open Polarion login` - Browser opens to Polarion
2. Login with your credentials
3. Generate a token at: `http://dev.polarion.atoms.tech/polarion/#/user_tokens`
4. `Set Polarion token: YOUR_TOKEN_HERE`

## 🎯 Available Tools

Once authenticated, you can use these tools in Cursor:

### 📋 Projects

- `Get Polarion projects` - List all projects
- `Get Polarion project: PROJECT_ID` - Get project details

### 📝 Work Items (Requirements)

- `Get Polarion work items: PROJECT_ID` - List work items
- `Get Polarion work item: PROJECT_ID ITEM_ID` - Get specific item

### 📄 Documents

- `Get Polarion document: PROJECT_ID SPACE_ID DOC_NAME` - Get documents

### 🔍 Status

- `Check Polarion status` - Verify authentication

## 💡 Example Usage

```
# First, authenticate
Open Polarion login
Set Polarion token: abc123xyz...

# Explore your projects
Get Polarion projects

# Work with requirements
Get Polarion work items: drivepilot (limit: 10)
Get Polarion work item: drivepilot REQ-123

# Check documents
Get Polarion document: drivepilot requirements SystemReqs
```

## 🔧 Troubleshooting

**Authentication Issues:**

- Regenerate token in Polarion
- Check token wasn't truncated when copying

**Connection Issues:**

- Verify `http://dev.polarion.atoms.tech/polarion` is accessible
- Check network/VPN settings

**Docker Issues:**

- Ensure Docker is running
- Try: `docker pull ghcr.io/sdunga1/polarion-mcp:latest`

## 📞 Support

For issues or questions:

- GitHub: [Polarion-MCP Issues](https://github.com/Sdunga1/Polarion-MCP/issues)
- Check connection status: `Check Polarion status`
