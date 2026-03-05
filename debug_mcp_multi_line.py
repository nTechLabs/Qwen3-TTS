#!/usr/bin/env python
"""MCP 서버 디버그 - 여러 줄 응답 확인"""

import json
import queue
import subprocess
import threading
import time
from pathlib import Path

venv_python = Path(r"c:\potenup3\Qwen3-TTS\.venv\Scripts\python.exe")
mcp_server = Path(r"c:\potenup3\Qwen3-TTS\mcp_server.py")

# 텍스트
text = """Hello friends,
Potenup 3rd AI-agent class members.
It's a pleasure to meet such wonderful people."""

print("=" * 80)
print("MCP 서버 디버그 - 여러 줄 응답 확인")
print("=" * 80)

# MCP 서버 시작
proc = subprocess.Popen(
    [str(venv_python), str(mcp_server)],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=False,
)

stderr_output = []
stdout_queue = queue.Queue()


def read_stdout():
    try:
        while True:
            line = proc.stdout.readline()
            if not line:
                break
            stdout_queue.put(line)
    except Exception as e:
        print(f"[STDOUT 읽기 오류] {e}")


def read_stderr():
    try:
        while True:
            line = proc.stderr.readline()
            if not line:
                break
            line_str = line.decode("utf-8", errors="replace")
            stderr_output.append(line_str)
            print(f"[STDERR] {line_str.rstrip()}")
    except Exception as e:
        print(f"[STDERR 읽기 오류]{e}")


stdout_thread = threading.Thread(target=read_stdout, daemon=True)
stdout_thread.start()
stderr_thread = threading.Thread(target=read_stderr, daemon=True)
stderr_thread.start()

# Initialize
init_req = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "debug", "version": "1.0"},
    },
}

print("\n1. Initialize 전송...")
proc.stdin.write((json.dumps(init_req) + "\n").encode("utf-8"))
proc.stdin.flush()

# Wait for init response - read multiple lines
all_init_responses = []
try:
    for _ in range(10):  # Try to read up to 10 lines
        try:
            resp = stdout_queue.get(timeout=1)
            all_init_responses.append(resp)
            print(f"   Got line {len(all_init_responses)}: {resp[:50]}")
        except queue.Empty:
            break

    if all_init_responses:
        print("   ✓ Initialize 응답 받음")
        for idx, resp in enumerate(all_init_responses):
            print(f"\n   Response {idx + 1}:")
            print(f"   Raw bytes: {resp}")
            print(f"   Hex: {resp.hex()}")
            try:
                resp_data = json.loads(resp.decode("utf-8", errors="replace"))
                print("   ✓ Valid JSON!")
                print(
                    f"   {json.dumps(resp_data, indent=2, ensure_ascii=False)[:200]}..."
                )
            except Exception as e:
                print(f"   Parse error: {e}")
    else:
        print("   ✗ Initialize 응답 없음")
except Exception as e:
    print(f"   ✗ 응답 읽기 오류: {e}")

# Send initialized
proc.stdin.write(b'{"jsonrpc": "2.0", "method": "initialized", "params": {}}\n')
proc.stdin.flush()
time.sleep(0.5)

# Send generate_voice
print("\n2. generate_voice 전송...")
gen_req = {
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
        "name": "generate_voice",
        "arguments": {"text": text, "voice_style": "trump", "language": "Auto"},
    },
}

print(f"   text 타입: {type(text)}")
print(f"   text 길이: {len(text)}")

proc.stdin.write((json.dumps(gen_req) + "\n").encode("utf-8"))
proc.stdin.flush()

print("\n3. 응답 대기 중 (최대 5분)...")
start_time = time.time()
all_gen_responses = []

# Read response with timeout - read multiple lines until JSON found
try:
    while time.time() - start_time < 300:  # 5분
        try:
            response = stdout_queue.get(timeout=1)
            all_gen_responses.append(response)
            print(f"Got response line {len(all_gen_responses)}: {response[:50]}")

            # Try parsing to see if it's JSON
            try:
                json.loads(response.decode("utf-8", errors="replace"))
                print(f"✓ Valid JSON found at line {len(all_gen_responses)}")
                break
            except:
                pass  # Not JSON yet, keep reading
        except queue.Empty:
            elapsed = int(time.time() - start_time)
            if elapsed % 10 == 0 and elapsed > 0:
                print(f"   대기 중... {elapsed}초 경과")
            continue
except Exception as e:
    print(f"   ✗ 응답 읽기 오류: {e}")

if all_gen_responses:
    print(f"\n총 {len(all_gen_responses)}개 응답 라인 받음")
    for idx, resp in enumerate(all_gen_responses):
        print(f"\n=== Response {idx + 1} ===")
        print(f"Raw bytes: {resp}")
        print(f"Hex: {resp.hex()}")
        try:
            resp_json = json.loads(resp.decode("utf-8", errors="replace"))
            print("✓ JSON 응답 파싱 성공!")
            result = resp_json.get("result", {})
            if isinstance(result, dict) and "content" in result:
                content_list = result["content"]
                if isinstance(content_list, list) and len(content_list) > 0:
                    content = content_list[0]
                    if isinstance(content, dict):
                        text_content = content.get("text", "")
                        print(f"응답 타입: {content.get('type')}")
                        if len(text_content) > 500:
                            print(f"응답 길이: {len(text_content)} 문자")
                            print(f"응답 앞부분:\n{text_content[:500]}...")
                        else:
                            print(f"응답:\n{text_content}")
            else:
                print(json.dumps(resp_json, indent=2, ensure_ascii=False)[:1000])
        except Exception as e:
            raw = resp.decode("utf-8", errors="replace")
            print(f"Raw string: {raw}")
            print(f"Parse error: {e}")
else:
    print("\n✗ 응답을 받지 못했습니다 (타임아웃)")

print("\n=== stderr 전체 로그 ===")
for line in stderr_output:
    print(line.rstrip())

print("\n서버 종료 중...")
proc.terminate()
proc.wait(timeout=5)
print("완료!")
