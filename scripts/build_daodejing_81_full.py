#!/usr/bin/env python3
"""将 81 章道德经动画拼接为一片，配 TTS 朗读与 BGM。

素材：
  assets/DaoDeJing/animations/final_81_chapters/Chapter_*_v6.mp4
  assets/DaoDeJing/taoteching_full.json

输出：
  output/daodejing-81-chapters-full.mp4
  output/daodejing-81-full/（中间文件：audio/、segments/）
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.bgm import mix_bgm_into_video  # noqa: E402
from pipeline.brand import (  # noqa: E402
    ENDING_DURATION_SEC,
    ENDING_IMAGE,
    ENDING_SCENE_ID,
)
from pipeline.ffmpeg_util import create_silent_audio, probe_duration_sec, require_ffmpeg  # noqa: E402
from pipeline.frame import render_frame  # noqa: E402
from pipeline.models import BgmConfig, RenderedScene, Scene, StyleConfig, TtsConfig  # noqa: E402
from pipeline.render import _concat_videos, _encode_still_video, _mux_video_audio  # noqa: E402
from pipeline.tts import generate_scene_audio  # noqa: E402

FRAME_WIDTH = 1920
FRAME_HEIGHT = 1080
FRAME_FPS = 30

CHAPTER_DIR = ROOT / "assets/DaoDeJing/animations/final_81_chapters"
TEXT_JSON = ROOT / "assets/DaoDeJing/taoteching_full.json"
DEFAULT_OUT = ROOT / "output/daodejing-81-chapters-full.mp4"
WORK_DIR = ROOT / "output/daodejing-81-full"


def _chapter_sort_key(path: Path) -> int:
    m = re.search(r"Chapter_(\d+)_", path.name)
    if not m:
        raise ValueError(f"无法解析章节号: {path.name}")
    return int(m.group(1))


def list_chapter_videos() -> list[Path]:
    videos = sorted(CHAPTER_DIR.glob("Chapter_*_v6.mp4"), key=_chapter_sort_key)
    if len(videos) != 81:
        raise RuntimeError(f"期望 81 个章节视频，实际 {len(videos)} 个")
    return videos


def load_chapter_texts() -> dict[int, str]:
    data = json.loads(TEXT_JSON.read_text(encoding="utf-8"))
    out: dict[int, str] = {}
    for key, body in data.items():
        num = int(key)
        lines = [ln.strip() for ln in str(body).splitlines() if ln.strip()]
        # 朗读：章号 + 原文（逗号停顿）
        out[num] = f"第{num}章。" + "，".join(lines)
    if len(out) != 81:
        raise RuntimeError(f"期望 81 章文本，实际 {len(out)} 章")
    return out


def narration_for(chapter: int, texts: dict[int, str]) -> str:
    return texts[chapter]


def mux_chapter_segment(
    video_path: Path,
    audio_path: Path,
    out_path: Path,
    *,
    crf: int = 20,
) -> float:
    """以 TTS 时长为准，变速画面（setpts）使画面与旁白对齐。"""
    ffmpeg = require_ffmpeg()
    video_dur = probe_duration_sec(video_path)
    audio_dur = probe_duration_sec(audio_path)
    if video_dur <= 0 or audio_dur <= 0:
        raise RuntimeError(f"无效时长 video={video_dur} audio={audio_dur} ({video_path.name})")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    # setpts 倍数 = 目标时长 / 原时长；>1 放慢，<1 加快
    pts_factor = audio_dur / video_dur
    vf = f"[0:v]setpts={pts_factor:.8f}*PTS[v]"

    cmd = [
        ffmpeg,
        "-y",
        "-i",
        str(video_path),
        "-i",
        str(audio_path),
        "-filter_complex",
        vf,
        "-map",
        "[v]",
        "-map",
        "1:a",
        "-t",
        f"{audio_dur:.3f}",
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        str(crf),
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-ar",
        "44100",
        "-ac",
        "2",
        "-movflags",
        "+faststart",
        str(out_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"合成 {out_path.name} 失败:\n{result.stderr[-2000:]}"
        )
    return audio_dur


def build_ending_segment(
    seg_dir: Path,
    audio_dir: Path,
    *,
    duration_sec: float = ENDING_DURATION_SEC,
    crf: int = 20,
) -> Path:
    """片尾 logo 页（与五讲系列相同的 avatar.webp）。"""
    image = (ROOT / ENDING_IMAGE).resolve()
    if not image.is_file():
        raise FileNotFoundError(f"片尾图不存在: {image}")

    seg_dir.mkdir(parents=True, exist_ok=True)
    audio_dir.mkdir(parents=True, exist_ok=True)
    out_path = seg_dir / "ending.mp4"
    frame_path = seg_dir / "ending_frame.png"
    silent_video = seg_dir / "ending_silent.mp4"
    audio_path = audio_dir / "ending.mp3"

    scene = Scene(id=ENDING_SCENE_ID, narration="", image=ENDING_IMAGE)
    render_frame(
        "",
        StyleConfig(),
        FRAME_WIDTH,
        FRAME_HEIGHT,
        frame_path,
        image_path=image,
        scene_id=ENDING_SCENE_ID,
        scene=scene,
    )
    ffmpeg = require_ffmpeg()
    _encode_still_video(ffmpeg, frame_path, FRAME_FPS, duration_sec, silent_video)
    create_silent_audio(duration_sec, audio_path)
    _mux_video_audio(ffmpeg, silent_video, audio_path, out_path)
    silent_video.unlink(missing_ok=True)
    return out_path


def build_rendered_scenes(
    durations: list[tuple[str, float]],
) -> list[RenderedScene]:
    scenes: list[RenderedScene] = []
    for scene_id, dur in durations:
        scenes.append(
            RenderedScene(
                scene=Scene(id=scene_id, narration=""),
                audio_path=Path("."),
                audio_duration_sec=dur,
            )
        )
    return scenes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=DEFAULT_OUT,
        help="成片路径",
    )
    parser.add_argument(
        "--work-dir",
        type=Path,
        default=WORK_DIR,
        help="中间目录（audio/、segments/）",
    )
    parser.add_argument("--from-chapter", type=int, default=1)
    parser.add_argument("--to-chapter", type=int, default=81)
    parser.add_argument("--skip-tts", action="store_true", help="复用已有配音")
    parser.add_argument("--skip-segments", action="store_true", help="复用已有分镜")
    parser.add_argument("--skip-bgm", action="store_true")
    parser.add_argument("--concat-only", action="store_true", help="仅拼接动画（无 TTS）")
    parser.add_argument(
        "--tts-provider",
        default="edge",
        choices=["edge", "volcengine"],
    )
    parser.add_argument("--voice", default="zh-CN-YunxiNeural")
    parser.add_argument("--rate", default="+0%")
    parser.add_argument("--crf", type=int, default=20)
    parser.add_argument(
        "--ending",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="片尾 logo 页（默认 4 秒 avatar）",
    )
    parser.add_argument(
        "--ending-duration",
        type=float,
        default=ENDING_DURATION_SEC,
        help="片尾时长（秒）",
    )
    parser.add_argument(
        "--ending-only",
        action="store_true",
        help="仅重拼已有 81 段 + 片尾 + BGM（最快）",
    )
    args = parser.parse_args()

    if not CHAPTER_DIR.is_dir():
        print(f"章节目录不存在: {CHAPTER_DIR}", file=sys.stderr)
        return 1
    if not TEXT_JSON.is_file() and not args.concat_only:
        print(f"原文 JSON 不存在: {TEXT_JSON}", file=sys.stderr)
        return 1

    videos = list_chapter_videos()
    texts = load_chapter_texts() if not args.concat_only else {}
    tts = TtsConfig(provider=args.tts_provider, voice=args.voice, rate=args.rate)

    work = args.work_dir.resolve()
    audio_dir = work / "audio"
    seg_dir = work / "segments"
    audio_dir.mkdir(parents=True, exist_ok=True)
    seg_dir.mkdir(parents=True, exist_ok=True)

    ch_from = max(1, args.from_chapter)
    ch_to = min(81, args.to_chapter)
    selected = [(i, videos[i - 1]) for i in range(ch_from, ch_to + 1)]

    if args.concat_only:
        print(f"仅拼接 {len(selected)} 章动画…")
        tmp = work / "concat_visual.mp4"
        _concat_videos(require_ffmpeg(), [p for _, p in selected], tmp)
        out = args.output.resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(tmp, out)
        print(f"成片: {out}")
        return 0

    if args.ending_only:
        args.skip_tts = True
        args.skip_segments = True

    built_segments: list[Path] = []
    built_durations: list[tuple[str, float]] = []

    for ch, video_path in selected:
        seg_path = seg_dir / f"ch{ch:02d}.mp4"
        audio_path = audio_dir / f"ch{ch:02d}.mp3"

        if args.skip_segments and seg_path.exists() and seg_path.stat().st_size > 1000:
            dur = probe_duration_sec(seg_path)
            built_segments.append(seg_path)
            built_durations.append((f"ch{ch:02d}", dur))
            print(f"[{ch:02d}/81] 跳过 segment（已存在）")
            continue

        if not args.skip_tts:
            text = narration_for(ch, texts)
            if audio_path.exists() and audio_path.stat().st_size < 500:
                audio_path.unlink(missing_ok=True)
            if not audio_path.exists() or audio_path.stat().st_size < 500:
                print(f"[{ch:02d}/81] TTS…")
                generate_scene_audio(text, audio_path, tts)
            else:
                print(f"[{ch:02d}/81] 复用 TTS")
        elif not audio_path.exists():
            print(f"缺少配音: {audio_path}", file=sys.stderr)
            return 1

        print(f"[{ch:02d}/81] 合成画面+旁白…")
        dur = mux_chapter_segment(video_path, audio_path, seg_path, crf=args.crf)
        built_segments.append(seg_path)
        built_durations.append((f"ch{ch:02d}", dur))

    concat_from = 1 if (ch_from > 1 and ch_to == 81) else ch_from
    concat_to = 81 if (ch_from > 1 and ch_to == 81) else ch_to
    segment_paths: list[Path] = []
    durations: list[tuple[str, float]] = []
    for ch in range(concat_from, concat_to + 1):
        p = seg_dir / f"ch{ch:02d}.mp4"
        if not p.exists():
            print(f"缺少分段 {p.name}", file=sys.stderr)
            return 1
        segment_paths.append(p)
        durations.append((f"ch{ch:02d}", probe_duration_sec(p)))

    if args.ending:
        print(f"生成片尾（{args.ending_duration:.1f}s）…")
        ending_path = build_ending_segment(
            seg_dir,
            audio_dir,
            duration_sec=args.ending_duration,
            crf=args.crf,
        )
        segment_paths.append(ending_path)
        durations.append((ENDING_SCENE_ID, args.ending_duration))

    narrated = work / "narrated_concat.mp4"
    print(f"拼接 {len(segment_paths)} 段（流复制）…")
    _concat_videos(require_ffmpeg(), segment_paths, narrated)

    out = args.output.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    if args.skip_bgm:
        shutil.copy2(narrated, out)
    else:
        bgm = BgmConfig(
            enabled=True,
            switch_at_scene="",  # 均分两轨 BGM
            volume=0.14,
            crossfade_sec=6.0,
            fade_in_sec=2.0,
            fade_out_sec=6.0,
        )
        rendered = build_rendered_scenes(durations)
        print("混入 BGM…")
        mix_bgm_into_video(narrated, ROOT, bgm, rendered, out_path=out)

    total_min = sum(d for _, d in durations) / 60.0
    ending_note = f"（含片尾 {args.ending_duration:.0f}s）" if args.ending else ""
    print(f"\n完成。约 {total_min:.1f} 分钟{ending_note}")
    print(f"成片: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
