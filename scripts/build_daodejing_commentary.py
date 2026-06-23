#!/usr/bin/env python3
"""道德经「朗读 + 讲解」成片：每章先原文 TTS + 动画，再讲解 TTS + 同章动画。

数据：
  assets/DaoDeJing/taoteching_full.json
  assets/DaoDeJing/daodejing_81_commentary.json

示例（第 1 章试听）：
  python3 scripts/build_daodejing_commentary.py --from-chapter 1 --to-chapter 1
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.bgm import mix_bgm_into_video  # noqa: E402
from pipeline.brand import ENDING_DURATION_SEC, ENDING_IMAGE, ENDING_SCENE_ID  # noqa: E402
from pipeline.ffmpeg_util import probe_duration_sec, require_ffmpeg  # noqa: E402
from pipeline.models import BgmConfig, RenderedScene, Scene, TtsConfig  # noqa: E402
from pipeline.render import _concat_videos  # noqa: E402
from pipeline.tts import generate_scene_audio  # noqa: E402

import importlib.util

_b81_spec = importlib.util.spec_from_file_location(
    "build_daodejing_81_full",
    ROOT / "scripts" / "build_daodejing_81_full.py",
)
_b81 = importlib.util.module_from_spec(_b81_spec)
assert _b81_spec.loader
_b81_spec.loader.exec_module(_b81)

build_ending_segment = _b81.build_ending_segment
build_rendered_scenes = _b81.build_rendered_scenes
list_chapter_videos = _b81.list_chapter_videos
load_chapter_texts = _b81.load_chapter_texts
mux_chapter_segment = _b81.mux_chapter_segment
narration_for = _b81.narration_for

COMMENTARY_JSON = ROOT / "assets/DaoDeJing/daodejing_81_commentary.json"
DEFAULT_OUT = ROOT / "output/daodejing-81-commentary-pilot.mp4"
WORK_DIR = ROOT / "output/daodejing-81-commentary"
INTRO_IMAGE = ROOT / "assets/DaoDeJing/cover_full_reading.jpg"


def load_commentary() -> dict:
    data = json.loads(COMMENTARY_JSON.read_text(encoding="utf-8"))
    series = data.get("series") or {}
    intro = (series.get("intro") or data.get("intro") or "").strip()
    chapters_raw = data.get("chapters") or {}
    chapters: dict[int, str] = {}
    for k, v in chapters_raw.items():
        if isinstance(v, str):
            chapters[int(k)] = v.strip()
        else:
            chapters[int(k)] = str(v.get("explain", "")).strip()
    return {"intro": intro, "chapters": chapters}


def build_intro_segment(
    intro_text: str,
    audio_dir: Path,
    seg_dir: Path,
    tts: TtsConfig,
    *,
    crf: int,
) -> Path | None:
    if not intro_text:
        return None
    if not INTRO_IMAGE.is_file():
        print(f"跳过片头画面（无图）: {INTRO_IMAGE}", file=sys.stderr)
        return None

    from pipeline.frame import render_frame  # noqa: E402
    from pipeline.models import StyleConfig  # noqa: E402
    from pipeline.render import _encode_still_video, _mux_video_audio  # noqa: E402
    from pipeline.ffmpeg_util import create_silent_audio  # noqa: E402

    audio_path = audio_dir / "intro.mp3"
    if not audio_path.exists() or audio_path.stat().st_size < 500:
        print("TTS 片头…")
        generate_scene_audio(intro_text, audio_path, tts)

    out = seg_dir / "intro.mp4"
    frame = seg_dir / "intro_frame.png"
    render_frame(
        "",
        StyleConfig(),
        1920,
        1080,
        frame,
        image_path=INTRO_IMAGE.resolve(),
    )
    ffmpeg = require_ffmpeg()
    dur = probe_duration_sec(audio_path)
    silent = seg_dir / "intro_silent.mp4"
    _encode_still_video(ffmpeg, frame, 30, dur, silent)
    _mux_video_audio(ffmpeg, silent, audio_path, out)
    silent.unlink(missing_ok=True)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--work-dir", type=Path, default=WORK_DIR)
    parser.add_argument("--from-chapter", type=int, default=1)
    parser.add_argument("--to-chapter", type=int, default=1)
    parser.add_argument("--skip-tts", action="store_true")
    parser.add_argument("--skip-segments", action="store_true")
    parser.add_argument("--skip-bgm", action="store_true")
    parser.add_argument("--no-intro", action="store_true")
    parser.add_argument("--no-ending", action="store_true")
    parser.add_argument("--tts-provider", default="edge")
    parser.add_argument("--voice", default="zh-CN-YunxiNeural")
    parser.add_argument("--rate", default="+0%")
    parser.add_argument("--crf", type=int, default=20)
    args = parser.parse_args()

    if not COMMENTARY_JSON.is_file():
        print(f"缺少讲解稿: {COMMENTARY_JSON}", file=sys.stderr)
        return 1

    meta = load_commentary()
    texts = load_chapter_texts()
    videos = list_chapter_videos()
    tts = TtsConfig(provider=args.tts_provider, voice=args.voice, rate=args.rate)

    work = args.work_dir.resolve()
    audio_dir = work / "audio"
    seg_dir = work / "segments"
    audio_dir.mkdir(parents=True, exist_ok=True)
    seg_dir.mkdir(parents=True, exist_ok=True)

    ch_from = max(1, args.from_chapter)
    ch_to = min(81, args.to_chapter)
    segment_paths: list[Path] = []
    durations: list[tuple[str, float]] = []

    if not args.no_intro and meta["intro"]:
        intro_path = seg_dir / "intro.mp4"
        if args.skip_segments and intro_path.exists():
            segment_paths.append(intro_path)
            durations.append(("intro", probe_duration_sec(intro_path)))
        else:
            p = build_intro_segment(
                meta["intro"], audio_dir, seg_dir, tts, crf=args.crf
            )
            if p:
                segment_paths.append(p)
                durations.append(("intro", probe_duration_sec(p)))

    for ch in range(ch_from, ch_to + 1):
        if ch not in meta["chapters"]:
            print(f"第 {ch} 章无讲解稿，跳过讲解段", file=sys.stderr)
            explain_text = ""
        else:
            explain_text = meta["chapters"][ch]

        video_path = videos[ch - 1]
        read_id = f"ch{ch:02d}-read"
        explain_id = f"ch{ch:02d}-explain"
        read_seg = seg_dir / f"{read_id}.mp4"
        explain_seg = seg_dir / f"{explain_id}.mp4"
        read_audio = audio_dir / f"{read_id}.mp3"
        explain_audio = audio_dir / f"{explain_id}.mp3"

        for seg_path, audio_path, narration, label in (
            (read_seg, read_audio, narration_for(ch, texts), "朗读"),
            (explain_seg, explain_audio, explain_text, "讲解"),
        ):
            if not narration:
                continue
            if args.skip_segments and seg_path.exists() and seg_path.stat().st_size > 1000:
                print(f"[{ch:02d}] 跳过 {label} segment")
                segment_paths.append(seg_path)
                durations.append((seg_path.stem, probe_duration_sec(seg_path)))
                continue
            if label == "讲解" and narration:
                nchar = len(narration)
                est_min = nchar / 260
                if est_min < 4.0 or est_min > 7.5:
                    print(
                        f"  ⚠ 讲解稿约 {nchar} 字、预估 {est_min:.1f} 分钟"
                        f"（目标讲解段 4.5–6.5 分钟，建议 1400–1700 字）",
                        file=sys.stderr,
                    )
            if not args.skip_tts:
                if not audio_path.exists() or audio_path.stat().st_size < 500:
                    print(f"[{ch:02d}] TTS {label}…")
                    generate_scene_audio(narration, audio_path, tts)
            elif not audio_path.exists():
                print(f"缺少配音: {audio_path}", file=sys.stderr)
                return 1
            print(f"[{ch:02d}] 合成 {label}…")
            dur = mux_chapter_segment(video_path, audio_path, seg_path, crf=args.crf)
            segment_paths.append(seg_path)
            durations.append((seg_path.stem, dur))

    if not args.no_ending:
        ending_path = seg_dir / "ending.mp4"
        if args.skip_segments and ending_path.exists():
            segment_paths.append(ending_path)
            durations.append((ENDING_SCENE_ID, probe_duration_sec(ending_path)))
        else:
            print("生成片尾…")
            segment_paths.append(
                build_ending_segment(
                    seg_dir, audio_dir, duration_sec=ENDING_DURATION_SEC, crf=args.crf
                )
            )
            durations.append((ENDING_SCENE_ID, ENDING_DURATION_SEC))

    narrated = work / "commentary_concat.mp4"
    print(f"拼接 {len(segment_paths)} 段…")
    _concat_videos(require_ffmpeg(), segment_paths, narrated)

    out = args.output.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    if args.skip_bgm:
        shutil.copy2(narrated, out)
    else:
        bgm = BgmConfig(enabled=True, switch_at_scene="", volume=0.12, crossfade_sec=6.0)
        mix_bgm_into_video(
            narrated, ROOT, bgm, build_rendered_scenes(durations), out_path=out
        )

    print(f"\n完成。约 {sum(d for _, d in durations) / 60:.1f} 分钟")
    print(f"成片: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
