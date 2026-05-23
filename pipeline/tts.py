from __future__ import annotations

import asyncio
import time
from pathlib import Path

from .ffmpeg_util import create_silent_audio
from .models import Storyboard, TtsConfig
from .subtitle_timing import cues_path_for, generate_timed_audio


async def _synthesize(text: str, voice: str, rate: str, out_path: Path) -> None:
    import edge_tts

    communicate = edge_tts.Communicate(text, voice=voice, rate=rate)
    await communicate.save(str(out_path))


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
            asyncio.run(_synthesize(narration, tts.voice, tts.rate, out_path))
            if out_path.stat().st_size > 500:
                return
        except Exception as exc:
            last_err = exc
            time.sleep(1.5 * (attempt + 1))
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
                and cues_file.exists()
            ):
                paths[scene.id] = path
                continue
            generate_timed_audio(scene.narration, path, storyboard.tts)
        else:
            duration = scene.duration_sec or 3.0
            create_silent_audio(duration, path)
        paths[scene.id] = path
    return paths
