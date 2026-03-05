import os
import sys

import whisper

# ── 모델 싱글톤 (처음 호출 시 로드) ──────────────────────────────
_model = None

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
STTOUT_DIR = os.path.join(PROJECT_ROOT, "sttout")
os.makedirs(STTOUT_DIR, exist_ok=True)


def _get_model():
    global _model
    if _model is None:
        print("Loading Whisper model...")
        _model = whisper.load_model("turbo")
        print("Whisper model loaded.")
    return _model


def transcribe(audio_path: str, save_result: bool = True) -> str:
    """
    audio_path : 절대 경로 또는 상대 경로의 오디오 파일
    save_result: True 이면 sttout/ 에 .txt 저장
    반환값     : 인식된 텍스트
    """
    model = _get_model()
    result = model.transcribe(audio_path)
    text = result["text"]

    if save_result:
        base_name = os.path.splitext(os.path.basename(audio_path))[0]
        output_path = os.path.join(STTOUT_DIR, f"{base_name}.txt")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"저장 완료: {output_path}")

    return text


# ── CLI 진입점 ────────────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python whisper_main.py <audio_file_path>")
        sys.exit(1)

    audio_arg = sys.argv[1]
    # 상대 경로면 audio/ 디렉토리 기준으로 해석
    if not os.path.isabs(audio_arg):
        audio_arg = os.path.join(PROJECT_ROOT, "audio", audio_arg)

    print(transcribe(audio_arg))
