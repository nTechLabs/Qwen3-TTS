#!/usr/bin/env python
"""Qwen3-TTS 간단한 실행 테스트"""

import os

import soundfile as sf
import torch

from qwen_tts import Qwen3TTSModel

print("=" * 60)
print("Qwen3-TTS 실행 테스트")
print("=" * 60)

# 설정
device = "cpu"
MODEL_PATH = "Qwen/Qwen3-TTS-12Hz-1.7B-Base"
OUT_DIR = "./output_wav"
os.makedirs(OUT_DIR, exist_ok=True)

print("\n1. 모델 로딩 중...")
try:
    tts = Qwen3TTSModel.from_pretrained(
        MODEL_PATH,
        device_map=device,
        dtype=torch.float32,
        attn_implementation="eager",
    )
    print("   ✓ 모델 로딩 성공!")
except Exception as e:
    print(f"   ✗ 모델 로딩 실패: {e}")
    print("\n   해결 방법:")
    print("   - 인터넷 연결 확인")
    print("   - 모델 다운로드 대기 (처음 실행시 시간 소요)")
    exit(1)

print("\n2. 음성 생성 중...")
try:
    # 간단한 텍스트로 테스트
    syn_text = "Hello, this is a test of Qwen3 TTS system."

    # Base 모델은 voice clone 방식 사용 (ref_audio + ref_text 필요)
    ref_audio_path = os.path.join(
        os.path.dirname(__file__), "assets", "Donald_Trump_VoiceSample.wav"
    )
    ref_text = "Thank you very much. A short time ago, the U.S. military carried out massive precision strikes on the three key nuclear facilities."

    wavs, sr = tts.generate_voice_clone(
        text=syn_text,
        language="Auto",
        ref_audio=ref_audio_path,
        ref_text=ref_text,
        max_new_tokens=10000,
        do_sample=True,
    )

    # 음성 저장
    output_path = os.path.join(OUT_DIR, "quick_test_output.wav")
    sf.write(output_path, wavs[0], samplerate=sr)

    print("   ✓ 음성 생성 성공!")
    print(f"   저장 경로: {output_path}")

except Exception as e:
    print(f"   ✗ 음성 생성 실패: {e}")
    import traceback

    traceback.print_exc()
    exit(1)

print("\n" + "=" * 60)
print("✓ 모든 테스트 완료! Qwen3-TTS가 정상 작동합니다.")
print("=" * 60)
