import os
import sys
import time
from contextlib import asynccontextmanager
from datetime import datetime

import soundfile as sf
import torch
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from qwen_tts import Qwen3TTSModel

# stt 모듈 임포트 (프로젝트 루트 기준)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from stt.whisper_main import transcribe as whisper_transcribe

# ── 경로 설정 ───────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

MODEL_PATH = "Qwen/Qwen3-TTS-12Hz-1.7B-Base"
REF_AUDIO_PATH = os.path.join(PROJECT_ROOT, "assets", "Donald_Trump_VoiceSample.wav")
REF_TEXT = (
    "Thank you very much. A short time ago, the U.S. military carried out "
    "massive precision strikes on the three key nuclear facilities."
)
OUT_DIR = os.path.join(PROJECT_ROOT, "output_wav")
INPUT_DIR = os.path.join(PROJECT_ROOT, "input_txt")
os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(INPUT_DIR, exist_ok=True)

# ── 모델 싱글톤 ──────────────────────────────────────────────
tts_model: Qwen3TTSModel = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """서버 시작 시 모델을 한 번만 로드합니다."""
    global tts_model
    print("Loading Qwen3-TTS model...")
    tts_model = Qwen3TTSModel.from_pretrained(
        MODEL_PATH,
        device_map="cpu",
        dtype=torch.float32,
        attn_implementation="eager",
    )
    print("Model loaded successfully!")
    yield
    print("Server shutting down.")


app = FastAPI(
    title="Qwen3-TTS API",
    description="Upload a .txt file and receive a synthesized WAV audio file.",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    return {"status": "ok", "model_loaded": tts_model is not None}


@app.post("/tts")
async def tts(file: UploadFile = File(..., description=".txt 파일을 업로드하세요")):
    """
    업로드된 .txt 파일의 텍스트를 Trump 음성으로 합성하여 WAV 파일로 반환합니다.
    """
    if tts_model is None:
        raise HTTPException(status_code=503, detail="Model is not loaded yet.")

    # ── 파일 타입 검증 ─────────────────────────────────────────
    if not file.filename.lower().endswith(".txt"):
        raise HTTPException(status_code=400, detail="Only .txt files are supported.")

    # ── 텍스트 읽기 ────────────────────────────────────────────
    raw = await file.read()
    try:
        syn_text = raw.decode("utf-8").strip()
    except UnicodeDecodeError:
        syn_text = raw.decode("cp949", errors="replace").strip()

    if not syn_text:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # ── 입력 파일 저장 (타임스탬프 포함) ─────────────────────────
    base_name = os.path.splitext(file.filename)[0]
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    saved_txt_path = os.path.join(INPUT_DIR, f"{base_name}_{timestamp}.txt")
    with open(saved_txt_path, "w", encoding="utf-8") as f:
        f.write(syn_text)

    # ── 음성 생성 ──────────────────────────────────────────────
    print(f"[{timestamp}] Generating TTS for: {file.filename}")
    t0 = time.time()
    try:
        wavs, sr = tts_model.generate_voice_clone(
            text=syn_text,
            language="Auto",
            ref_audio=REF_AUDIO_PATH,
            ref_text=REF_TEXT,
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS generation failed: {e}")

    elapsed = time.time() - t0
    print(f"[{timestamp}] Done in {elapsed:.2f}s")

    # ── WAV 저장 ───────────────────────────────────────────────
    output_filename = f"{base_name}_{timestamp}.wav"
    output_path = os.path.join(OUT_DIR, output_filename)
    sf.write(output_path, wavs[0], sr)
    print(f"[{timestamp}] Saved: {output_path}")

    # ── WAV 파일 반환 ──────────────────────────────────────────
    return FileResponse(
        path=output_path,
        media_type="audio/wav",
        filename=output_filename,
        headers={"X-Generation-Time": f"{elapsed:.2f}s"},
    )


# ── STT 엔드포인트 ─────────────────────────────────────────────
AUDIO_UPLOAD_DIR = os.path.join(PROJECT_ROOT, "audio")
os.makedirs(AUDIO_UPLOAD_DIR, exist_ok=True)

ALLOWED_AUDIO_EXT = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".webm"}


@app.post("/stt")
async def stt(
    file: UploadFile = File(
        ..., description="오디오 파일을 업로드하세요 (mp3, wav 등)"
    ),
):
    """
    업로드된 오디오 파일을 Whisper로 음성 인식하여 텍스트를 반환합니다.
    인식 결과는 sttout/ 디렉토리에 .txt 파일로도 저장됩니다.
    """
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_AUDIO_EXT:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio format '{ext}'. Allowed: {', '.join(ALLOWED_AUDIO_EXT)}",
        )

    # 업로드 파일을 audio/ 에 저장
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    base_name = os.path.splitext(file.filename)[0]
    saved_audio_path = os.path.join(AUDIO_UPLOAD_DIR, f"{base_name}_{timestamp}{ext}")

    raw = await file.read()
    with open(saved_audio_path, "wb") as f:
        f.write(raw)

    print(f"[{timestamp}] STT 요청: {file.filename}")
    t0 = time.time()
    try:
        text = whisper_transcribe(saved_audio_path, save_result=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"STT failed: {e}")

    elapsed = time.time() - t0
    print(f"[{timestamp}] STT 완료 ({elapsed:.2f}s): {text[:80]}...")

    return JSONResponse(
        content={
            "filename": file.filename,
            "text": text,
            "elapsed_sec": round(elapsed, 2),
        }
    )
