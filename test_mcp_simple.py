#!/usr/bin/env python
"""간단한 MCP 서버 테스트"""

import json
import subprocess
import time
from pathlib import Path

venv_python = Path(r"c:\potenup3\Qwen3-TTS\.venv\Scripts\python.exe")
mcp_server = Path(r"c:\potenup3\Qwen3-TTS\mcp_server.py")

print("Starting MCP server...")
process = subprocess.Popen(
    [str(venv_python), str(mcp_server)],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,  # Merge stderr to stdout
    text=True,
)

# Send initialize request
print("\nSending initialize request...")
init_request = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "test-client", "version": "1.0.0"},
    },
}

request_str = json.dumps(init_request) + "\n"
print(f"Request: {request_str}")
process.stdin.write(request_str)
process.stdin.flush()

# Read response with timeout
print("\nWaiting for response...")
time.sleep(3)

# Try to read 10 lines or until timeout
for i in range(10):
    try:
        line = process.stdout.readline()
        if line:
            print(f"Line {i}: {repr(line)}")
            if line.strip() and line.strip().startswith("{"):
                try:
                    response = json.loads(line)
                    print("\n✓ Got JSON response:")
                    print(json.dumps(response, indent=2, ensure_ascii=False))
                    break
                except json.JSONDecodeError as e:
                    print(f"JSON parse error: {e}")
        else:
            print(f"Line {i}: <empty>")
    except Exception as e:
        print(f"Error reading line {i}: {e}")
        break

# Cleanup
print("\nTerminating process...")
process.terminate()
try:
    process.wait(timeout=2)
except subprocess.TimeoutExpired:
    process.kill()

print("Done")
