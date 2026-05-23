"""按句 TTS + 时间轴字幕（与配音对齐）。"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .ffmpeg_util import probe_duration_sec, require_ffmpeg
from .models import StyleConfig


@dataclass
class SubtitleCue:
    text: str
    start: float
    end: float


def split_sentences(text: str, *, max_chars: int = 42) -> list[str]:
    text = text.strip()
    if not text:
        return []
    parts = re.split(r"(?<=[。！？!?；\n])", text)
    sentences: list[str] = []
    for part in parts:
        chunk = part.strip()
        if not chunk:
            continue
        if len(chunk) <= max_chars:
            sentences.append(chunk)
            continue
        subparts = re.split(r"(?<=[，,、])", chunk)
        buf = ""
        for sp in subparts:
            sp = sp.strip()
            if not sp:
                continue
            if len(buf) + len(sp) <= max_chars:
                buf += sp
            else:
                if buf:
                    sentences.append(buf)
                buf = sp
        if buf:
            sentences.append(buf)
    return sentences


def cues_path_for(audio_path: Path) -> Path:
    return audio_path.with_suffix(".cues.json")


def load_cues(path: Path) -> list[SubtitleCue]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return [SubtitleCue(**item) for item in data]


def save_cues(path: Path, cues: list[SubtitleCue]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [
        {"text": c.text, "start": round(c.start, 3), "end": round(c.end, 3)}
        for c in cues
    ]
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def generate_timed_audio(
    narration: str,
    audio_path: Path,
    tts_config,
) -> list[SubtitleCue]:
    """逐句配音并拼接，返回与音频对齐的字幕时间轴。"""
    sentences = split_sentences(narration)
    if not sentences:
        sentences = [narration.strip()]

    parts_dir = audio_path.parent / f"{audio_path.stem}_parts"
    parts_dir.mkdir(parents=True, exist_ok=True)

    seg_paths: list[Path] = []
    cues: list[SubtitleCue] = []
    cursor = 0.0

    from .tts import generate_scene_audio

    for idx, sentence in enumerate(sentences):
        seg_path = parts_dir / f"{idx:03d}.mp3"
        generate_scene_audio(sentence, seg_path, tts_config)
        dur = probe_duration_sec(seg_path)
        cues.append(SubtitleCue(text=sentence, start=cursor, end=cursor + dur))
        cursor += dur
        seg_paths.append(seg_path)

    _concat_audio(seg_paths, audio_path)

    save_cues(cues_path_for(audio_path), cues)
    return cues


def _concat_audio(seg_paths: list[Path], out_path: Path) -> None:
    ffmpeg = require_ffmpeg()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if not seg_paths:
        raise ValueError("没有音频片段可拼接")

    if len(seg_paths) == 1:
        shutil.copy2(seg_paths[0], out_path)
        return

    list_file = out_path.parent / f"{out_path.stem}_concat.txt"
    with list_file.open("w", encoding="utf-8") as f:
        for path in seg_paths:
            f.write(f"file '{path.resolve()}'\n")

    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_file),
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


def build_drawtext_chain(
    cues: list[SubtitleCue],
    style: StyleConfig,
    font_path: str,
    work_dir: Path,
    scene_id: str,
) -> tuple[str, str] | None:
    """返回 (filter_complex, 最终视频流标签)。"""
    if not cues or not font_path:
        return None

    margin_bottom = style.subtitle_margin_bottom
    font_size = style.subtitle_font_size
    color = style.subtitle_color.lstrip("#")
    font_color = f"0x{color}FF" if len(color) == 6 else "white"
    y_expr = f"h-{margin_bottom}-text_h"
    fontfile = font_path.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")

    chain: list[str] = []
    label_in = "0:v"
    for i, cue in enumerate(cues):
        label_out = f"vs{i}"
        text_file = work_dir / f"{scene_id}_sub_{i:03d}.txt"
        text_file.write_text(cue.text, encoding="utf-8")
        textfile = str(text_file.resolve()).replace("\\", "\\\\").replace(":", "\\:")
        enable = f"between(t,{cue.start:.3f},{cue.end:.3f})"
        filt = (
            f"[{label_in}]drawtext=fontfile='{fontfile}':textfile='{textfile}':"
            f"fontsize={font_size}:fontcolor={font_color}:"
            f"x=(w-text_w)/2:y={y_expr}:"
            f"shadowcolor=black@0.55:shadowx=2:shadowy=2:"
            f"enable='{enable}'[{label_out}]"
        )
        chain.append(filt)
        label_in = label_out
    return ";".join(chain), label_in
