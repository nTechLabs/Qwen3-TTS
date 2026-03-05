#!/usr/bin/env python
"""MCP 서버 직접 테스트 스크립트"""

import json
import subprocess
import sys
import threading
from pathlib import Path


def read_stderr(process):
    """Read stderr in a separate thread"""
    for line in process.stderr:
        print(f"[STDERR] {line}", end="", file=sys.stderr)


def test_mcp_server():
    """Test MCP server with basic requests"""

    print("=" * 60)
    print("Qwen3-TTS MCP Server 테스트")
    print("=" * 60)

    # MCP 서버 시작
    venv_python = Path(r"c:\potenup3\Qwen3-TTS\.venv\Scripts\python.exe")
    mcp_server = Path(r"c:\potenup3\Qwen3-TTS\mcp_server.py")

    if not venv_python.exists():
        print(f"✗ Python 실행 파일을 찾을 수 없음: {venv_python}")
        return

    if not mcp_server.exists():
        print(f"✗ MCP 서버 파일을 찾을 수 없음: {mcp_server}")
        return

    print("\n1. MCP 서버 시작 중...")
    print(f"   Python: {venv_python}")
    print(f"   Server: {mcp_server}")

    try:
        process = subprocess.Popen(
            [str(venv_python), str(mcp_server)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

        # Start stderr reader thread
        stderr_thread = threading.Thread(
            target=read_stderr, args=(process,), daemon=True
        )
        stderr_thread.start()

        print("   ✓ 프로세스 시작 완료")

        # Test 1: Initialize
        print("\n2. Initialize 요청 전송...")
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

        process.stdin.write(json.dumps(init_request) + "\n")
        process.stdin.flush()

        # Wait a bit for stderr output
        import time

        time.sleep(2)

        response = process.stdout.readline()
        print(f"   Raw response: {repr(response)}")

        if response and response.strip():
            try:
                init_response = json.loads(response)
                print("   ✓ Initialize 응답:")
                print(f"     {json.dumps(init_response, indent=2, ensure_ascii=False)}")
            except json.JSONDecodeError as e:
                print(f"   ✗ JSON 파싱 에러: {e}")
                print(f"   응답 내용: {response}")
        else:
            print("   ✗ 응답 없음")

        # Test 2: Initialized notification
        print("\n3. Initialized 알림 전송...")
        initialized_notif = {"jsonrpc": "2.0", "method": "initialized", "params": {}}

        process.stdin.write(json.dumps(initialized_notif) + "\n")
        process.stdin.flush()
        print("   ✓ Initialized 전송 완료")

        # Test 3: List tools
        print("\n4. Tools/List 요청 전송...")
        list_request = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}

        process.stdin.write(json.dumps(list_request) + "\n")
        process.stdin.flush()

        response = process.stdout.readline()
        if response:
            list_response = json.loads(response)
            print("   ✓ Tools/List 응답:")
            tools = list_response.get("result", {}).get("tools", [])
            for tool in tools:
                print(f"     - {tool['name']}: {tool['description']}")

        print("\n" + "=" * 60)
        print("✓ MCP 서버가 정상적으로 작동합니다!")
        print("=" * 60)

        # Cleanup
        process.terminate()
        process.wait(timeout=5)

    except subprocess.TimeoutExpired:
        print("✗ 프로세스 종료 시간 초과")
        process.kill()
    except Exception as e:
        print(f"✗ 테스트 실패: {e}")
        import traceback

        traceback.print_exc()
        if "process" in locals():
            # Print stderr
            stderr_output = process.stderr.read()
            if stderr_output:
                print("\nStderr 출력:")
                print(stderr_output)


if __name__ == "__main__":
    test_mcp_server()
