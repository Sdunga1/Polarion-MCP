#!/bin/bash
# Auto-updating Polarion MCP wrapper script

REPO="ghcr.io/sdunga1/polarion-mcp:latest"

# Check for updates (silent)
docker pull $REPO > /dev/null 2>&1

# Run the MCP server with fresh image
exec docker run -i --rm -v polarion-tokens:/app/tokens $REPO "$@"
