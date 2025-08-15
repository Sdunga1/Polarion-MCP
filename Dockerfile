FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the MCP server
COPY polarion_mcp_server.py .

# Set environment variable to run in stdio mode
ENV MCP_TRANSPORT=stdio

# Run the MCP server
CMD ["python", "polarion_mcp_server.py"]
