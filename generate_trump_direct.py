"""
Trump Voice Generator - Direct Implementation
trumpSpeech.txt를 읽어서 Trump 음성으로 변환
"""

import os
import shutil
import time
from datetime import datetime

import soundfile as sf
import torch

from qwen_tts import Qwen3TTSModel


def main():
    device = "cpu"
    MODEL_PATH = "Qwen/Qwen3-TTS-12Hz-1.7B-Base"

    # Get project root directory
    project_root = os.path.dirname(os.path.abspath(__file__))

    OUT_DIR = os.path.join(project_root, "output_wav")
    INPUT_DIR = os.path.join(project_root, "input_txt")
    os.makedirs(OUT_DIR, exist_ok=True)

    print("=" * 80)
    print("Trump Voice Generator - Direct Implementation")
    print("=" * 80)

    print("\n1. Loading model...")
    t_load_start = time.time()
    tts = Qwen3TTSModel.from_pretrained(
        MODEL_PATH,
        device_map=device,
        dtype=torch.float32,
        attn_implementation="eager",
    )
    t_load_end = time.time()
    print(f"   ✓ Model loaded in {t_load_end - t_load_start:.1f}s")

    # Reference audio
    ref_audio_path = os.path.join(
        project_root, "assets", "Donald_Trump_VoiceSample.wav"
    )
    ref_text = "Thank you very much. A short time ago, the U.S. military carried out massive precision strikes on the three key nuclear facilities."

    # Read synthesis text from file
    input_txt_path = os.path.join(INPUT_DIR, "trumpSpeech.txt")
    print(f"\n2. Reading text from: {input_txt_path}")
    with open(input_txt_path, encoding="utf-8") as f:
        syn_text = f.read().strip()

    print(f"   Text length: {len(syn_text)} characters")
    print(f"   Preview: {syn_text[:100]}...")

    syn_lang = "Auto"

    print("\n3. Generating speech...")
    print("   (This may take several minutes)")
    t0 = time.time()

    # Progress indicator
    import threading

    stop_progress = threading.Event()

    def show_progress():
        elapsed = 0
        while not stop_progress.is_set():
            time.sleep(10)
            if not stop_progress.is_set():
                elapsed += 10
                print(f"   ... {elapsed}s elapsed", end="\r")

    progress_thread = threading.Thread(target=show_progress, daemon=True)
    progress_thread.start()

    try:
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
    finally:
        stop_progress.set()
        progress_thread.join(timeout=1)

    t1 = time.time()
    print(f"\n   ✓ Generation completed in {t1 - t0:.1f}s")

    # Create timestamp for both input and output files
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

    # Copy input txt file with timestamp
    timestamped_txt_path = os.path.join(INPUT_DIR, f"trumpSpeech_{timestamp}.txt")
    shutil.copy2(input_txt_path, timestamped_txt_path)
    print("\n4. Files saved:")
    print(f"   Input: {timestamped_txt_path}")

    # Save audio with same timestamp
    output_path = os.path.join(OUT_DIR, f"trumpSpeech_{timestamp}.wav")
    sf.write(output_path, wavs[0], sr)
    print(f"   Audio: {output_path}")

    # File size
    file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"   Size: {file_size_mb:.2f} MB")

    print("\n" + "=" * 80)
    print("✓ Trump voice generation completed successfully!")
    print("=" * 80)


if __name__ == "__main__":
    main()
