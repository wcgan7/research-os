#!/usr/bin/env python3
"""Monitor a running literature review agent."""

import json
import sys
from pathlib import Path


def monitor(log_file: str):
    with open(log_file) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                if obj.get("type") == "assistant":
                    msg = obj.get("message", {})
                    for block in msg.get("content", []):
                        if block.get("type") == "text":
                            print(f"\n>>> {block['text']}")
                        elif block.get("type") == "tool_use":
                            inp = block.get("input", {})
                            cmd = inp.get("command", "")[:200]
                            print(f"  TOOL: {cmd}")
                        elif block.get("type") == "thinking":
                            thinking = block.get("thinking", "")[:300]
                            print(f"  [thinking: {thinking}]")
                elif obj.get("type") == "result":
                    print(f"\n=== RESULT ===")
                    print(f"  Duration: {obj.get('duration_ms', 0)/1000:.1f}s")
                    print(f"  Turns: {obj.get('num_turns', 0)}")
                    print(f"  Cost: ${obj.get('total_cost_usd', 0):.4f}")
                    print(f"  Stop: {obj.get('stop_reason', '?')}")
            except json.JSONDecodeError:
                pass


if __name__ == "__main__":
    if len(sys.argv) < 2:
        # Find latest log
        log_root = Path.home() / ".research-os" / "logs"
        dirs = sorted(log_root.rglob("stdout.log"), key=lambda p: p.stat().st_mtime, reverse=True)
        if dirs:
            log_file = str(dirs[0])
            print(f"Using latest: {log_file}\n")
        else:
            print("No logs found")
            sys.exit(1)
    else:
        log_file = sys.argv[1]

    monitor(log_file)
