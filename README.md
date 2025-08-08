# Polarion MCP Server

This MCP server provides tools to authenticate with Polarion, generate access tokens, and fetch requirements from your Polarion instance.

## Features

- **Authentication**: Form-based login to Polarion
- **Token Generation**: Automated token generation using browser automation
- **Requirements Fetching**: Fetch requirements via Polarion REST API
- **Status Checking**: Check authentication and token status

## Setup

1. **Install dependencies:**

   ```bash
   cd atoms-monorepo/apps/polarion-mcp
   uv venv
   source .venv/bin/activate
   uv pip install -e .
   ```

2. **Install Chrome WebDriver:**

   ```bash
   # The webdriver-manager will handle this automatically
   # or install manually: brew install chromedriver
   ```

3. **Configure MCP in Cursor:**

   Add to your `mcp.json` file:

   ```json
   {
     "mcpServers": {
       "polarion-server": {
         "command": "/Users/sarathkumardunga/.local/bin/uv",
         "args": [
           "--directory",
           "/Users/sarathkumardunga/Desktop/ATOMS.Tech/atoms-monorepo/apps/polarion-mcp",
           "run",
           "polarion_mcp_server.py"
         ]
       }
     }
   }
   ```

## Usage

### 1. Authenticate with Polarion

```
"Authenticate me to Polarion with username: admin and password: [your_password]"
```

### 2. Generate Access Token

```
"Generate a Polarion access token named 'cursor-integration'"
```

### 3. Fetch Requirements

```
"Get 5 requirements from my Polarion instance"
```

### 4. Check Status

```
"Check my Polarion connection status"
```

### 5. Complete Flow (with Google Sheets)

```
"Get 5 requirements from my Polarion instance and write them to the Google Sheets called 'polarion-requirements'"
```

## Security

- Credentials are stored locally in `polarion_credentials.json`
- Tokens are stored locally in `polarion_token.json`
- Files are created in the same directory as the MCP server

## Troubleshooting

1. **Chrome WebDriver Issues**: Make sure Chrome is installed and up to date
2. **Authentication Failures**: Verify your Polarion credentials
3. **Token Generation Issues**: Check if the token page is accessible
4. **API Errors**: Ensure you have proper permissions in Polarion

## Files Created

- `polarion_credentials.json`: Stored credentials
- `polarion_token.json`: Generated access tokens
