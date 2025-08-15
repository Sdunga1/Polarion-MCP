FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Create directory for persistent token storage
RUN mkdir -p /app/tokens

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the MCP server
COPY polarion_mcp_server.py .

# Set environment variables
ENV MCP_TRANSPORT=stdio
ENV TOKEN_DIR=/app/tokens

# Run the MCP server
CMD ["python", "polarion_mcp_server.py"]
