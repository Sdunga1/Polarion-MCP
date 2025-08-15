# Distribution Guide

## 🚀 Publishing Your Polarion MCP Server

### Option 1: Docker Distribution (Recommended)

#### 1. Push to GitHub

```bash
git add .
git commit -m "Add Polarion MCP Server"
git push
```

#### 2. Create a Release

- Go to your GitHub repository
- Click "Releases" → "Create a new release"
- Tag version: `v1.0.0`
- Release title: `Polarion MCP Server v1.0.0`
- Click "Publish release"

#### 3. Auto-Deploy

The GitHub Action will automatically:

- Build the Docker image
- Push to `ghcr.io/your-username/polarion-mcp`
- Tag as `latest` and `v1.0.0`

#### 4. Users Add to mcp.json

```json
{
  "mcpServers": {
    "polarion": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "ghcr.io/your-username/polarion-mcp:latest"]
    }
  }
}
```

### Option 2: NPM Distribution

#### 1. Publish to NPM

```bash
npm publish
```

#### 2. Users Install

```json
{
  "mcpServers": {
    "polarion": {
      "command": "uvx",
      "args": ["mcp-polarion-server@latest"]
    }
  }
}
```

## 📋 Pre-Distribution Checklist

- [ ] Update `POLARION_BASE_URL` to your instance
- [ ] Test authentication flow
- [ ] Verify all tools work correctly
- [ ] Update README with your specific setup
- [ ] Set up GitHub repository
- [ ] Configure GitHub Container Registry permissions

## 🎯 Distribution Strategy

**Primary: Docker** (like GitHub MCP)

- Zero setup for users
- Consistent environment
- Proven pattern

**Secondary: NPM** (like Google Sheets MCP)

- For Python developers
- Lighter weight option

## 🔧 Maintenance

- **Updates**: Create new releases to trigger auto-builds
- **Versions**: Use semantic versioning (v1.0.0, v1.1.0, etc.)
- **Support**: Monitor GitHub issues for user feedback
