# coding=utf-8
import os
import sys
import time
import shutil
from datetime import datetime
import torch
import soundfile as sf

from qwen_tts import Qwen3TTSModel


def main():
    # Get input filename from command line argument
    if len(sys.argv) < 2:
        print("Usage: python test_simple.py <input_filename.txt>")
        print("Example: python test_simple.py test.txt")
        sys.exit(1)
    
    input_filename = sys.argv[1]
    
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

    # Reference audio - Using Trump voice as reference
    ref_audio_path = os.path.join(project_root, "assets", "Donald_Trump_VoiceSample.wav")
    ref_text = "Thank you very much. A short time ago, the U.S. military carried out massive precision strikes on the three key nuclear facilities."

    # Read synthesis text from file
    input_txt_path = os.path.join(INPUT_DIR, input_filename)
    print(f"Reading text from: {input_txt_path}")
    with open(input_txt_path, "r", encoding="utf-8") as f:
        syn_text = f.read().strip()
    
    print(f"Text to synthesize: {syn_text}")
    syn_lang = "korean"  # 한국어로 명시적 지정

    print("Generating speech with default Korean voice...")
    t0 = time.time()
    
    # 기본 TTS 생성 (참조 오디오 사용)
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
    input_name = os.path.splitext(os.path.basename(input_txt_path))[0]
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    
    # Copy input txt file with timestamp
    timestamped_txt_path = os.path.join(INPUT_DIR, f"{input_name}_{timestamp}.txt")
    shutil.copy2(input_txt_path, timestamped_txt_path)
    print(f"Input text copied to: {timestamped_txt_path}")
    
    # Save audio with same timestamp
    output_path = os.path.join(OUT_DIR, f"{input_name}_{timestamp}.wav")
    sf.write(output_path, wavs[0], sr)
    print(f"Audio saved to: {output_path}")


if __name__ == "__main__":
    main()