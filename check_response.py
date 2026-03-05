#!/usr/bin/env python
"""MCP 응답 상세 확인"""

import json
import queue
import subprocess
import threading
import time
from pathlib import Path

venv_python = Path(r"c:\potenup3\Qwen3-TTS\.venv\Scripts\python.exe")
mcp_server = Path(r"c:\potenup3\Qwen3-TTS\mcp_server.py")

# 텍스트 읽기
with open(r"c:\potenup3\Qwen3-TTS\input_txt\trumpSpeech.txt", encoding="utf-8") as f:
    text_content = f.read().strip()

# MCP 서버 시작
proc = subprocess.Popen(
    [str(venv_python), str(mcp_server)],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=False,
)

output_queue = queue.Queue()
stderr_list = []


def read_output():
    try:
        while True:
            line = proc.stdout.readline()
            if not line:
                break
            output_queue.put(line)
    except:
        pass


def read_stderr():
    try:
        while True:
            line = proc.stderr.readline()
            if not line:
                break
            stderr_list.append(line.decode("utf-8", errors="replace"))
    except:
        pass


output_thread = threading.Thread(target=read_output, daemon=True)
stderr_thread = threading.Thread(target=read_stderr, daemon=True)
output_thread.start()
stderr_thread.start()

# Initialize
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

proc.stdin.write((json.dumps(init_req) + "\n").encode("utf-8"))
proc.stdin.flush()

# Wait for initialize response
while True:
    try:
        line = output_queue.get(timeout=5)
        resp = json.loads(line.decode("utf-8", errors="replace"))
        if resp.get("id") == 1:
            break
    except:
        pass

# Send initialized
proc.stdin.write(b'{"jsonrpc": "2.0", "method": "initialized", "params": {}}\n')
proc.stdin.flush()

# Send generate_voice
gen_req = {
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
        "name": "generate_voice",
        "arguments": {"text": text_content, "voice_style": "trump", "language": "Auto"},
    },
}

proc.stdin.write((json.dumps(gen_req) + "\n").encode("utf-8"))
proc.stdin.flush()

print("Waiting for response...")

start = time.time()
timeout = 300
response = None

while time.time() - start < timeout:
    try:
        line = output_queue.get(timeout=1)
        line_str = line.decode("utf-8", errors="replace")

        if line_str.strip().startswith("{"):
            try:
                resp = json.loads(line_str)
                if resp.get("id") == 2:
                    response = resp
                    break
            except:
                pass
    except queue.Empty:
        if int(time.time() - start) % 10 == 0 and int(time.time() - start) > 0:
            print(f"Progress: {int(time.time() - start)}s")

if response:
    print("\n=== Full Response ===")
    print(json.dumps(response, indent=2, ensure_ascii=False))
else:
    print("No response")

print("\n=== Server Logs ===")
for line in stderr_list[-50:]:
    line = line.strip()
    if line:
        print(line)

proc.terminate()
