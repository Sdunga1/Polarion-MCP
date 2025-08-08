# Polarion MCP Server

A Model Context Protocol (MCP) server for interacting with Siemens Polarion requirements management system.

## Features

- Authentication with Polarion
- Fetch requirements from Polarion REST API
- Get user information
- Status checking
- HTTP API endpoints for web hosting

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

## Deployment to Render

### Option 1: Using render.yaml (Recommended)

1. Push your code to a GitHub repository
2. Go to [Render Dashboard](https://dashboard.render.com/)
3. Click "New +" → "Blueprint"
4. Connect your GitHub repository
5. Render will automatically detect the `render.yaml` file and deploy

### Option 2: Manual Deployment

1. Push your code to a GitHub repository
2. Go to [Render Dashboard](https://dashboard.render.com/)
3. Click "New +" → "Web Service"
4. Connect your GitHub repository
5. Configure:
   - **Name**: `polarion-mcp-server`
   - **Environment**: `Python`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python polarion_mcp_server.py`
   - **Environment Variables**:
     - `MCP_TRANSPORT`: `http`
     - `PORT`: `8000`

### Environment Variables

- `MCP_TRANSPORT`: Set to `http` for web hosting, `stdio` for local development
- `PORT`: Port number (default: 8000, Render will set this automatically)

## API Endpoints

Once deployed, your server will be available at `https://your-app-name.onrender.com` with these endpoints:

- `GET /` - Health check
- `GET /health` - Service status
- `POST /open_polarion_login` - Open Polarion login page
- `POST /set_polarion_token` - Set Polarion token
- `GET /get_polarion_requirements?limit=5` - Get requirements
- `GET /check_polarion_status` - Check authentication status
- `GET /get_polarion_user/{user_id}` - Get user information

## Usage

1. Deploy to Render
2. Get your URL (e.g., `https://polarion-mcp-server.onrender.com`)
3. Use the HTTP endpoints to interact with Polarion

## Local vs Hosted

- **Local**: Uses stdio transport for MCP development
- **Hosted**: Uses HTTP transport for web API access

The server automatically detects the environment and switches transport modes accordingly.
