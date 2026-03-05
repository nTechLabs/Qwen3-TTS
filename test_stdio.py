#!/usr/bin/env python
"""MCP 서버를 stdio로 직접 테스트"""

import json
import subprocess
from pathlib import Path

venv_python = Path(r"c:\potenup3\Qwen3-TTS\.venv\Scripts\python.exe")
mcp_server = Path(r"c:\potenup3\Qwen3-TTS\mcp_server.py")

# Start서버
proc = subprocess.Popen(
    [str(venv_python), str(mcp_server)],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=False,  # binary mode
)

# Send initialize
init_req = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "test", "version": "1.0"},
    },
}
request_bytes = (json.dumps(init_req) + "\n").encode("utf-8")

print(f"Sending: {request_bytes}")
proc.stdin.write(request_bytes)
proc.stdin.flush()

# Read response
print("Waiting for response...")
import queue
import threading


def read_stream(stream, q, name):
    try:
        while True:
            line = stream.readline()
            if not line:
                break
            q.put((name, line))
    except Exception as e:
        q.put((name, f"ERROR: {e}"))


stdout_queue = queue.Queue()
stderr_queue = queue.Queue()

stdout_thread = threading.Thread(
    target=read_stream, args=(proc.stdout, stdout_queue, "stdout"), daemon=True
)
stderr_thread = threading.Thread(
    target=read_stream, args=(proc.stderr, stderr_queue, "stderr"), daemon=True
)
stdout_thread.start()
stderr_thread.start()

# Wait for response
timeout = 10
import time

start = time.time()

response_received = False
while time.time() - start < timeout and not response_received:
    # Check stdout
    try:
        name, data = stdout_queue.get(timeout=0.1)
        if isinstance(data, bytes):
            data_str = data.decode("utf-8", errors="replace")
        else:
            data_str = str(data)

        print(f"[{name}] {data_str}")

        if name == "stdout" and data_str.strip().startswith("{"):
            try:
                resp_json = json.loads(data_str)
                print("\n✓ Parsed response:")
                print(json.dumps(resp_json, indent=2, ensure_ascii=False))
                response_received = True
            except Exception as e:
                print(f"Parse error: {e}")
    except queue.Empty:
        pass

    # Check stderr
    try:
        name, data = stderr_queue.get(timeout=0)
        if isinstance(data, bytes):
            data_str = data.decode("utf-8", errors="replace")
        else:
            data_str = str(data)
        print(f"[{name}] {data_str}")
    except queue.Empty:
        pass

if not response_received:
    print("\n✗ No valid response received")

proc.terminate()
proc.wait()
