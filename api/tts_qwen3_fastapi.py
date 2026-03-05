import collections
import logging
import os
import sys
import tempfile
import time
from contextlib import asynccontextmanager
from datetime import datetime

import soundfile as sf
import torch
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from qwen_tts import Qwen3TTSModel

# stt 모듈 임포트 (프로젝트 루트를 sys.path 에 추가 후 임포트)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from stt.whisper_main import transcribe as whisper_transcribe  # noqa: E402

# ── 로깅 설정 ────────────────────────────────────────────────
LOG_MAX_LINES = 200  # 메모리에 보관할 최대 로그 줄 수
_log_buffer: collections.deque = collections.deque(maxlen=LOG_MAX_LINES)


class _DequeHandler(logging.Handler):
    """최근 로그를 deque 에 보관하는 핸들러 (GET /logs 용)."""

    def emit(self, record: logging.LogRecord) -> None:
        _log_buffer.append(self.format(record))


def _setup_logging() -> logging.Logger:
    fmt = logging.Formatter(
        "%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logger = logging.getLogger("qwen_api")
    logger.setLevel(logging.DEBUG)
    if logger.handlers:  # 중복 핸들러 방지
        return logger

    # 콘솔
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    # 메모리 버퍼
    dh = _DequeHandler()
    dh.setFormatter(fmt)
    logger.addHandler(dh)

    # 파일 (PROJECT_ROOT/api_server.log)
    log_file = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "api_server.log"
    )
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    return logger


log = _setup_logging()

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
    log.info("[STARTUP] Loading Qwen3-TTS model: %s", MODEL_PATH)
    log.info("[STARTUP] ref_audio : %s", REF_AUDIO_PATH)
    log.info("[STARTUP] ref_text  : %s", REF_TEXT)
    tts_model = Qwen3TTSModel.from_pretrained(
        MODEL_PATH,
        device_map="cpu",
        dtype=torch.float32,
        attn_implementation="eager",
    )
    log.info("[STARTUP] Model loaded successfully!")
    yield
    log.info("[SHUTDOWN] Server shutting down.")


app = FastAPI(
    title="Qwen3-TTS API",
    description="Upload a .txt file and receive a synthesized WAV audio file.",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    return {"status": "ok", "model_loaded": tts_model is not None}


@app.get("/logs")
async def get_logs(n: int = 100):
    """최근 로그 n 줄을 반환합니다 (기본값 100)."""
    lines = list(_log_buffer)[-n:]
    return JSONResponse(content={"lines": lines, "total": len(_log_buffer)})


@app.post("/tts")
async def tts(
    file: UploadFile = File(..., description="합성할 텍스트 .txt 파일"),
    ref_audio_file: UploadFile | None = File(
        None,
        description="참조 음성 파일 (미지정 시 기본값: assets/Donald_Trump_VoiceSample.wav)",
    ),
    ref_file: UploadFile | None = File(
        None,
        description="참조 텍스트 .txt 파일 (미지정 시 기본값: assets/ref_file.txt)",
    ),
):
    """
    업로드된 .txt 파일의 텍스트를 음성으로 합성하여 WAV 파일로 반환합니다.
    ref_audio_file / ref_file 을 선택적으로 업로드하면 해당 파일을 참조로 사용합니다.
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

    # ── 참조 음성 결정 ─────────────────────────────────────────
    _tmp_files = []  # 요청 완료 후 삭제할 임시 파일 목록
    if ref_audio_file and ref_audio_file.filename:
        audio_raw = await ref_audio_file.read()
        ext = os.path.splitext(ref_audio_file.filename)[1] or ".wav"
        tmp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=ext, dir=OUT_DIR)
        tmp_audio.write(audio_raw)
        tmp_audio.close()
        _tmp_files.append(tmp_audio.name)
        used_ref_audio = tmp_audio.name
        log.info("[TTS] ref_audio  : (uploaded) %s", ref_audio_file.filename)
    else:
        used_ref_audio = REF_AUDIO_PATH
        log.info("[TTS] ref_audio  : (default) %s", used_ref_audio)

    # ── 참조 텍스트 결정 ───────────────────────────────────────
    if ref_file and ref_file.filename:
        ref_raw = await ref_file.read()
        try:
            used_ref_text = ref_raw.decode("utf-8").strip()
        except UnicodeDecodeError:
            used_ref_text = ref_raw.decode("cp949", errors="replace").strip()
        log.info(
            "[TTS] ref_text   : (uploaded) %s  →  %s",
            ref_file.filename,
            used_ref_text[:60],
        )
    else:
        _default_ref_txt = os.path.join(PROJECT_ROOT, "assets", "ref_file.txt")
        if os.path.exists(_default_ref_txt):
            with open(_default_ref_txt, encoding="utf-8") as _f:
                used_ref_text = _f.read().strip()
            log.info("[TTS] ref_text   : (assets/ref_file.txt) %s", used_ref_text[:60])
        else:
            used_ref_text = REF_TEXT
            log.info("[TTS] ref_text   : (hardcoded default) %s", used_ref_text[:60])

    # ── 음성 생성 ──────────────────────────────────────────────
    log.info("[TTS] ── 요청 시작 ──────────────────────────")
    log.info("[TTS] 파일명      : %s", file.filename)
    log.info(
        "[TTS] 입력 텍스트 : %s",
        syn_text[:120] + ("..." if len(syn_text) > 120 else ""),
    )
    log.info(
        "[TTS] 파라미터   : language=Auto x_vector_only=True max_new_tokens=2048 "
        "temperature=0.9 top_k=50 top_p=1.0 repetition_penalty=1.05"
    )
    t0 = time.time()
    try:
        wavs, sr = tts_model.generate_voice_clone(
            text=syn_text,
            language="Auto",
            ref_audio=used_ref_audio,
            ref_text=used_ref_text,
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
        log.error("[TTS] 생성 실패: %s", e)
        raise HTTPException(status_code=500, detail=f"TTS generation failed: {e}")
    finally:
        for _f in _tmp_files:
            try:
                os.remove(_f)
            except OSError:
                pass

    elapsed = time.time() - t0
    log.info("[TTS] 생성 완료  : %.2fs", elapsed)

    # ── WAV 저장 ───────────────────────────────────────────────
    output_filename = f"{base_name}_{timestamp}.wav"
    output_path = os.path.join(OUT_DIR, output_filename)
    sf.write(output_path, wavs[0], sr)
    log.info("[TTS] 저장 완료  : %s", output_path)

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

    log.info("[STT] ── 요청 시작 ──────────────────────────")
    log.info("[STT] 파일명      : %s", file.filename)
    log.info("[STT] 저장 경로   : %s", saved_audio_path)
    log.info("[STT] 파일 크기   : %d bytes", len(raw))
    t0 = time.time()
    try:
        text = whisper_transcribe(saved_audio_path, save_result=True)
    except Exception as e:
        log.error("[STT] 변환 실패: %s", e)
        raise HTTPException(status_code=500, detail=f"STT failed: {e}")

    elapsed = time.time() - t0
    log.info("[STT] 변환 완료  : %.2fs", elapsed)
    log.info("[STT] 전사 결과  : %s", text[:120] + ("..." if len(text) > 120 else ""))

    return JSONResponse(
        content={
            "filename": file.filename,
            "text": text,
            "elapsed_sec": round(elapsed, 2),
        }
    )
