#!/usr/bin/env bash
# PreToolUse hook: inject user steering messages into agent context.
# Reads from $STEERING_FILE, returns additionalContext if non-empty, then clears.

# No-op if env var not set (interactive sessions)
[ -z "$STEERING_FILE" ] && exit 0

# No-op if file doesn't exist
[ -f "$STEERING_FILE" ] || exit 0

# Read content
content=$(cat "$STEERING_FILE")

# No-op if empty/whitespace
trimmed=$(printf '%s' "$content" | tr -d '[:space:]')
[ -z "$trimmed" ] && exit 0

# JSON-escape the content safely
json_content=$(printf '%s' "$content" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read()))')

# Output hook response — strip outer quotes from json.dumps result
cat <<HOOKJSON
{"hookSpecificOutput":{"hookEventName":"PreToolUse","additionalContext":"[STEERING] ${json_content:1:-1}"}}
HOOKJSON

# Clear the file
> "$STEERING_FILE"
exit 0
