from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .ffmpeg_util import probe_duration_sec, require_ffmpeg
from .frame import render_frame
from .models import RenderedScene, Storyboard
from .prepare import prepare_storyboard_assets
from .subtitle_timing import SubtitleCue, cues_path_for, load_cues
from .tts import generate_all_audio


def _resolve_image(path_str: str | None, storyboard_path: Path) -> Path | None:
    if not path_str:
        return None
    p = Path(path_str)
    if not p.is_absolute():
        p = (storyboard_path.parent / p).resolve()
        if not p.exists():
            p = (storyboard_path.parent.parent / path_str).resolve()
    return p if p.exists() else None


def _encode_still_video(
    ffmpeg: str,
    frame_path: Path,
    fps: int,
    duration_sec: float,
    out_path: Path,
) -> None:
    frames = max(1, int(duration_sec * fps))
    result = subprocess.run(
        [
            ffmpeg,
            "-y",
            "-loop",
            "1",
            "-framerate",
            str(fps),
            "-i",
            str(frame_path),
            "-frames:v",
            str(frames),
            "-an",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(out_path),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"编码静帧视频失败:\n{result.stderr[-1500:]}")


def _concat_videos(ffmpeg: str, paths: list[Path], out_path: Path) -> None:
    if not paths:
        raise ValueError("没有视频片段可拼接")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if len(paths) == 1:
        shutil.copy2(paths[0], out_path)
        return

    list_file = out_path.parent / f"{out_path.stem}_vconcat.txt"
    with list_file.open("w", encoding="utf-8") as f:
        for path in paths:
            f.write(f"file '{path.resolve()}'\n")

    result = subprocess.run(
        [
            ffmpeg,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_file),
            "-c",
            "copy",
            str(out_path),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"拼接视频失败:\n{result.stderr[-1500:]}")


def _mux_video_audio(
    ffmpeg: str,
    video_path: Path,
    audio_path: Path,
    out_path: Path,
) -> None:
    result = subprocess.run(
        [
            ffmpeg,
            "-y",
            "-i",
            str(video_path),
            "-i",
            str(audio_path),
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-ar",
            "44100",
            "-ac",
            "2",
            "-shortest",
            "-movflags",
            "+faststart",
            str(out_path),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"混流失败:\n{result.stderr[-1500:]}")


def _render_timed_cues_segment(
    rendered: RenderedScene,
    storyboard: Storyboard,
    storyboard_path: Path,
    segments_dir: Path,
    cues: list[SubtitleCue],
    *,
    image: Path | None,
    logo_path: Path | None,
    w: int,
    h: int,
    fps: int,
    segment_path: Path,
) -> Path:
    scene = rendered.scene
    style = storyboard.style
    ffmpeg = require_ffmpeg()

    if scene.pause_after_sec and cues:
        last = cues[-1]
        cues = cues[:-1] + [
            SubtitleCue(last.text, last.start, last.end + scene.pause_after_sec)
        ]

    cue_videos: list[Path] = []
    for i, cue in enumerate(cues):
        dur = max(0.05, cue.end - cue.start)
        frame_path = segments_dir / f"{scene.id}_cue_{i:03d}.png"
        cue_mp4 = segments_dir / f"{scene.id}_cue_{i:03d}.mp4"
        render_frame(
            scene.narration,
            style,
            w,
            h,
            frame_path,
            image_path=image,
            watermark=storyboard.watermark,
            watermark_logo_path=logo_path,
            scene_id=scene.id,
            scene=scene,
            timed_subtitle=cue.text,
        )
        _encode_still_video(ffmpeg, frame_path, fps, dur, cue_mp4)
        cue_videos.append(cue_mp4)

    video_only = segments_dir / f"{scene.id}_video.mp4"
    _concat_videos(ffmpeg, cue_videos, video_only)
    _mux_video_audio(ffmpeg, video_only, rendered.audio_path, segment_path)
    rendered.segment_path = segment_path
    return segment_path


def render_scene_segment(
    rendered: RenderedScene,
    storyboard: Storyboard,
    storyboard_path: Path,
    segments_dir: Path,
) -> Path:
    scene = rendered.scene
    style = storyboard.style
    out = storyboard.output

    duration = scene.duration_sec or rendered.audio_duration_sec
    duration += scene.pause_after_sec

    image = _resolve_image(scene.image, storyboard_path)
    segment_path = segments_dir / f"{scene.id}.mp4"
    w, h, fps = out.width, out.height, out.fps
    logo_path = _resolve_image(storyboard.watermark.image, storyboard_path)

    cues = load_cues(cues_path_for(rendered.audio_path))
    if cues:
        return _render_timed_cues_segment(
            rendered,
            storyboard,
            storyboard_path,
            segments_dir,
            cues,
            image=image,
            logo_path=logo_path,
            w=w,
            h=h,
            fps=fps,
            segment_path=segment_path,
        )

    frame_path = segments_dir / f"{scene.id}_frame.png"
    render_frame(
        scene.narration,
        style,
        w,
        h,
        frame_path,
        image_path=image,
        watermark=storyboard.watermark,
        watermark_logo_path=logo_path,
        scene_id=scene.id,
        scene=scene,
    )

    ffmpeg = require_ffmpeg()
    frame_count = max(1, int(duration * fps))
    cmd = [
        ffmpeg,
        "-y",
        "-loop",
        "1",
        "-framerate",
        str(fps),
        "-i",
        str(frame_path),
        "-i",
        str(rendered.audio_path),
        "-frames:v",
        str(frame_count),
        "-map",
        "0:v",
        "-map",
        "1:a",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-ar",
        "44100",
        "-ac",
        "2",
        "-shortest",
        "-movflags",
        "+faststart",
        str(segment_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"渲染镜头 {scene.id} 失败:\n{result.stderr[-2000:]}"
        )
    rendered.segment_path = segment_path
    return segment_path


def concat_segments(segment_paths: list[Path], output_path: Path) -> Path:
    ffmpeg = require_ffmpeg()
    n = len(segment_paths)
    if n == 0:
        raise ValueError("没有可拼接的镜头")

    inputs: list[str] = []
    for path in segment_paths:
        inputs.extend(["-i", str(path.resolve())])

    stream_refs = "".join(f"[{i}:v][{i}:a]" for i in range(n))
    filter_complex = f"{stream_refs}concat=n={n}:v=1:a=1[v][a]"

    result = subprocess.run(
        [
            ffmpeg,
            "-y",
            *inputs,
            "-filter_complex",
            filter_complex,
            "-map",
            "[v]",
            "-map",
            "[a]",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "23",
            "-c:a",
            "aac",
            "-ar",
            "44100",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            str(output_path),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"拼接成片失败:\n{result.stderr[-2000:]}")
    return output_path


def render_storyboard(
    storyboard_path: Path,
    work_dir: Path | None = None,
    output_dir: Path | None = None,
    skip_tts: bool = False,
) -> Path:
    storyboard_path = storyboard_path.resolve()
    project_root = storyboard_path.parent.parent
    storyboard = Storyboard.load(storyboard_path)
    storyboard = prepare_storyboard_assets(
        storyboard, project_root, storyboard_path=storyboard_path
    )

    base_work = work_dir or (project_root / ".work")
    base_work = base_work.resolve()
    base_work.mkdir(parents=True, exist_ok=True)

    out_dir = output_dir or (storyboard_path.parent.parent / "output")
    out_dir.mkdir(parents=True, exist_ok=True)
    final_path = out_dir / storyboard.output.filename

    if not skip_tts:
        generate_all_audio(storyboard, base_work)

    audio_dir = base_work / "audio"
    segments_dir = base_work / "segments"
    segments_dir.mkdir(parents=True, exist_ok=True)

    rendered_scenes: list[RenderedScene] = []
    for scene in storyboard.all_scenes():
        audio_path = audio_dir / f"{scene.id}.mp3"
        if not audio_path.exists():
            raise FileNotFoundError(f"缺少配音文件: {audio_path}")
        duration = probe_duration_sec(audio_path)
        rendered_scenes.append(
            RenderedScene(
                scene=scene,
                audio_path=audio_path,
                audio_duration_sec=duration,
            )
        )

    segment_paths: list[Path] = []
    for rs in rendered_scenes:
        segment_paths.append(
            render_scene_segment(rs, storyboard, storyboard_path, segments_dir)
        )

    concat_segments(segment_paths, final_path)
    return final_path
