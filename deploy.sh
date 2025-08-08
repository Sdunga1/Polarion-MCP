#!/bin/bash

echo "🚀 Polarion MCP Server Deployment Script"
echo "========================================"

# Check if git is initialized
if [ ! -d ".git" ]; then
    echo "❌ Git repository not found. Please initialize git first:"
    echo "   git init"
    echo "   git add ."
    echo "   git commit -m 'Initial commit'"
    echo "   git remote add origin <your-github-repo-url>"
    echo "   git push -u origin main"
    exit 1
fi

# Check if all required files exist
echo "📋 Checking required files..."
required_files=("polarion_mcp_server.py" "requirements.txt" "render.yaml" "README.md")
for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file found"
    else
        echo "❌ $file missing"
        exit 1
    fi
done

echo ""
echo "✅ All files are ready!"
echo ""
echo "📝 Next steps:"
echo "1. Push your code to GitHub:"
echo "   git add ."
echo "   git commit -m 'Add Render deployment support'"
echo "   git push"
echo ""
echo "2. Deploy to Render:"
echo "   - Go to https://dashboard.render.com/"
echo "   - Click 'New +' → 'Blueprint'"
echo "   - Connect your GitHub repository"
echo "   - Render will auto-deploy using render.yaml"
echo ""
echo "3. Get your URL:"
echo "   - After deployment, you'll get a URL like:"
echo "   - https://polarion-mcp-server.onrender.com"
echo ""
echo "🎉 Your MCP server will be available as a web API!"
