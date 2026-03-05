# STT → TTS 파이프라인 서비스 개발 계획

## 개요

`streamlit/voicecopy.py`를 단일 페이지로 구현합니다.
수직 플로우로 ① 오디오 업로드 → ② `/stt` 호출 및 전사 텍스트 표시 → ③ 텍스트 편집 → ④ `/tts` 호출 및 WAV 재생/다운로드 순서로 진행합니다.
`requests` 라이브러리로 `http://127.0.0.1:8000`에 연결, `st.session_state`로 STT 결과를 TTS 단계로 전달합니다.
탭 없이 구분선(divider)과 섹션 헤더만 사용합니다.

---

## 개발 단계

### Step 1. 파일 신규 작성

- 대상 파일: `streamlit/voicecopy.py` (현재 비어있음)
- 전체 내용을 새로 작성

---

### Step 2. 상단 공통 구성

- `API_BASE = "http://127.0.0.1:8000"` 상수 정의 (사이드바에서 변경 가능)
- `/health` 호출 → `st.success` / `st.error` 뱃지로 서버 상태 표시
- `st.session_state` 키 초기화
  - `stt_text` : STT 전사 텍스트
  - `wav_bytes` : TTS 생성된 WAV 바이트
  - `wav_filename` : 다운로드용 파일명

---

### Step 3. [STEP 1] 오디오 업로드 & STT 실행

- `st.file_uploader` — 허용 타입: `mp3, wav, m4a, ogg, flac, webm`
- "▶ STT 실행" 버튼 클릭 시
  - `requests.post("/stt", files={"file": ...})` 호출
  - `st.spinner`로 처리 중 표시
  - 응답 JSON의 `text` 를 `st.session_state.stt_text`에 저장
  - `st.metric`으로 소요 시간(`elapsed_sec`) 표시

---

### Step 4. [STEP 2] 전사 텍스트 확인 & 편집

- `st.text_area("전사 결과", value=st.session_state.stt_text)`
  - 사용자가 직접 수정 가능 (TTS에 넘길 텍스트 편집)
- `st.divider()` 로 구간 시각 구분

---

### Step 5. [STEP 3] TTS 실행 & WAV 재생

- "▶ TTS 생성" 버튼 클릭 시
  - 텍스트를 인메모리 `.txt` bytes로 변환
  - `requests.post("/tts", files={"file": (filename+".txt", text_bytes, "text/plain")})` 호출
  - 응답 bytes를 `st.session_state.wav_bytes`에 저장
  - `X-Generation-Time` 헤더로 소요 시간 표시
- **`st.audio(wav_bytes, format="audio/wav")`** — 브라우저에서 즉시 재생
- **`st.download_button`** — WAV 파일 다운로드

---

### Step 6. 에러 처리

- 서버 미연결 시 `st.error`로 안내 메시지 출력
- HTTP 4xx / 5xx 시 응답 `detail` 메시지 표시
- 파일 미선택 및 빈 텍스트 업로드 방지 (버튼 비활성 또는 경고)

---

## 설계 결정 사항

| 항목           | 결정 내용                                                  |
| -------------- | ---------------------------------------------------------- |
| STT / TTS 구분 | 탭 대신 `st.divider()` + 번호 헤더(STEP 1/2/3) 사용        |
| TTS 입력       | STT 텍스트 자동 채움 + 수동 편집 모두 허용                 |
| WAV 출력       | `st.audio` 즉시 재생 + `st.download_button` 저장 동시 제공 |
| 서버 URL       | 사이드바 입력란으로 변경 가능하게 구성                     |

---

## API 명세 요약

### `POST /stt`

- **Request:** `multipart/form-data` — `file`: 오디오 파일 (mp3, wav, m4a, ogg, flac, webm)
- **Response:**
  ```json
  {
    "filename": "Leejamsample.mp3",
    "text": "전사된 텍스트...",
    "elapsed_sec": 3.14
  }
  ```

### `POST /tts`

- **Request:** `multipart/form-data` — `file`: `.txt` 파일 (UTF-8)
- **Response:** `audio/wav` 바이너리 스트림, 헤더 `X-Generation-Time: <seconds>s`

---

## 실행 명령어

```powershell
# FastAPI 서버 기동
.\.venv\Scripts\python.exe -m uvicorn api.tts_qwen3_fastapi:app --host 127.0.0.1 --port 8000 --reload

# Streamlit 앱 기동
.\.venv\Scripts\python.exe -m streamlit run streamlit/voicecopy.py
```

---

## 검증 시나리오

1. FastAPI 서버 실행 상태에서 Streamlit 앱 기동
2. `Leejamsample.mp3` 업로드 → STT 결과 텍스트 확인
3. 텍스트 그대로 또는 수정 후 TTS 실행 → 브라우저 내 WAV 재생 확인
4. WAV 파일 다운로드 확인
5. 서버 미기동 상태에서 접속 시 에러 메시지 정상 출력 확인
