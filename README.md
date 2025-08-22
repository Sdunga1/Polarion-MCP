# Polarion MCP Server

A Model Context Protocol (MCP) server for interacting with Siemens Polarion requirements management system.

## Features

- 🔐 **Authentication** - Browser-based login with manual token generation
- 📋 **Projects** - List and get detailed project information
- 📝 **Work Items** - Query requirements, tasks, and other work items
- 📄 **Documents** - Access Polarion documents and spaces
- 🔍 **Flexible queries** - Filter work items with custom queries
- ⚡ **Lightweight** - Optimized API calls with configurable field sets

## Quick Start (Recommended)

### Using Docker (Like GitHub MCP)

Add this to your `mcp.json`:

```json
{
  "mcpServers": {
    "polarion": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "--pull=always",
        "-v",
        "polarion-tokens:/app/tokens",
        "ghcr.io/sdunga1/polarion-mcp:latest"
      ]
    }
  }
}
```

**That's it!** No installation needed, just restart Cursor.

> **Auto-Updates:** The `--pull=always` flag ensures you automatically get the latest version every time you use the MCP server. No manual updates needed!

## Usage

Once connected, you'll have access to these tools in Cursor:

1. **Authentication:**

   ```
   Open Polarion login → Set Polarion token
   ```

2. **Explore Projects:**

   ```
   Get Polarion projects (limit: 10)
   Get Polarion project: your-project-id
   ```

3. **Work with Requirements:**

   ```
   Get Polarion work items: project-id (limit: 5)
   Get Polarion work item: project-id work-item-id
   ```

4. **Access Documents:**

   ```
   Get Polarion document: project-id space-id document-name
   ```

5. **Check Status:**
   ```
   Check Polarion status
   ```

## Local Development

### Prerequisites

- Python 3.10+
- Access to Polarion instance

### Installation

```bash
pip install -r requirements.txt
```

### Running Locally

```bash
python polarion_mcp_server.py
```

This runs the server in stdio mode for local MCP development.
