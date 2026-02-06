"""
Qwen3-TTS MCP Server
MCP (Model Context Protocol) stdio-based server for Qwen3-TTS voice cloning
"""

import json
import os
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

import soundfile as sf
import torch

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# MCP Protocol Implementation
MODEL_PATH = "Qwen/Qwen3-TTS-12Hz-1.7B-Base"
PROJECT_ROOT = Path(__file__).parent

# Global model instance
tts_model = None


def load_model():
    """Load TTS model on first use"""
    global tts_model
    if tts_model is None:
        # Import here to avoid stdout pollution during server startup
        from qwen_tts import Qwen3TTSModel

        # sys.stdout is already redirected to null in main()
        tts_model = Qwen3TTSModel.from_pretrained(
            MODEL_PATH,
            device_map="cpu",
            dtype=torch.float32,
            attn_implementation="eager",
        )


def generate_voice(
    text: str, voice_style: str = "trump", language: str = "Auto"
) -> dict:
    """Generate voice from text"""
    if tts_model is None:
        load_model()

    # # Normalize input types
    # if isinstance(text, dict) and "text" in text:
    #     text = text["text"]
    # elif isinstance(text, (list, tuple)):
    #     text = "\n".join([str(item) for item in text])
    # elif isinstance(text, (bytes, bytearray)):
    #     text = text.decode("utf-8", errors="replace")

    # if not isinstance(text, str):
    #     text = str(text)

    # if isinstance(language, (list, tuple)):
    #     language = language[0] if language else "Auto"
    # elif isinstance(language, (bytes, bytearray)):
    #     language = language.decode("utf-8", errors="replace")

    text = text.strip()
    if not text:
        return {"success": False, "error": "Input text is empty"}

    try:
        # FIX: Write text to temp file and read back to create fresh str object
        # This resolves TextEncodeInput type error from MCP protocol
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", suffix=".txt", delete=False
        ) as tmp:
            tmp.write(text)
            tmp_path = tmp.name

        try:
            with open(tmp_path, encoding="utf-8") as f:
                text = f.read().strip()
        finally:
            os.unlink(tmp_path)

        # Select reference audio based on voice style
        if voice_style.lower() == "trump":
            ref_audio_path = PROJECT_ROOT / "assets" / "Donald_Trump_VoiceSample.wav"
            ref_text = "Thank you very much. A short time ago, the U.S. military carried out massive precision strikes on the three key nuclear facilities."
        elif voice_style.lower() == "leejemyung":
            ref_audio_path = PROJECT_ROOT / "assets" / "Leejamsample.mp3"
            ref_text = "유연의 지원과 도움의 힘입어 성장한 우리 대한민국은 이제 민주주의 회복의 경험과 역사를 아낌없이 나누는 선도국가로서의 역할을 마다하지 않겠습니다."
        else:
            return {"success": False, "error": f"Unknown voice style: {voice_style}"}

        if not ref_audio_path.exists():
            return {
                "success": False,
                "error": f"Reference audio not found: {ref_audio_path}",
            }

        # Generate speech
        t0 = time.time()

        # sys.stdout is already redirected to null in main()
        wavs, sr = tts_model.generate_voice_clone(
            text=text,
            language=language,
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

        # Save files with timestamp
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        output_dir = PROJECT_ROOT / "output_wav"
        input_dir = PROJECT_ROOT / "input_txt"
        output_dir.mkdir(exist_ok=True)
        input_dir.mkdir(exist_ok=True)

        # Generate filenames
        base_name = f"{voice_style}_mcp_{timestamp}"
        txt_path = input_dir / f"{base_name}.txt"
        audio_path = output_dir / f"{base_name}.wav"

        # Save input text
        txt_path.write_text(text, encoding="utf-8")

        # Convert wavs to numpy array if needed
        import numpy as np

        if isinstance(wavs, torch.Tensor):
            audio_data = wavs.cpu().numpy()
        else:
            audio_data = np.array(wavs)

        # Handle shape
        if len(audio_data.shape) == 3:
            audio_data = audio_data[0, 0, :]
        elif len(audio_data.shape) == 2:
            audio_data = audio_data[0, :]
        elif len(audio_data.shape) == 1:
            pass
        else:
            return {
                "success": False,
                "error": f"Unexpected audio shape: {audio_data.shape}",
            }

        # Ensure sr is int
        sr_int = int(sr) if not isinstance(sr, int) else sr

        # Save using soundfile
        sf.write(str(audio_path), audio_data, sr_int)

        return {
            "success": True,
            "audio_file": str(audio_path),
            "text_file": str(txt_path),
            "duration": float(len(audio_data) / sr_int),
            "sample_rate": sr_int,
            "generation_time": float(generation_time),
        }

    except Exception as e:
        import traceback

        error_msg = str(e)
        error_trace = traceback.format_exc()

        return {"success": False, "error": error_msg, "traceback": error_trace}


def list_voices() -> dict:
    """List available voice styles"""
    return {
        "voices": [
            {
                "name": "trump",
                "description": "Donald Trump voice",
                "language": "english",
            },
            {
                "name": "leejemyung",
                "description": "Lee Jae-myung voice (이재명)",
                "language": "korean",
            },
        ]
    }


def process_request(request: dict) -> dict:
    """Process MCP request"""
    method = request.get("method")
    params = request.get("params", {})
    request_id = request.get("id")

    try:
        if method == "initialize":
            # MCP initialization handshake
            result = {
                "protocolVersion": "2024-11-05",
                "serverInfo": {"name": "qwen3tts", "version": "0.0.4"},
                "capabilities": {"tools": {}},
            }
        elif method == "initialized":
            # Client has finished initializing
            return None  # No response needed for notification
        elif method == "tools/list":
            result = {
                "tools": [
                    {
                        "name": "generate_voice",
                        "description": "Generate voice from text using voice cloning",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "text": {
                                    "type": "string",
                                    "description": "Text to convert to speech",
                                },
                                "voice_style": {
                                    "type": "string",
                                    "description": "Voice style (trump, leejemyung)",
                                },
                                "language": {
                                    "type": "string",
                                    "description": "Language (Auto, english, zh, korean, etc)",
                                },
                            },
                            "required": ["text"],
                        },
                    },
                    {
                        "name": "list_voices",
                        "description": "List available voice styles",
                        "inputSchema": {"type": "object", "properties": {}},
                    },
                ]
            }
        elif method == "tools/call":
            tool_name = params.get("name")
            tool_params = params.get("arguments", {})

            if tool_name == "generate_voice":
                result_data = generate_voice(
                    text=tool_params.get("text", ""),
                    voice_style=tool_params.get("voice_style", "trump"),
                    language=tool_params.get("language", "Auto"),
                )
                # Return MCP-compatible format
                result = {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(
                                result_data, ensure_ascii=False, indent=2
                            ),
                        }
                    ]
                }
            elif tool_name == "list_voices":
                result_data = list_voices()
                result = {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(
                                result_data, ensure_ascii=False, indent=2
                            ),
                        }
                    ]
                }
            else:
                return {
                    "error": {"code": -32602, "message": f"Unknown tool: {tool_name}"},
                    "id": request_id,
                }
        else:
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32601, "message": f"Unknown method: {method}"},
                "id": request_id,
            }

        return {"jsonrpc": "2.0", "result": result, "id": request_id}

    except Exception as e:
        return {
            "jsonrpc": "2.0",
            "error": {"code": -32603, "message": str(e)},
            "id": request_id,
        }


def main():
    """Main MCP server loop"""
    # Save real stdout file descriptor to write JSON responses
    # This prevents library progress bars from polluting JSON-RPC output
    real_stdout_fd = os.dup(sys.stdout.fileno())
    real_stdout = os.fdopen(real_stdout_fd, "w", encoding="utf-8")

    # Redirect sys.stdout to null to suppress library output
    null_fd = os.open(os.devnull, os.O_RDWR)
    os.dup2(null_fd, sys.stdout.fileno())
    os.close(null_fd)

    # Don't pre-load model - load on first use instead

    try:
        while True:
            try:
                # Read request from stdin
                line = sys.stdin.readline()
                if not line:
                    break

                request = json.loads(line)
                response = process_request(request)

                # Write response to real stdout (skip if None for notifications)
                if response is not None:
                    real_stdout.write(json.dumps(response) + "\n")
                    real_stdout.flush()

            except json.JSONDecodeError:
                continue
            except KeyboardInterrupt:
                break
            except Exception as e:
                error_response = {
                    "jsonrpc": "2.0",
                    "error": {"code": -32603, "message": str(e)},
                    "id": None,
                }
                real_stdout.write(json.dumps(error_response) + "\n")
                real_stdout.flush()
    finally:
        real_stdout.close()


if __name__ == "__main__":
    main()
