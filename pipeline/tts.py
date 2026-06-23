from __future__ import annotations

import asyncio
import time
from pathlib import Path

from dataclasses import replace

from .ffmpeg_util import create_silent_audio, is_silent_audio
from .models import Storyboard, TtsConfig
from .subtitle_timing import (
    build_cues_for_audio,
    cues_are_valid,
    cues_path_for,
    generate_scene_audio_and_cues,
)


async def _synthesize(text: str, voice: str, rate: str, out_path: Path) -> None:
    import edge_tts

    communicate = edge_tts.Communicate(text, voice=voice, rate=rate)
    await communicate.save(str(out_path))


def _synthesize_with_provider(text: str, tts: TtsConfig, out_path: Path) -> None:
    provider = (tts.provider or "edge").lower()
    if provider == "edge":
        asyncio.run(_synthesize(text, tts.voice, tts.rate, out_path))
        return
    if provider in ("volcengine", "doubao", "bytedance", "huoshan"):
        from .tts_volcengine import synthesize_volcengine

        synthesize_volcengine(text, tts, out_path)
        return
    if provider in ("gemini", "google", "google_gemini", "google_cloud", "gcp", "cloud"):
        from .tts_google import synthesize_google

        synthesize_google(text, tts, out_path)
        return
    raise ValueError(f"未知 TTS provider: {tts.provider}")


def generate_scene_audio(
    narration: str,
    out_path: Path,
    tts: TtsConfig,
    *,
    max_retries: int = 4,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    last_err: Exception | None = None
    for attempt in range(max_retries):
        try:
            if out_path.exists():
                out_path.unlink()
            _synthesize_with_provider(narration, tts, out_path)
            if out_path.stat().st_size > 500:
                return
        except Exception as exc:
            last_err = exc
            time.sleep(1.5 * (attempt + 1))
    provider = (tts.provider or "edge").lower()
    if provider not in ("edge",):
        fallback = replace(
            tts,
            provider="edge",
            voice="zh-CN-YunxiNeural",
            resource_id="",
            emotion="",
        )
        try:
            if out_path.exists():
                out_path.unlink()
            _synthesize_with_provider(narration, fallback, out_path)
            if out_path.stat().st_size > 500:
                return
        except Exception as exc:
            last_err = exc
    raise RuntimeError(f"TTS 失败 ({out_path.name}): {last_err}") from last_err


def generate_all_audio(storyboard: Storyboard, work_dir: Path) -> dict[str, Path]:
    audio_dir = work_dir / "audio"
    paths: dict[str, Path] = {}
    for scene in storyboard.all_scenes():
        path = audio_dir / f"{scene.id}.mp3"
        if scene.narration.strip():
            cues_file = cues_path_for(path)
            if (
                path.exists()
                and path.stat().st_size > 500
                and not is_silent_audio(path)
                and cues_are_valid(cues_file)
            ):
                paths[scene.id] = path
                continue
            if path.exists() and path.stat().st_size > 500 and not is_silent_audio(path):
                build_cues_for_audio(scene.narration, path)
                paths[scene.id] = path
                continue
            generate_scene_audio_and_cues(scene.narration, path, storyboard.tts)
        else:
            duration = scene.duration_sec or 3.0
            create_silent_audio(duration, path)
        paths[scene.id] = path
    return paths
