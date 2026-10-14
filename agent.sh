export MCP_CONNECTION_NONBLOCKING=0
TOOLS="Read(./**),Grep(./**),Glob(./**),Edit(./rules.json)"
TOOLS="$TOOLS,Bash(python verify.py)"
TOOLS="$TOOLS,mcp__scrapingbee__get_page_html,mcp__scrapingbee__get_page_text"
claude -p --model claude-sonnet-5-5 --setting-sources "" \
  --tools "Read,Grep,Glob,Edit,Bash" --allowedTools "$TOOLS" \
  --mcp-config ../mcp.json --strict-mcp-config < task.txt
