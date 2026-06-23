"""每镜一条配音 + 对齐时间轴字幕。"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from .ffmpeg_util import probe_duration_sec
from .models import StyleConfig

CUES_VERSION = "align_v1"


@dataclass
class SubtitleCue:
    text: str
    start: float
    end: float


def split_sentences(text: str, *, max_chars: int = 26) -> list[str]:
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
    if isinstance(data, list):
        return [SubtitleCue(**item) for item in data]
    if data.get("version") != CUES_VERSION:
        return []
    return [SubtitleCue(**item) for item in data.get("cues", [])]


def save_cues(path: Path, cues: list[SubtitleCue]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": CUES_VERSION,
        "cues": [
            {"text": c.text, "start": round(c.start, 3), "end": round(c.end, 3)}
            for c in cues
        ],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def cues_are_valid(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    if isinstance(data, list):
        return False
    return data.get("version") == CUES_VERSION and bool(data.get("cues"))


def align_cues_to_duration(narration: str, duration: float) -> list[SubtitleCue]:
    """按句切分 + 字数比例分配时长（每镜一条 mp3 对齐）。"""
    sentences = split_sentences(narration)
    if not sentences:
        text = narration.strip()
        if not text or duration <= 0:
            return []
        return [SubtitleCue(text=text, start=0.0, end=duration)]

    weights = [max(1, len(s)) for s in sentences]
    total = sum(weights)
    cues: list[SubtitleCue] = []
    cursor = 0.0
    for sentence, weight in zip(sentences, weights):
        seg = duration * weight / total
        cues.append(SubtitleCue(text=sentence, start=cursor, end=cursor + seg))
        cursor += seg
    if cues:
        cues[-1] = SubtitleCue(cues[-1].text, cues[-1].start, duration)
    return cues


def build_cues_for_audio(narration: str, audio_path: Path) -> list[SubtitleCue]:
    duration = probe_duration_sec(audio_path)
    cues = align_cues_to_duration(narration, duration)
    save_cues(cues_path_for(audio_path), cues)
    return cues


def generate_scene_audio_and_cues(
    narration: str,
    audio_path: Path,
    tts_config,
) -> list[SubtitleCue]:
    """每镜一次 TTS，再从整段 mp3 时长对齐句级 cues。"""
    from .tts import generate_scene_audio

    generate_scene_audio(narration, audio_path, tts_config)
    return build_cues_for_audio(narration, audio_path)


def build_drawtext_chain(
    cues: list[SubtitleCue],
    style: StyleConfig,
    font_path: str,
    work_dir: Path,
    scene_id: str,
) -> tuple[str, str] | None:
    """drawtext 链（部分 ffmpeg 构建无此滤镜时不用）。"""
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
