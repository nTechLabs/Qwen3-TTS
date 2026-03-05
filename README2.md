qwen3tts 를 이용해서 trumpSpeech.txt 를 trump 음성으로 변환해줘
.venv/bin/python ./examples/trumpVoice.py trumpSpeech.txt

.\.venv\Scripts\python.exe quick_test.py

CLI
.\.venv\Scripts\python.exe .\tts\tts_qwen3_main.py trumpSpeech.txt

.\.venv\Scripts\python.exe .\tts\tts_qwen3_main.py trumpSpeech.txt --ref_audio_file=Donald_Trump_VoiceSample.wav

.\.venv\Scripts\python.exe .\tts\tts_qwen3_main.py trumpSpeech.txt --ref_file=ref_file.txt

fastapi
.\.venv\Scripts\python.exe -m uvicorn api.tts_qwen3_fastapi:app --host 127.0.0.1 --port 8000 --reload

.\.venv\Scripts\python.exe .\stt\whisper_main.py Leejamsample.mp3

streamlit
.\.venv\Scripts\python.exe -m streamlit run streamlit/voicecopy.py 2>&1
