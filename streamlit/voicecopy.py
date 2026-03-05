r"""
STT → TTS 파이프라인 서비스 (Streamlit)
실행: .\.venv\Scripts\python.exe -m streamlit run streamlit/voicecopy.py
"""

import io

import requests

import streamlit as st

# ── 페이지 설정 ─────────────────────────────────────────────────
st.set_page_config(
    page_title="Voice Copy  |  STT → TTS",
    page_icon="🎙️",
    layout="centered",
)

# ── 사이드바 : 서버 URL 설정 ────────────────────────────────────
with st.sidebar:
    st.header("⚙️ 설정")
    API_BASE = st.text_input(
        "FastAPI 서버 URL",
        value="http://127.0.0.1:8000",
        help="uvicorn 으로 기동된 서버 주소",
    ).rstrip("/")

    st.divider()

    # 서버 상태 확인
    st.subheader("서버 상태")
    if st.button("🔄 상태 확인"):
        try:
            r = requests.get(f"{API_BASE}/health", timeout=3)
            if r.ok and r.json().get("model_loaded"):
                st.success("✅ 서버 정상 · 모델 로드됨")
            elif r.ok:
                st.warning("⚠️ 서버 응답 · 모델 로딩 중")
            else:
                st.error(f"❌ 서버 오류 ({r.status_code})")
        except requests.exceptions.ConnectionError:
            st.error("❌ 서버에 연결할 수 없습니다")
        except Exception as e:
            st.error(f"❌ {e}")

    st.caption(
        "서버 기동 명령어:\n"
        "```\n"
        ".venv\\Scripts\\python.exe -m uvicorn "
        "api.tts_qwen3_fastapi:app --host 127.0.0.1 --port 8000 --reload\n"
        "```"
    )

    st.divider()

    # ── LOG 섹션 ────────────────────────────────────────────
    st.subheader("📋 LOG")

    log_n = st.slider("표시 줄 수", min_value=20, max_value=200, value=50, step=10)
    auto_refresh = st.checkbox("자동 갱신 (3초)", value=False)

    if auto_refresh:
        import time as _time

        _time.sleep(3)
        st.rerun()

    if st.button("🔄 로그 갱신", use_container_width=True):
        st.rerun()

    try:
        lr = requests.get(f"{API_BASE}/logs", params={"n": log_n}, timeout=3)
        if lr.ok:
            lines = lr.json().get("lines", [])
            total = lr.json().get("total", 0)
            st.caption(f"최근 {len(lines)}줄 / 전체 {total}줄")
            if lines:
                st.code("\n".join(lines), language="", wrap_lines=False)
            else:
                st.info("로그가 없습니다.")
        else:
            st.warning(f"로그 조회 실패 ({lr.status_code})")
    except requests.exceptions.ConnectionError:
        st.warning("서버 미연결 — 로그를 불러올 수 없습니다.")
    except Exception as _e:
        st.warning(f"로그 오류: {_e}")

# ── session_state 초기화 ─────────────────────────────────────────
for key, default in [
    ("stt_text", ""),
    ("wav_bytes", None),
    ("wav_filename", "output.wav"),
    ("stt_elapsed", None),
    ("tts_elapsed", None),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ── 타이틀 ──────────────────────────────────────────────────────
st.title("🎙️ Voice Copy")
st.caption("오디오 파일 → STT 전사 → TTS 음성 합성 파이프라인")

# ════════════════════════════════════════════════════════════════
# STEP 1 · 오디오 업로드 & STT
# ════════════════════════════════════════════════════════════════
st.markdown("## STEP 1 · 오디오 업로드 & 전사 (STT)")

audio_file = st.file_uploader(
    "음성 파일을 선택하세요",
    type=["mp3", "wav", "m4a", "ogg", "flac", "webm"],
    help="허용 포맷: mp3, wav, m4a, ogg, flac, webm",
)

if audio_file:
    st.audio(audio_file, format=f"audio/{audio_file.name.rsplit('.', 1)[-1]}")

stt_btn = st.button(
    "▶ STT 실행",
    disabled=(audio_file is None),
    use_container_width=True,
    type="primary",
)

if stt_btn:
    if audio_file is None:
        st.warning("파일을 먼저 선택하세요.")
    else:
        with st.spinner("음성을 텍스트로 변환 중..."):
            try:
                audio_file.seek(0)
                resp = requests.post(
                    f"{API_BASE}/stt",
                    files={
                        "file": (
                            audio_file.name,
                            audio_file.read(),
                            audio_file.type or "application/octet-stream",
                        )
                    },
                    timeout=300,
                )
                if resp.ok:
                    data = resp.json()
                    st.session_state.stt_text = data.get("text", "")
                    st.session_state.stt_elapsed = data.get("elapsed_sec")
                    st.success("STT 완료!")
                else:
                    detail = resp.json().get("detail", resp.text)
                    st.error(f"STT 실패 ({resp.status_code}): {detail}")
            except requests.exceptions.ConnectionError:
                st.error(
                    "❌ 서버에 연결할 수 없습니다. 사이드바에서 서버 URL을 확인하세요."
                )
            except Exception as e:
                st.error(f"❌ 오류: {e}")

if st.session_state.stt_elapsed is not None:
    st.metric("STT 소요 시간", f"{st.session_state.stt_elapsed} 초")

# ════════════════════════════════════════════════════════════════
# STEP 2 · 전사 텍스트 확인 & 편집
# ════════════════════════════════════════════════════════════════
st.divider()
st.markdown("## STEP 2 · 전사 결과 확인 & 편집")

edited_text = st.text_area(
    "전사 결과 (직접 수정 가능)",
    value=st.session_state.stt_text,
    height=200,
    placeholder="STEP 1에서 STT를 실행하면 결과가 여기에 표시됩니다.\n직접 텍스트를 입력하거나 수정할 수도 있습니다.",
)

char_count = len(edited_text.strip())
st.caption(f"글자 수: {char_count}자")

# ════════════════════════════════════════════════════════════════
# STEP 3 · TTS 실행 & WAV 재생
# ════════════════════════════════════════════════════════════════
st.divider()
st.markdown("## STEP 3 · 음성 합성 (TTS) & 재생")

# ── 참조 파일 선택 (접힌 상태로 시작) ────────────────────────────
with st.expander(
    "🎤 참조 음성 파일 변경 (선택 · 미입력 시 기본값: assets/Donald_Trump_VoiceSample.wav)",
    expanded=False,
):
    tts_ref_audio = st.file_uploader(
        "참조 음성 파일 (ref_audio_file)",
        type=["mp3", "wav", "m4a", "ogg", "flac", "webm"],
        key="tts_ref_audio",
        help="업로드하지 않으면 서버의 assets/Donald_Trump_VoiceSample.wav 를 사용합니다.",
    )
    if tts_ref_audio:
        st.audio(tts_ref_audio, format=f"audio/{tts_ref_audio.name.rsplit('.', 1)[-1]}")
        st.caption(f"선택된 파일: {tts_ref_audio.name}")

with st.expander(
    "📄 참조 텍스트 파일 변경 (선택 · 미입력 시 기본값: assets/ref_file.txt)",
    expanded=False,
):
    tts_ref_text_file = st.file_uploader(
        "참조 텍스트 파일 (ref_file, .txt)",
        type=["txt"],
        key="tts_ref_file",
        help="업로드하지 않으면 서버의 assets/ref_file.txt 를 사용합니다.",
    )
    if tts_ref_text_file:
        preview = tts_ref_text_file.read().decode("utf-8", errors="replace")
        tts_ref_text_file.seek(0)
        st.caption(f"선택된 파일: {tts_ref_text_file.name}")
        st.text(preview[:200] + ("..." if len(preview) > 200 else ""))

tts_btn = st.button(
    "▶ TTS 생성",
    disabled=(char_count == 0),
    use_container_width=True,
    type="primary",
)

if tts_btn:
    if not edited_text.strip():
        st.warning("텍스트를 입력하거나 STEP 1에서 STT를 먼저 실행하세요.")
    else:
        # 텍스트를 TXT 파일로 변환
        base_name = audio_file.name.rsplit(".", 1)[0] if audio_file else "input"
        txt_filename = f"{base_name}.txt"
        txt_bytes = edited_text.strip().encode("utf-8")

        with st.spinner("음성을 합성 중... (수 분 소요될 수 있습니다)"):
            try:
                files = {
                    "file": (txt_filename, io.BytesIO(txt_bytes), "text/plain"),
                }
                if tts_ref_audio:
                    tts_ref_audio.seek(0)
                    files["ref_audio_file"] = (
                        tts_ref_audio.name,
                        tts_ref_audio.read(),
                        tts_ref_audio.type or "audio/wav",
                    )
                if tts_ref_text_file:
                    tts_ref_text_file.seek(0)
                    files["ref_file"] = (
                        tts_ref_text_file.name,
                        tts_ref_text_file.read(),
                        "text/plain",
                    )
                resp = requests.post(
                    f"{API_BASE}/tts",
                    files=files,
                    timeout=600,
                )
                if resp.ok:
                    st.session_state.wav_bytes = resp.content
                    st.session_state.wav_filename = (
                        resp.headers.get("content-disposition", "")
                        .split("filename=")[-1]
                        .strip('"')
                        or f"{base_name}_output.wav"
                    )
                    gen_time = resp.headers.get("X-Generation-Time", "")
                    st.session_state.tts_elapsed = gen_time
                    st.success("TTS 완료!")
                else:
                    detail = resp.json().get("detail", resp.text)
                    st.error(f"TTS 실패 ({resp.status_code}): {detail}")
            except requests.exceptions.ConnectionError:
                st.error(
                    "❌ 서버에 연결할 수 없습니다. 사이드바에서 서버 URL을 확인하세요."
                )
            except Exception as e:
                st.error(f"❌ 오류: {e}")

if st.session_state.wav_bytes:
    if st.session_state.tts_elapsed:
        st.metric("TTS 소요 시간", st.session_state.tts_elapsed)

    st.markdown("#### 🔊 생성된 음성")
    st.audio(st.session_state.wav_bytes, format="audio/wav")

    st.download_button(
        label="⬇️ WAV 파일 다운로드",
        data=st.session_state.wav_bytes,
        file_name=st.session_state.wav_filename,
        mime="audio/wav",
        use_container_width=True,
    )
