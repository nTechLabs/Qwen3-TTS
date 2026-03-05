#!/usr/bin/env python
"""qwen3tts MCP 서버 최종 확인 테스트"""

import json
import queue
import subprocess
import threading
import time
from pathlib import Path


def test_qwen3tts_mcp():
    print("=" * 70)
    print("Qwen3-TTS MCP Server - START 확인")
    print("=" * 70)

    venv_python = Path(r"c:\potenup3\Qwen3-TTS\.venv\Scripts\python.exe")
    mcp_server = Path(r"c:\potenup3\Qwen3-TTS\mcp_server.py")

    if not venv_python.exists():
        print(f"✗ Python 실행 파일 없음: {venv_python}")
        return False

    if not mcp_server.exists():
        print(f"✗ MCP 서버 파일 없음: {mcp_server}")
        return False

    print("\n1. MCP 서버 설정 확인")
    print(f"   Python: {venv_python}")
    print(f"   Server: {mcp_server}")
    print("   ✓ 설정 확인 완료")

    print("\n2. MCP 서버 시작...")
    try:
        proc = subprocess.Popen(
            [str(venv_python), str(mcp_server)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False,
        )
        print("   ✓ 프로세스 시작")
    except Exception as e:
        print(f"   ✗ 프로세스 시작 실패: {e}")
        return False

    print("\n3. Initialize 요청 전송...")
    init_req = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "1.0"},
        },
    }

    try:
        request_bytes = (json.dumps(init_req) + "\n").encode("utf-8")
        proc.stdin.write(request_bytes)
        proc.stdin.flush()
        print("   ✓ 요청 전송")
    except Exception as e:
        print(f"   ✗ 요청 전송 실패: {e}")
        proc.terminate()
        return False

    print("\n4. 응답 대기...")

    response_queue = queue.Queue()
    stderr_queue = queue.Queue()

    def read_stdout():
        try:
            for line in proc.stdout:
                response_queue.put(line)
        except:
            pass

    def read_stderr():
        try:
            for line in proc.stderr:
                stderr_queue.put(line.decode("utf-8", errors="replace").strip())
        except:
            pass

    stdout_thread = threading.Thread(target=read_stdout, daemon=True)
    stderr_thread = threading.Thread(target=read_stderr, daemon=True)
    stdout_thread.start()
    stderr_thread.start()

    # Wait for response
    timeout = 10
    start = time.time()
    response = None

    while time.time() - start < timeout:
        try:
            line = response_queue.get(timeout=0.5)
            line_str = line.decode("utf-8", errors="replace").strip()
            if line_str and line_str.startswith("{"):
                try:
                    response = json.loads(line_str)
                    break
                except:
                    pass
        except queue.Empty:
            pass

    # Print stderr messages
    while not stderr_queue.empty():
        msg = stderr_queue.get_nowait()
        if msg and "Warning" in msg:
            print(f"   [INFO] {msg}")

    if response:
        print("   ✓ 응답 수신")
        print("\n5. 응답 내용:")
        print(f"   {json.dumps(response, indent=4, ensure_ascii=False)}")

        # Verify response
        if response.get("jsonrpc") == "2.0" and "result" in response:
            result = response.get("result", {})
            if (
                result.get("protocolVersion") == "2024-11-05"
                and result.get("serverInfo", {}).get("name") == "qwen3tts"
            ):
                print("\n" + "=" * 70)
                print("✓ qwen3tts MCP 서버가 정상적으로 START됩니다!")
                print("=" * 70)
                print("\n[서버 정보]")
                print(f"  이름: {result['serverInfo']['name']}")
                print(f"  버전: {result['serverInfo']['version']}")
                print(f"  프로토콜: {result['protocolVersion']}")
                print("\n[사용 가능한 도구]")
                tools_result = result.get("capabilities", {})
                print(f"  tools: {list(tools_result.keys())}")

                proc.terminate()
                return True

        print("\n✗ 응답 형식이 기대와 다릅니다")
    else:
        print("   ✗ 응답 없음 (타임아웃)")
        # Print any stderr
        print("\n[STDERR 출력]")
        while not stderr_queue.empty():
            msg = stderr_queue.get_nowait()
            if msg:
                print(f"  {msg}")

    proc.terminate()
    return False


if __name__ == "__main__":
    success = test_qwen3tts_mcp()
    exit(0 if success else 1)
