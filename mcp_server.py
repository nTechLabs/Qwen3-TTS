"""
Qwen3-TTS MCP Server
HTTP-based MCP server for Qwen3-TTS voice cloning
"""

import sys
import time
from datetime import datetime
from pathlib import Path

import soundfile as sf
import torch
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))
from qwen_tts import Qwen3TTSModel

app = FastAPI(title="Qwen3-TTS MCP Server", version="1.0.0")

# Global model instance
tts_model = None
MODEL_PATH = "Qwen/Qwen3-TTS-12Hz-1.7B-Base"
PROJECT_ROOT = Path(__file__).parent


class VoiceRequest(BaseModel):
    text: str
    voice_style: str = "trump"  # trump, leejemyung, etc
    language: str = "Auto"


class VoiceResponse(BaseModel):
    success: bool
    audio_file: str | None = None
    text_file: str | None = None
    generation_time: float | None = None
    error: str | None = None


@app.on_event("startup")
async def load_model():
    """Load TTS model on startup"""
    global tts_model
    print("Loading Qwen3-TTS model...")
    tts_model = Qwen3TTSModel.from_pretrained(
        MODEL_PATH,
        device_map="cpu",
        dtype=torch.float32,
        attn_implementation="eager",
    )
    print("Model loaded successfully!")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "model_loaded": tts_model is not None}


@app.post("/generate", response_model=VoiceResponse)
async def generate_voice(request: VoiceRequest):
    """Generate voice from text"""
    if tts_model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    try:
        # Select reference audio based on voice style
        if request.voice_style.lower() == "trump":
            ref_audio_path = PROJECT_ROOT / "assets" / "Donald_Trump_VoiceSample.wav"
            ref_text = "Thank you very much. A short time ago, the U.S. military carried out massive precision strikes on the three key nuclear facilities."
        elif request.voice_style.lower() == "leejemyung":
            ref_audio_path = PROJECT_ROOT / "assets" / "Leejamsample.mp3"
            ref_text = "유연의 지원과 도움의 힘입어 성장한 우리 대한민국은 이제 민주주의 회복의 경험과 역사를 아낌없이 나누는 선도국가로서의 역할을 마다하지 않겠습니다."
        else:
            raise HTTPException(
                status_code=400, detail=f"Unknown voice style: {request.voice_style}"
            )

        if not ref_audio_path.exists():
            raise HTTPException(
                status_code=404, detail=f"Reference audio not found: {ref_audio_path}"
            )

        # Generate speech
        print(f"Generating speech with {request.voice_style} voice...")
        t0 = time.time()

        wavs, sr = tts_model.generate_voice_clone(
            text=request.text,
            language=request.language,
            ref_audio=str(ref_audio_path),
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

        generation_time = time.time() - t0
        print(f"Generation completed in {generation_time:.3f}s")

        # Save files with timestamp
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        output_dir = PROJECT_ROOT / "output_wav"
        input_dir = PROJECT_ROOT / "input_txt"
        output_dir.mkdir(exist_ok=True)
        input_dir.mkdir(exist_ok=True)

        filename = f"{request.voice_style}_mcp_{timestamp}"
        audio_path = output_dir / f"{filename}.wav"
        text_path = input_dir / f"{filename}.txt"

        # Save audio
        sf.write(str(audio_path), wavs[0], sr)

        # Save text
        with open(text_path, "w", encoding="utf-8") as f:
            f.write(request.text)

        return VoiceResponse(
            success=True,
            audio_file=str(audio_path),
            text_file=str(text_path),
            generation_time=generation_time,
        )

    except Exception as e:
        print(f"Error generating voice: {e}")
        return VoiceResponse(success=False, error=str(e))


@app.get("/audio/{filename}")
async def get_audio(filename: str):
    """Download generated audio file"""
    audio_path = PROJECT_ROOT / "output_wav" / filename
    if not audio_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")
    return FileResponse(audio_path, media_type="audio/wav")


@app.get("/voices")
async def list_voices():
    """List available voice styles"""
    return {
        "voices": [
            {"name": "trump", "description": "Donald Trump voice"},
            {"name": "leejemyung", "description": "Lee Jae-myung voice"},
        ]
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8001)
