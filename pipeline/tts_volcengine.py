"""火山引擎豆包语音合成 V3（HTTP SSE 单向流式）。"""

from __future__ import annotations

import base64
import json
import os
import uuid
import urllib.error
import urllib.request
from pathlib import Path

from .models import TtsConfig
from .text_preprocess import fix_pronunciation_for_tts

API_URL = "https://openspeech.bytedance.com/api/v3/tts/unidirectional/sse"
DEFAULT_RESOURCE_ID = "seed-tts-2.0"
DEFAULT_SPEAKER = "zh_male_ruyaqingnian_uranus_bigtts"  # 儒雅青年 2.0


def _api_key() -> str | None:
    for name in (
        "VOLCENGINE_TTS_API_KEY",
        "DOUBAO_TTS_API_KEY",
        "VOLCENGINE_API_KEY",
        "BYTEPLUS_TTS_API_KEY",
    ):
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return None


def _legacy_credentials() -> tuple[str, str]:
    appid = (
        os.environ.get("DOUBAO_TTS_APPID", "").strip()
        or os.environ.get("VOLCENGINE_TTS_APPID", "").strip()
    )
    token = (
        os.environ.get("DOUBAO_TTS_TOKEN", "").strip()
        or os.environ.get("VOLCENGINE_TTS_ACCESS_TOKEN", "").strip()
        or os.environ.get("DOUBAO_TTS_ACCESS_TOKEN", "").strip()
    )
    return appid, token


def volcengine_env_status() -> str:
    """用于错误提示：哪些变量已设置（不暴露值）。"""
    checks = [
        "VOLCENGINE_API_KEY",
        "VOLCENGINE_TTS_API_KEY",
        "DOUBAO_TTS_API_KEY",
        "DOUBAO_TTS_APPID",
        "DOUBAO_TTS_TOKEN",
        "DOUBAO_TTS_RESOURCE_ID",
    ]
    lines = []
    for name in checks:
        val = os.environ.get(name, "").strip()
        lines.append(f"  {name}: {'已设置' if val else '未设置'}")
    return "\n".join(lines)


def _resource_id(tts: TtsConfig) -> str:
    return (
        (tts.resource_id or "").strip()
        or os.environ.get("DOUBAO_TTS_RESOURCE_ID", "").strip()
        or DEFAULT_RESOURCE_ID
    )


def parse_volcengine_speech_rate(rate: str) -> int:
    """edge 风格 '-5%' -> 火山 speech_rate [-50, 100]。"""
    rate = (rate or "0").strip()
    if rate.endswith("%"):
        return max(-50, min(100, int(round(float(rate[:-1])))))
    try:
        return max(-50, min(100, int(rate)))
    except ValueError:
        return 0


def _build_headers(tts: TtsConfig) -> dict[str, str]:
    resource_id = _resource_id(tts)
    headers = {
        "X-Api-Resource-Id": resource_id,
        "X-Api-Request-Id": str(uuid.uuid4()),
        "Content-Type": "application/json",
    }
    api_key = _api_key()
    if api_key:
        headers["X-Api-Key"] = api_key
        return headers
    appid, token = _legacy_credentials()
    if appid and token:
        headers["X-Api-App-Id"] = appid
        headers["X-Api-Access-Key"] = token
        return headers
    raise RuntimeError(
        "未配置火山豆包 TTS 凭证。请在项目根目录 .env 中设置并保存（Cmd+S）：\n"
        "  新版：VOLCENGINE_TTS_API_KEY=控制台API_Key\n"
        "  旧版：DOUBAO_TTS_APPID=... 与 DOUBAO_TTS_TOKEN=...\n"
        "获取：火山控制台 → 豆包语音 → 应用管理（不是方舟大模型的 Key）\n"
        "当前 .env 检测结果：\n"
        f"{volcengine_env_status()}"
    )


def _speaker_id(tts: TtsConfig) -> str:
    voice = (tts.voice or "").strip()
    if voice and not voice.startswith("zh-CN-"):
        return voice
    return DEFAULT_SPEAKER


def _parse_sse_audio(resp) -> bytes:
    audio_chunks: list[bytes] = []
    buffer = b""
    while True:
        chunk = resp.read(4096)
        if not chunk:
            break
        buffer += chunk
        while b"\n" in buffer:
            line, buffer = buffer.split(b"\n", 1)
            line = line.strip()
            if not line or line.startswith(b"event:"):
                continue
            if not line.startswith(b"data:"):
                continue
            raw = line[5:].strip()
            if not raw:
                continue
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError:
                continue
            code = obj.get("code", 0)
            if code == 20000000:
                continue
            if code and code != 0:
                raise RuntimeError(
                    f"豆包 TTS 错误 (code={code}): {obj.get('message', obj)}"
                )
            audio_b64 = obj.get("data")
            if audio_b64:
                audio_chunks.append(base64.b64decode(audio_b64))
    if not audio_chunks:
        raise RuntimeError("豆包 TTS 未返回音频数据")
    return b"".join(audio_chunks)


def synthesize_volcengine(text: str, tts: TtsConfig, out_path: Path) -> None:
    # 预处理文本，修正发音问题
    processed_text = fix_pronunciation_for_tts(text, provider="volcengine")
    
    speaker = _speaker_id(tts)
    audio_params: dict = {
        "format": "mp3",
        "sample_rate": 24000,
        "speech_rate": parse_volcengine_speech_rate(tts.rate),
        "loudness_rate": 0,
        "disable_markdown_filter": True,
    }
    emotion = (tts.emotion or "").strip()
    if emotion:
        audio_params["emotion"] = emotion

    payload = {
        "user": {"uid": "ai_youtuber"},
        "req_params": {
            "text": processed_text,  # 使用处理后的文本
            "speaker": speaker,
            "audio_params": audio_params,
        },
    }
    headers = _build_headers(tts)
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(API_URL, data=data, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            audio = _parse_sse_audio(resp)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"豆包 TTS HTTP {exc.code}: {detail[:800]}") from exc

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(audio)
