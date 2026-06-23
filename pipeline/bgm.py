"""将 assets/BGM 配乐混入成片（循环、分段 crossfade、首尾淡入淡出）。"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .ffmpeg_util import probe_duration_sec, require_ffmpeg
from .models import BgmConfig, RenderedScene


@dataclass
class BgmSwitch:
    time_sec: float
    scene_id: str


def _resolve_tracks(project_root: Path, tracks: list[str]) -> list[Path]:
    paths: list[Path] = []
    for rel in tracks:
        p = (project_root / rel).resolve()
        if not p.exists():
            raise FileNotFoundError(f"BGM 文件不存在: {p}")
        paths.append(p)
    return paths


def scene_switch_times(
    rendered_scenes: list[RenderedScene],
    switch_at_scene: str,
) -> list[BgmSwitch]:
    """在指定镜头起点切换 BGM（用于多轨 crossfade）。"""
    if not switch_at_scene.strip():
        return []
    cursor = 0.0
    for rs in rendered_scenes:
        scene = rs.scene
        dur = rs.audio_duration_sec + scene.pause_after_sec
        if scene.id == switch_at_scene:
            return [BgmSwitch(time_sec=cursor, scene_id=scene.id)]
        cursor += dur
    return []


def _build_switch_times(
    total_duration: float,
    rendered_scenes: list[RenderedScene],
    config: BgmConfig,
    n_tracks: int,
) -> list[float]:
    """返回每条音轨的起始时间（秒），长度 = n_tracks。"""
    if n_tracks <= 1:
        return [0.0]
    explicit = scene_switch_times(rendered_scenes, config.switch_at_scene)
    if explicit:
        times = [0.0, explicit[0].time_sec]
        while len(times) < n_tracks:
            times.append(total_duration)
        return times[:n_tracks]
    # 默认：均分，在分界点 crossfade
    step = total_duration / n_tracks
    return [step * i for i in range(n_tracks)]


def mix_bgm_into_video(
    video_path: Path,
    project_root: Path,
    config: BgmConfig,
    rendered_scenes: list[RenderedScene],
    *,
    out_path: Path | None = None,
) -> Path:
    if not config.enabled:
        if out_path and out_path.resolve() != video_path.resolve():
            shutil.copy2(video_path, out_path)
            return out_path
        return video_path

    tracks = _resolve_tracks(project_root, config.tracks)
    if not tracks:
        return video_path

    duration = probe_duration_sec(video_path)
    if duration <= 0:
        raise RuntimeError(f"无法读取视频时长: {video_path}")

    out = out_path or video_path
    tmp_out = out.with_suffix(".bgm.tmp.mp4") if out == video_path else out
    ffmpeg = require_ffmpeg()

    cf = max(0.5, config.crossfade_sec)
    fade_in = max(0.0, config.fade_in_sec)
    fade_out = max(0.0, config.fade_out_sec)
    vol = max(0.01, min(1.0, config.volume))

    switch_times = _build_switch_times(duration, rendered_scenes, config, len(tracks))

    # 每段 BGM：从 switch_i 到 switch_{i+1}（最后到片尾），加 crossfade 余量并循环
    seg_ends = list(switch_times[1:]) + [duration]
    parts: list[str] = []
    inputs = ["-i", str(video_path)]
    for i, track in enumerate(tracks):
        inputs.extend(["-i", str(track)])

    labels: list[str] = []
    for i, track in enumerate(tracks):
        start = switch_times[i]
        end = seg_ends[i]
        seg_len = max(0.5, end - start + (cf if i < len(tracks) - 1 else 0))
        label = f"bg{i}"
        parts.append(
            f"[{i + 1}:a]aloop=loop=-1:size=2e+09,atrim=0:{seg_len:.3f},"
            f"asetpts=PTS-STARTPTS[{label}]"
        )
        labels.append(f"[{label}]")

    if len(labels) == 1:
        bed = labels[0]
    else:
        bed = labels[0]
        for j in range(1, len(labels)):
            out_label = f"xf{j}"
            parts.append(f"{bed}{labels[j]}acrossfade=d={cf:.3f}:c1=tri:c2=tri[{out_label}]")
            bed = f"[{out_label}]"

    fade_out_start = max(0.0, duration - fade_out)
    parts.append(
        f"{bed}afade=t=in:st=0:d={fade_in:.3f},"
        f"afade=t=out:st={fade_out_start:.3f}:d={fade_out:.3f},"
        f"volume={vol:.4f}[bgm]"
    )
    parts.append(
        "[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=2:normalize=0[aout]"
    )
    filter_complex = ";".join(parts)

    cmd = [
        ffmpeg,
        "-y",
        *inputs,
        "-filter_complex",
        filter_complex,
        "-map",
        "0:v",
        "-map",
        "[aout]",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-ar",
        "44100",
        "-b:a",
        "192k",
        "-movflags",
        "+faststart",
        str(tmp_out),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"BGM 混音失败:\n{result.stderr[-2500:]}")

    if tmp_out != out:
        tmp_out.replace(out)
    return out
