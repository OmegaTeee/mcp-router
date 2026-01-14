#!/bin/bash

# Required parameters:
# @raycast.schemaVersion 1
# @raycast.title MCP Query
# @raycast.mode fullOutput
# @raycast.packageName MCP Router

# Optional parameters:
# @raycast.icon 🤖
# @raycast.argument1 { "type": "text", "placeholder": "Your query" }

# Documentation:
# @raycast.description Send a query to MCP Router with prompt enhancement
# @raycast.author MCP Router
# @raycast.authorURL https://github.com/your-username/mcp-router

# Installation:
# 1. Copy this script to ~/.config/raycast/scripts/mcp-query.sh
# 2. Make executable: chmod +x ~/.config/raycast/scripts/mcp-query.sh
# 3. Refresh Raycast scripts

ROUTER_URL="${MCP_ROUTER_URL:-http://localhost:9090}"

# First, enhance the prompt
enhanced=$(curl -s -X POST "${ROUTER_URL}/ollama/enhance" \
  -H "Content-Type: application/json" \
  -H "X-Client-Name: raycast" \
  -d "{\"prompt\": \"$1\"}")

# Extract the enhanced prompt
enhanced_prompt=$(echo "$enhanced" | python3 -c "import sys,json; print(json.load(sys.stdin).get('enhanced', '$1'))" 2>/dev/null || echo "$1")

# Display the result
echo "Original: $1"
echo ""
echo "Enhanced:"
echo "$enhanced_prompt"
