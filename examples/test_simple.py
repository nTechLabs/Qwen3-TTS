# coding=utf-8
import os
import time
import torch
import soundfile as sf

from qwen_tts import Qwen3TTSModel


def main():
    device = "cpu"
    MODEL_PATH = "Qwen/Qwen3-TTS-12Hz-1.7B-Base"
    OUT_DIR = "output_wav"
    os.makedirs(OUT_DIR, exist_ok=True)

    print("Loading model...")
    tts = Qwen3TTSModel.from_pretrained(
        MODEL_PATH,
        device_map=device,
        dtype=torch.float32,
        attn_implementation="eager",
    )
    print("Model loaded!")

    # Reference audio
    ref_audio_path = "https://qianwen-res.oss-cn-beijing.aliyuncs.com/Qwen3-TTS-Repo/clone_2.wav"
    ref_text = "Okay. Yeah. I resent you. I love you. I respect you. But you know what? You blew it! And thanks to you."

    # Synthesis target
    syn_text = "Good one. Okay, fine, I'm just gonna leave this sock monkey here. Goodbye."
    syn_lang = "Auto"

    print("Generating speech...")
    t0 = time.time()
    
    wavs, sr = tts.generate_voice_clone(
        text=syn_text,
        language=syn_lang,
        ref_audio=ref_audio_path,
        ref_text=ref_text,
        x_vector_only_mode=False,
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

    # Save only the first audio
    output_path = os.path.join(OUT_DIR, "output.wav")
    sf.write(output_path, wavs[0], sr)
    print(f"Audio saved to: {output_path}")


if __name__ == "__main__":
    main()