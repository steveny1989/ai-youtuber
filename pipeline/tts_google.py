"""Google TTS：Gemini API（AI Studio Key）与 Cloud Text-to-Speech。"""

from __future__ import annotations

import base64
import json
import os
import subprocess
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

from .ffmpeg_util import require_ffmpeg
from .models import TtsConfig

GEMINI_TTS_DEFAULT_MODEL = "gemini-2.5-flash-preview-tts"
GEMINI_TTS_DEFAULT_VOICE = "Charon"
GOOGLE_CLOUD_DEFAULT_VOICE = "zh-CN-Neural2-C"
GEMINI_PCM_SAMPLE_RATE = 24000


def google_api_key() -> str | None:
    for name in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return None


def parse_speaking_rate(rate: str) -> float:
    rate = (rate or "+0%").strip()
    if rate.endswith("%"):
        return max(0.25, min(4.0, 1.0 + float(rate[:-1]) / 100.0))
    return max(0.25, min(4.0, float(rate)))


def _pcm_to_mp3(pcm: bytes, out_path: Path, *, sample_rate: int = GEMINI_PCM_SAMPLE_RATE) -> None:
    ffmpeg = require_ffmpeg()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".pcm", delete=False) as tmp:
        tmp.write(pcm)
        pcm_path = tmp.name
    try:
        subprocess.run(
            [
                ffmpeg,
                "-y",
                "-f",
                "s16le",
                "-ar",
                str(sample_rate),
                "-ac",
                "1",
                "-i",
                pcm_path,
                "-c:a",
                "libmp3lame",
                "-q:a",
                "2",
                str(out_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    finally:
        Path(pcm_path).unlink(missing_ok=True)


def _http_post_json(url: str, body: dict, *, headers: dict | None = None) -> dict:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", **(headers or {})},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Google TTS HTTP {exc.code}: {detail[:800]}") from exc


def _extract_gemini_audio(payload: dict) -> bytes:
    for candidate in payload.get("candidates", []):
        content = candidate.get("content") or {}
        for part in content.get("parts", []):
            inline = part.get("inlineData") or part.get("inline_data")
            if not inline:
                continue
            raw = inline.get("data")
            if not raw:
                continue
            if isinstance(raw, str):
                return base64.b64decode(raw)
            if isinstance(raw, (bytes, bytearray)):
                return bytes(raw)
    raise RuntimeError(f"Gemini TTS 响应无音频: {json.dumps(payload, ensure_ascii=False)[:500]}")


def synthesize_gemini(text: str, tts: TtsConfig, out_path: Path) -> None:
    api_key = google_api_key()
    if not api_key:
        raise RuntimeError(
            "未设置 GEMINI_API_KEY 或 GOOGLE_API_KEY。"
            "在 https://aistudio.google.com/apikey 创建后 export GEMINI_API_KEY=..."
        )

    model = tts.model or GEMINI_TTS_DEFAULT_MODEL
    voice = tts.voice if tts.voice and not tts.voice.startswith("zh-CN-") else GEMINI_TTS_DEFAULT_VOICE
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={api_key}"
    )
    rate = parse_speaking_rate(tts.rate)
    pace_hint = ""
    if rate < 0.98:
        pace_hint = "请用略慢、沉稳的语速朗读以下旁白原文，不要添加任何解释或前后缀，只朗读原文：\n"
    elif rate > 1.02:
        pace_hint = "请用略快的语速朗读以下旁白原文，不要添加任何解释或前后缀，只朗读原文：\n"

    body = {
        "contents": [{"parts": [{"text": f"{pace_hint}{text}"}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {
                    "prebuiltVoiceConfig": {"voiceName": voice},
                },
            },
        },
    }
    payload = _http_post_json(url, body)
    pcm = _extract_gemini_audio(payload)
    _pcm_to_mp3(pcm, out_path)


def synthesize_google_cloud(text: str, tts: TtsConfig, out_path: Path) -> None:
    api_key = google_api_key()
    voice = tts.voice if tts.voice and tts.voice.startswith("zh-") else GOOGLE_CLOUD_DEFAULT_VOICE
    if tts.language_code:
        language_code = tts.language_code
    elif voice.count("-") >= 1:
        parts = voice.split("-")
        language_code = f"{parts[0]}-{parts[1]}"
    else:
        language_code = "zh-CN"

    if api_key:
        url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={api_key}"
        body = {
            "input": {"text": text},
            "voice": {"languageCode": language_code, "name": voice},
            "audioConfig": {
                "audioEncoding": "MP3",
                "speakingRate": parse_speaking_rate(tts.rate),
            },
        }
        payload = _http_post_json(url, body)
        out_path.write_bytes(base64.b64decode(payload["audioContent"]))
        return

    try:
        from google.cloud import texttospeech
    except ImportError as exc:
        raise RuntimeError(
            "Cloud TTS 需要 GEMINI_API_KEY/GOOGLE_API_KEY，或安装 google-cloud-texttospeech "
            "并配置 GOOGLE_APPLICATION_CREDENTIALS"
        ) from exc

    client = texttospeech.TextToSpeechClient()
    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice_params = texttospeech.VoiceSelectionParams(
        language_code=language_code,
        name=voice,
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3,
        speaking_rate=parse_speaking_rate(tts.rate),
    )
    response = client.synthesize_speech(
        input=synthesis_input,
        voice=voice_params,
        audio_config=audio_config,
    )
    out_path.write_bytes(response.audio_content)


def synthesize_google(text: str, tts: TtsConfig, out_path: Path) -> None:
    provider = (tts.provider or "gemini").lower()
    if provider in ("gemini", "google", "google_gemini"):
        synthesize_gemini(text, tts, out_path)
    elif provider in ("google_cloud", "gcp", "cloud"):
        synthesize_google_cloud(text, tts, out_path)
    else:
        raise ValueError(f"未知 Google TTS provider: {tts.provider}")
