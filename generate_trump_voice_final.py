#!/usr/bin/env python
"""qwen3tts MCP를 사용한 음성 생성 - 최종 버전"""

import json
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path

# UTF-8 인코딩 설정
if sys.stdout:
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


def call_qwen3tts_mcp():
    print("=" * 80)
    print("Qwen3-TTS MCP - Trump 음성 생성")
    print("=" * 80)

    # 텍스트 읽기
    text_file = Path(r"c:\potenup3\Qwen3-TTS\input_txt\trumpSpeech.txt")
    print(f"\n1. 텍스트 파일 읽기: {text_file}")

    if not text_file.exists():
        print("   ✗ 파일을 찾을 수 없습니다")
        return False

    with open(text_file, encoding="utf-8") as f:
        text_content = f.read().strip()

    print(f"   ✓ 읽음 ({len(text_content)} 자)")

    # MCP 서버 시작
    venv_python = Path(r"c:\potenup3\Qwen3-TTS\.venv\Scripts\python.exe")
    mcp_server = Path(r"c:\potenup3\Qwen3-TTS\mcp_server.py")

    print("\n2. MCP 서버 시작...")
    try:
        proc = subprocess.Popen(
            [str(venv_python), str(mcp_server)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False,
        )
        print("   ✓ 서버 시작")
    except Exception as e:
        print(f"   ✗ 실패: {e}")
        return False

    # Read stderr in background
    stderr_lines = []

    def read_stderr():
        try:
            while True:
                line = proc.stderr.readline()
                if not line:
                    break
                stderr_lines.append(line.decode("utf-8", errors="replace"))
        except:
            pass

    stderr_thread = threading.Thread(target=read_stderr, daemon=True)
    stderr_thread.start()

    # Initialize
    print("\n3. Initialize 요청...")
    init_req = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "voice-converter", "version": "1.0"},
        },
    }

    req_bytes = (json.dumps(init_req) + "\n").encode("utf-8")
    proc.stdin.write(req_bytes)
    proc.stdin.flush()

    # Read initialize response
    response_queue = queue.Queue()

    def read_output():
        try:
            while True:
                line = proc.stdout.readline()
                if not line:
                    break
                response_queue.put(line)
        except:
            pass

    output_thread = threading.Thread(target=read_output, daemon=True)
    output_thread.start()

    # Wait for initialize response
    start = time.time()
    while time.time() - start < 5:
        try:
            line = response_queue.get(timeout=0.5)
            line_str = line.decode("utf-8", errors="replace").strip()
            if line_str and line_str.startswith("{"):
                try:
                    resp = json.loads(line_str)
                    if resp.get("id") == 1:
                        print("   ✓ Initialize 완료")
                        break
                except:
                    pass
        except queue.Empty:
            pass

    # Send initialized notification
    print("\n4. Initialized 알림 전송...")
    init_notif = {"jsonrpc": "2.0", "method": "initialized", "params": {}}

    notif_bytes = (json.dumps(init_notif) + "\n").encode("utf-8")
    proc.stdin.write(notif_bytes)
    proc.stdin.flush()
    print("   ✓ 알림 전송")

    # Send generate_voice request
    print("\n5. 음성 생성 요청 전송...")
    print("   음성: trump")
    print("   언어: Auto")

    gen_req = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "generate_voice",
            "arguments": {
                "text": text_content,
                "voice_style": "trump",
                "language": "Auto",
            },
        },
    }

    gen_bytes = (json.dumps(gen_req) + "\n").encode("utf-8")
    proc.stdin.write(gen_bytes)
    proc.stdin.flush()
    print("   ✓ 요청 전송")

    # Wait for response
    print("\n6. 음성 생성 대기 중...")
    print("   processing", end="", flush=True)

    start = time.time()
    timeout = 300  # 5분 타임아웃
    response = None
    progress_count = 0

    while time.time() - start < timeout:
        elapsed = time.time() - start
        try:
            line = response_queue.get(timeout=1)
            line_str = line.decode("utf-8", errors="replace").strip()

            if line_str and line_str.startswith("{"):
                try:
                    resp = json.loads(line_str)
                    if resp.get("id") == 2:
                        response = resp
                        break
                except:
                    pass
        except queue.Empty:
            # Print one dot every 10 seconds
            next_count = int(elapsed // 10)
            if next_count > progress_count:
                print(".", end="", flush=True)
                progress_count = next_count

    if response:
        print(f"\n   ✓ 응답 수신 ({int(time.time() - start)}초)")

        result = response.get("result", {})

        # Handle MCP standard response format (content wrapper)
        audio_file = None
        text_file_out = None
        gen_time = 0
        success = False
        error = "Unknown error"

        if "content" in result:
            # MCP 표준 형식
            content = result.get("content", [{}])[0]
            if isinstance(content, dict) and "text" in content:
                try:
                    inner_result = json.loads(content["text"])
                    success = inner_result.get("success")
                    error = inner_result.get("error")
                    audio_file = inner_result.get("audio_file")
                    text_file_out = inner_result.get("text_file")
                    gen_time = inner_result.get("generation_time", 0)
                except json.JSONDecodeError:
                    success = False
                    error = "Failed to parse response content"
        else:
            # 직접 응답 형식
            success = result.get("success")
            error = result.get("error")
            audio_file = result.get("audio_file")
            text_file_out = result.get("text_file")
            gen_time = result.get("generation_time", 0)

        if success:
            print("\n" + "=" * 80)
            print("✓ 음성 생성 완료!")
            print("=" * 80)
            print("\n[결과 정보]")
            print(f"  생성 시간: {gen_time:.2f}초")
            print(f"  음성 파일: {audio_file}")
            print(f"  텍스트 파일: {text_file_out}")

            if audio_file and Path(audio_file).exists():
                file_size = Path(audio_file).stat().st_size / 1024 / 1024
                print(f"  파일 크기: {file_size:.2f} MB")

            print(f"\n✓ {Path(audio_file).name} 파일이 생성되었습니다!")

            proc.terminate()
            return True
        else:
            print(f"\n   ✗ 음성 생성 실패: {error}")
    else:
        print(f"\n   ✗ 응답 없음 (타임아웃: {timeout}초)")

    proc.terminate()
    return False


if __name__ == "__main__":
    success = call_qwen3tts_mcp()
    exit(0 if success else 1)
