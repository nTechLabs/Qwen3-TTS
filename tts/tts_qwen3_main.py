import argparse
import os
import shutil
import sys
import time
from datetime import datetime

import soundfile as sf
import torch

from qwen_tts import Qwen3TTSModel


def main():
    # ── 커맨드라인 인자 파싱 ────────────────────────────────────
    parser = argparse.ArgumentParser(description="Qwen3-TTS voice cloning CLI")
    parser.add_argument(
        "input_filename",
        help="합성할 텍스트 파일명 (input_txt/ 기준, 예: trumpSpeech.txt)",
    )
    parser.add_argument(
        "--ref_audio_file",
        default="Donald_Trump_VoiceSample.wav",
        help="참조 음성 파일명 (assets/ 기준, 기본값: Donald_Trump_VoiceSample.wav)",
    )
    parser.add_argument(
        "--ref_file",
        default=None,
        help="참조 텍스트 파일명 (assets/ 기준, 예: ref_file.txt). "
        "미지정 시 ref_audio_file 과 같은 이름의 .txt 또는 내장 기본값 사용",
    )
    args = parser.parse_args()

    input_filename = args.input_filename

    device = "cpu"
    MODEL_PATH = "Qwen/Qwen3-TTS-12Hz-1.7B-Base"

    # Get project root directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)

    OUT_DIR = os.path.join(project_root, "output_wav")
    INPUT_DIR = os.path.join(project_root, "input_txt")
    os.makedirs(OUT_DIR, exist_ok=True)

    print("Loading model...")
    tts = Qwen3TTSModel.from_pretrained(
        MODEL_PATH,
        device_map=device,
        dtype=torch.float32,
        attn_implementation="eager",
    )
    print("Model loaded!")

    # ── 참조 음성 설정 ──────────────────────────────────────────
    ref_audio_path = os.path.join(project_root, "assets", args.ref_audio_file)
    if not os.path.exists(ref_audio_path):
        print(f"[ERROR] ref_audio_file 을 찾을 수 없습니다: {ref_audio_path}")
        sys.exit(1)
    print(f"ref_audio : {ref_audio_path}")

    # ref_text 결정 우선순위:
    #  1) --ref_file 로 명시된 파일 (assets/ 기준)
    #  2) ref_audio_file 과 동일 이름의 .txt (assets/ 에 존재할 경우)
    #  3) assets/ref_file.txt
    _default_ref_txt = os.path.join(project_root, "assets", "ref_file.txt")

    def _read_txt(path: str) -> str:
        with open(path, encoding="utf-8") as _f:
            return _f.read().strip()

    if args.ref_file:
        ref_text_path = os.path.join(project_root, "assets", args.ref_file)
        if not os.path.exists(ref_text_path):
            print(f"[ERROR] ref_file 을 찾을 수 없습니다: {ref_text_path}")
            sys.exit(1)
        ref_text = _read_txt(ref_text_path)
        print(f"ref_text  : (from --ref_file={args.ref_file}) {ref_text[:60]}...")
    else:
        auto_txt = os.path.splitext(ref_audio_path)[0] + ".txt"
        if os.path.exists(auto_txt):
            ref_text = _read_txt(auto_txt)
            print(f"ref_text  : (auto from {auto_txt}) {ref_text[:60]}...")
        elif os.path.exists(_default_ref_txt):
            ref_text = _read_txt(_default_ref_txt)
            print(f"ref_text  : (from assets/ref_file.txt) {ref_text[:60]}...")
        else:
            print(
                "[ERROR] ref_text 파일을 찾을 수 없습니다. "
                "--ref_file 을 지정하거나 assets/ref_file.txt 를 생성하세요."
            )
            sys.exit(1)

    # Read synthesis text from file
    input_txt_path = os.path.join(INPUT_DIR, input_filename)
    print(f"Reading text from: {input_txt_path}")
    with open(input_txt_path, encoding="utf-8") as f:
        syn_text = f.read().strip()

    print(f"Text to synthesize: {syn_text}")
    syn_lang = "Auto"

    print("Generating speech...")
    t0 = time.time()

    wavs, sr = tts.generate_voice_clone(
        text=syn_text,
        language=syn_lang,
        ref_audio=ref_audio_path,
        ref_text=ref_text,
        x_vector_only_mode=True,
        max_new_tokens=2048,
        do_sample=True,
        top_k=50,
        top_p=1.0,
        temperature=0.9,
        repetition_penalty=1.05,
        subtalker_dosample=True,
        subtalker_top_k=50,
        subtalker_top_p=1.0,
        subtalker_temperature=0.9,
    )

    t1 = time.time()
    print(f"Generation completed in {t1 - t0:.3f}s")

    # Create timestamp for both input and output files
    input_filename = os.path.splitext(os.path.basename(input_txt_path))[0]
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

    # Copy input txt file with timestamp
    timestamped_txt_path = os.path.join(INPUT_DIR, f"{input_filename}_{timestamp}.txt")
    shutil.copy2(input_txt_path, timestamped_txt_path)
    print(f"Input text copied to: {timestamped_txt_path}")

    # Save audio with same timestamp
    output_path = os.path.join(OUT_DIR, f"{input_filename}_{timestamp}.wav")
    sf.write(output_path, wavs[0], sr)
    print(f"Audio saved to: {output_path}")


if __name__ == "__main__":
    main()
