from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .image_resolve import (
    MissingStoryboardImagesError,
    find_missing_storyboard_images,
    resolve_daodejing_image,
)
from .ffmpeg_util import (
    create_silent_audio,
    is_silent_audio,
    probe_duration_sec,
    require_ffmpeg,
)
from .frame import (
    is_prerendered_slide,
    render_frame,
    render_subtitle_overlay_rgba,
    render_watermark_overlay_rgba,
)
from .models import RenderedScene, Scene, Storyboard, TtsConfig
from .motion import render_kenburns_video, resolve_motion
from .prepare import prepare_storyboard_assets
from .subtitle_timing import (
    SubtitleCue,
    build_cues_for_audio,
    cues_are_valid,
    cues_path_for,
    load_cues,
)
from .ambient import (
    composite_ambient_on_video,
    ensure_ambient_loops,
    resolve_ambient_layer,
)
from .bgm import mix_bgm_into_video
from .tts import generate_all_audio, generate_scene_audio_and_cues


def _ensure_scene_audio(
    scene: Scene,
    audio_path: Path,
    tts: TtsConfig,
    *,
    skip_tts: bool,
) -> None:
    """skip_tts 时仍会为「有旁白但缓存为静音」的镜头重录 TTS。"""
    if not scene.narration.strip():
        if not audio_path.exists() or audio_path.stat().st_size < 500:
            dur = scene.duration_sec or 3.0
            create_silent_audio(dur, audio_path)
        return

    stale = (
        not audio_path.exists()
        or audio_path.stat().st_size < 500
        or is_silent_audio(audio_path)
        or not cues_are_valid(cues_path_for(audio_path))
    )
    if stale:
        generate_scene_audio_and_cues(scene.narration, audio_path, tts)
    elif not skip_tts and not cues_are_valid(cues_path_for(audio_path)):
        build_cues_for_audio(scene.narration, audio_path)


def _resolve_image(
    path_str: str | None,
    storyboard_path: Path,
    *,
    allow_missing: bool = False,
) -> Path | None:
    if not path_str:
        return None
    project_root = _project_root_from_storyboard(storyboard_path)
    resolved = resolve_daodejing_image(path_str, project_root)
    if resolved is not None:
        return resolved
    if allow_missing:
        return None
    # 严格模式：由 render_storyboard 预检统一报错；单镜 fallback
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


def _should_use_kenburns(
    scene,
    storyboard: Storyboard,
    image: Path | None,
) -> bool:
    if not image or not image.exists():
        return False
    if is_prerendered_slide(image):
        return False
    motion = resolve_motion(
        scene.motion,
        style_motion=storyboard.style.motion,
        scene_id=scene.id,
    )
    return motion != "static"


def _project_root_from_storyboard(storyboard_path: Path) -> Path:
    return storyboard_path.resolve().parent.parent


def _build_video_filters(
    *,
    base_label: str,
    wm_input: int | None,
    subtitle_plan: list[tuple[int, SubtitleCue]],
) -> tuple[list[str], str]:
    """base（已烘焙氛围）→ 水印 → 字幕。"""
    parts: list[str] = []
    label = base_label

    if wm_input is not None:
        wm_filt, label = _overlay_static_layer_filter(label, wm_input)
        parts.append(wm_filt)

    for i, (sub_input, cue) in enumerate(subtitle_plan):
        label_out = f"sv{i}"
        enable = f"between(t,{cue.start:.3f},{cue.end:.3f})"
        parts.append(
            f"[{label}][{sub_input}:v]overlay=0:0:enable='{enable}'[{label_out}]"
        )
        label = label_out

    return parts, label


def _overlay_static_layer_filter(input_label: str, overlay_index: int) -> tuple[str, str]:
    """全时长叠加静态 PNG（水印）。"""
    out = f"wm{overlay_index}"
    filt = f"[{input_label}][{overlay_index}:v]overlay=0:0[{out}]"
    return filt, out


def _build_overlay_filter(cues: list[SubtitleCue]) -> tuple[str, str]:
    parts: list[str] = []
    label_in = "0:v"
    for i, cue in enumerate(cues):
        label_out = f"sv{i}"
        enable = f"between(t,{cue.start:.3f},{cue.end:.3f})"
        parts.append(
            f"[{label_in}][{i + 1}:v]overlay=0:0:enable='{enable}'[{label_out}]"
        )
        label_in = label_out
    return ";".join(parts), label_in


def _render_slideshow_cues_segment(
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
    """一镜一图 + 一条音轨 + cues 时间轴；可选 Ken Burns + 叠字幕。"""
    scene = rendered.scene
    style = storyboard.style
    ffmpeg = require_ffmpeg()

    duration = rendered.audio_duration_sec + scene.pause_after_sec
    if scene.pause_after_sec and cues:
        last = cues[-1]
        cues = cues[:-1] + [
            SubtitleCue(last.text, last.start, last.end + scene.pause_after_sec)
        ]

    motion = resolve_motion(
        scene.motion,
        style_motion=style.motion,
        scene_id=scene.id,
    )
    use_kenburns = _should_use_kenburns(scene, storyboard, image)
    project_root = _project_root_from_storyboard(storyboard_path)
    ambient_layer = (
        resolve_ambient_layer(storyboard, scene.id, config=storyboard.ambient)
        if use_kenburns
        else None
    )
    if ambient_layer:
        ensure_ambient_loops(project_root, w, h)

    overlay_paths: list[Path] = []
    for i, cue in enumerate(cues):
        op = segments_dir / f"{scene.id}_sub_{i:03d}.png"
        render_subtitle_overlay_rgba(cue.text, style, w, h, op)
        overlay_paths.append(op)

    wm_path: Path | None = None
    if use_kenburns and storyboard.watermark.enabled:
        wm_path = segments_dir / f"{scene.id}_wm.png"
        render_watermark_overlay_rgba(
            storyboard.watermark,
            style,
            w,
            h,
            wm_path,
            logo_path=logo_path,
        )

    cmd: list[str] = [ffmpeg, "-y"]

    if use_kenburns and image:
        motion_vid = segments_dir / f"{scene.id}_motion.mp4"
        render_kenburns_video(
            image,
            motion_vid,
            width=w,
            height=h,
            fps=fps,
            duration_sec=duration,
            motion=motion,
            background_color=style.background_color,
        )
        motion_src = motion_vid
        if ambient_layer:
            motion_baked = segments_dir / f"{scene.id}_motion_amb.mp4"
            composite_ambient_on_video(
                motion_vid,
                motion_baked,
                project_root=project_root,
                preset=ambient_layer.preset,
                opacity=ambient_layer.opacity,
                duration_sec=duration,
                width=w,
                height=h,
                fps=fps,
            )
            motion_src = motion_baked
        cmd.extend(["-i", str(motion_src)])
        input_idx = 1
    else:
        base_png = segments_dir / f"{scene.id}_base.png"
        render_frame(
            scene.narration,
            style,
            w,
            h,
            base_png,
            image_path=image,
            watermark=storyboard.watermark,
            watermark_logo_path=logo_path,
            scene_id=scene.id,
            scene=scene,
        )
        cmd.extend(
            [
                "-loop",
                "1",
                "-framerate",
                str(fps),
                "-i",
                str(base_png),
            ]
        )
        input_idx = 1

    if wm_path and wm_path.exists():
        cmd.extend(["-i", str(wm_path)])

    for op in overlay_paths:
        cmd.extend(["-i", str(op)])
    cmd.extend(["-i", str(rendered.audio_path)])

    sub_start_idx = input_idx + (1 if wm_path else 0)
    audio_input = sub_start_idx + len(overlay_paths)
    wm_input = input_idx if wm_path else None
    subtitle_plan = [
        (sub_start_idx + i, cue) for i, cue in enumerate(cues)
    ]

    filt_parts, vout = _build_video_filters(
        base_label="0:v",
        wm_input=wm_input,
        subtitle_plan=subtitle_plan,
    )

    if filt_parts:
        cmd.extend(
            [
                "-filter_complex",
                ";".join(filt_parts),
                "-map",
                f"[{vout}]",
                "-map",
                f"{audio_input}:a",
            ]
        )
    else:
        cmd.extend(["-map", "0:v", "-map", f"{audio_input}:a"])

    cmd.extend(
        [
            "-t",
            f"{duration:.3f}",
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
    )

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"渲染镜头 {scene.id} 失败:\n{result.stderr[-2500:]}"
        )
    rendered.segment_path = segment_path
    return segment_path


def render_scene_segment(
    rendered: RenderedScene,
    storyboard: Storyboard,
    storyboard_path: Path,
    segments_dir: Path,
    *,
    allow_missing_images: bool = False,
) -> Path:
    scene = rendered.scene
    style = storyboard.style
    out = storyboard.output

    duration = scene.duration_sec or rendered.audio_duration_sec
    duration += scene.pause_after_sec

    image = _resolve_image(
        scene.image, storyboard_path, allow_missing=allow_missing_images
    )
    segment_path = segments_dir / f"{scene.id}.mp4"
    w, h, fps = out.width, out.height, out.fps
    logo_path = _resolve_image(
        storyboard.watermark.image, storyboard_path, allow_missing=True
    )

    cues = load_cues(cues_path_for(rendered.audio_path))
    if cues:
        return _render_slideshow_cues_segment(
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
    motion = resolve_motion(
        scene.motion,
        style_motion=style.motion,
        scene_id=scene.id,
    )
    use_kenburns = _should_use_kenburns(scene, storyboard, image)
    project_root = _project_root_from_storyboard(storyboard_path)
    ambient_layer = (
        resolve_ambient_layer(storyboard, scene.id, config=storyboard.ambient)
        if use_kenburns
        else None
    )
    if ambient_layer:
        ensure_ambient_loops(project_root, w, h)

    if use_kenburns and image:
        motion_vid = segments_dir / f"{scene.id}_motion.mp4"
        render_kenburns_video(
            image,
            motion_vid,
            width=w,
            height=h,
            fps=fps,
            duration_sec=duration,
            motion=motion,
            background_color=style.background_color,
        )
        motion_src = motion_vid
        if ambient_layer:
            motion_baked = segments_dir / f"{scene.id}_motion_amb.mp4"
            composite_ambient_on_video(
                motion_vid,
                motion_baked,
                project_root=project_root,
                preset=ambient_layer.preset,
                opacity=ambient_layer.opacity,
                duration_sec=duration,
                width=w,
                height=h,
                fps=fps,
            )
            motion_src = motion_baked
        wm_path = segments_dir / f"{scene.id}_wm.png"
        render_watermark_overlay_rgba(
            storyboard.watermark,
            style,
            w,
            h,
            wm_path,
            logo_path=logo_path,
        )
        ffmpeg = require_ffmpeg()
        cmd: list[str] = [ffmpeg, "-y", "-i", str(motion_src)]
        input_idx = 1
        cmd.extend(["-i", str(wm_path), "-i", str(rendered.audio_path)])
        wm_input = input_idx
        audio_input = input_idx + 1
        filt_parts, vout = _build_video_filters(
            base_label="0:v",
            wm_input=wm_input,
            subtitle_plan=[],
        )
        cmd.extend(
            [
                "-filter_complex",
                ";".join(filt_parts),
                "-map",
                f"[{vout}]",
                "-map",
                f"{audio_input}:a",
                "-t",
                f"{duration:.3f}",
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
        )
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(
                f"渲染镜头 {scene.id} 失败:\n{result.stderr[-2000:]}"
            )
        rendered.segment_path = segment_path
        return segment_path

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
    *,
    allow_missing_images: bool = False,
) -> Path:
    storyboard_path = storyboard_path.resolve()
    project_root = storyboard_path.parent.parent

    missing = find_missing_storyboard_images(storyboard_path, project_root)
    if missing and not allow_missing_images:
        raise MissingStoryboardImagesError(storyboard_path, missing)

    storyboard = Storyboard.load(storyboard_path)
    storyboard = prepare_storyboard_assets(
        storyboard, project_root, storyboard_path=storyboard_path
    )

    out_dir = output_dir or (project_root / "output")
    out_dir = out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    # 配音、片段与成片默认都在 output/（便于在 Finder 中查看）
    base_work = (work_dir or out_dir).resolve()
    base_work.mkdir(parents=True, exist_ok=True)
    final_path = out_dir / storyboard.output.filename

    if not skip_tts:
        generate_all_audio(storyboard, base_work)

    audio_dir = base_work / "audio"
    segments_dir = base_work / "segments"
    segments_dir.mkdir(parents=True, exist_ok=True)

    rendered_scenes: list[RenderedScene] = []
    for scene in storyboard.all_scenes():
        audio_path = audio_dir / f"{scene.id}.mp3"
        _ensure_scene_audio(scene, audio_path, storyboard.tts, skip_tts=skip_tts)
        if scene.narration.strip() and not cues_are_valid(cues_path_for(audio_path)):
            build_cues_for_audio(scene.narration, audio_path)
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
            render_scene_segment(
                rs,
                storyboard,
                storyboard_path,
                segments_dir,
                allow_missing_images=allow_missing_images,
            )
        )

    concat_segments(segment_paths, final_path)
    mix_bgm_into_video(
        final_path,
        project_root,
        storyboard.bgm,
        rendered_scenes,
    )
    return final_path
