#!/bin/bash
# Auto-register agent reviews from Task tool calls
#
# Installation:
#   1. Copy this script to your project: .claude/hooks/auto-review.sh
#   2. Make executable: chmod +x .claude/hooks/auto-review.sh
#   3. Add to .claude/settings.json:
#      {
#        "hooks": {
#          "PostToolUse": [
#            {
#              "matcher": "Task",
#              "hooks": [
#                {
#                  "type": "command",
#                  "command": ".claude/hooks/auto-review.sh"
#                }
#              ]
#            }
#          ]
#        }
#      }

# Read tool input from stdin
INPUT=$(cat)

# Extract subagent_type from Task tool input
AGENT=$(echo "$INPUT" | jq -r '.tool_input.subagent_type // empty' 2>/dev/null)

# Only process if agent name was found
if [ -n "$AGENT" ] && [ "$AGENT" != "null" ]; then
    # Check if flow command exists
    if command -v flow &> /dev/null; then
        flow review --agent "$AGENT" --summary "Auto-registered via PostToolUse hook"
    fi
fi

# Always exit 0 to not block Claude
exit 0
