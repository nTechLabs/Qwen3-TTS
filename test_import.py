#!/usr/bin/env python
"""qwen_tts 모듈 import 테스트"""

import sys
import traceback

print("=" * 50)
print("Qwen3-TTS Import 테스트")
print("=" * 50)

try:
    print("\n1. qwen_tts 모듈 import 시도...")
    import qwen_tts

    print("   ✓ qwen_tts import 성공!")

    print("\n2. Qwen3TTSModel import 시도...")
    from qwen_tts import Qwen3TTSModel

    print("   ✓ Qwen3TTSModel import 성공!")

    print("\n3. 기타 주요 모듈 확인...")
    print(f"   - qwen_tts 경로: {qwen_tts.__file__}")

    print("\n" + "=" * 50)
    print("✓ 모든 테스트 통과! Qwen3-TTS가 정상적으로 설치되어 있습니다.")
    print("=" * 50)

except ImportError as e:
    print("\n✗ Import 에러 발생:")
    print(f"   {str(e)}")
    print("\n상세 에러:")
    traceback.print_exc()
    print("\n해결 방법:")
    print("   1. pip install -e . 실행")
    print("   2. 또는 pip install qwen-tts 실행")
    sys.exit(1)

except Exception as e:
    print("\n✗ 예상치 못한 에러:")
    print(f"   {str(e)}")
    traceback.print_exc()
    sys.exit(1)
