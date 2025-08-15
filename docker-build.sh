#!/bin/bash

echo "🐳 Building Polarion MCP Docker Image"
echo "===================================="

# Build the Docker image
docker build -t polarion-mcp-server .

# Tag for GitHub Container Registry
docker tag polarion-mcp-server ghcr.io/your-username/polarion-mcp-server:latest

echo "✅ Docker image built successfully!"
echo ""
echo "📋 Next steps:"
echo "1. Push to GitHub Container Registry:"
echo "   docker push ghcr.io/your-username/polarion-mcp-server:latest"
echo ""
echo "2. Users can then add to their mcp.json:"
echo '   "polarion": {'
echo '     "command": "docker",'
echo '     "args": ["run", "-i", "--rm", "ghcr.io/your-username/polarion-mcp-server:latest"]'
echo '   }'
