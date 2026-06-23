#!/usr/bin/env python3
"""仅重录片尾 CTA 配音并重拼 hybrid 成片（不重渲全部讲解镜头）。

用法:
  python3 scripts/refresh_hybrid_endings.py --chapters 1-81
  python3 scripts/refresh_hybrid_endings.py --chapter 1
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.bgm import mix_bgm_into_video  # noqa: E402
from pipeline.brand import ENDING_SCENE_ID  # noqa: E402
from pipeline.env_util import load_dotenv  # noqa: E402
from pipeline.ffmpeg_util import probe_duration_sec, require_ffmpeg  # noqa: E402
from pipeline.models import BgmConfig, RenderedScene, Storyboard  # noqa: E402
from pipeline.prepare import prepare_storyboard_assets  # noqa: E402
from pipeline.render import (  # noqa: E402
    _concat_videos,
    concat_segments,
    render_scene_segment,
)
from pipeline.subtitle_timing import generate_scene_audio_and_cues  # noqa: E402

import importlib.util

_b81_spec = importlib.util.spec_from_file_location(
    "build_daodejing_81_full",
    ROOT / "scripts" / "build_daodejing_81_full.py",
)
_b81 = importlib.util.module_from_spec(_b81_spec)
assert _b81_spec.loader
_b81_spec.loader.exec_module(_b81)

build_hybrid_bgm_scenes = None  # set after import build_chapter_hybrid


def _import_hybrid_helpers():
    global build_hybrid_bgm_scenes
    spec = importlib.util.spec_from_file_location(
        "build_chapter_hybrid",
        ROOT / "scripts" / "build_chapter_hybrid.py",
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    build_hybrid_bgm_scenes = mod.build_hybrid_bgm_scenes
    return mod.load_chapter_config


def parse_chapters(spec: str) -> list[int]:
    out: list[int] = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            out.extend(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return sorted(set(out))


def purge_ending_artifacts(comm_work: Path) -> None:
    audio_dir = comm_work / "audio"
    seg_dir = comm_work / "segments"
    for name in ("ending.mp3", "ending.cues.json"):
        (audio_dir / name).unlink(missing_ok=True)
    if seg_dir.is_dir():
        for p in seg_dir.glob("ending*"):
            p.unlink(missing_ok=True)


def refresh_chapter(ch: int, load_chapter_config, *, ending_audio_from: int | None = None) -> None:
    cfg = load_chapter_config(ch)
    if cfg.get("mode") != "hybrid":
        print(f"  ch{ch:02d} skip (not hybrid)")
        return

    storyboard_path = (ROOT / cfg["storyboard"]).resolve()
    storyboard = Storyboard.load(storyboard_path)
    storyboard = prepare_storyboard_assets(
        storyboard, ROOT, storyboard_path=storyboard_path
    )

    work = ROOT / f"output/ch{ch:02d}-hybrid"
    comm_work = work / "commentary.work"
    comm_out_dir = work / "commentary"
    if not comm_work.is_dir():
        raise FileNotFoundError(f"缺少 commentary.work: {comm_work}")

    ending_scene = next(
        (s for s in storyboard.all_scenes() if s.id == ENDING_SCENE_ID),
        None,
    )
    if not ending_scene or not ending_scene.narration.strip():
        print(f"  ch{ch:02d} skip (no ending narration)")
        return

    purge_ending_artifacts(comm_work)

    audio_dir = comm_work / "audio"
    seg_dir = comm_work / "segments"
    audio_dir.mkdir(parents=True, exist_ok=True)
    seg_dir.mkdir(parents=True, exist_ok=True)

    ending_audio = audio_dir / "ending.mp3"
    if ending_audio_from is not None:
        src_work = ROOT / f"output/ch{ending_audio_from:02d}-hybrid/commentary.work/audio"
        for name in ("ending.mp3", "ending.cues.json"):
            src = src_work / name
            if not src.is_file():
                raise FileNotFoundError(f"缺少片尾素材: {src}")
            shutil.copy2(src, audio_dir / name)
        print(f"  ch{ch:02d} 复用 ch{ending_audio_from:02d} 片尾配音…")
    else:
        print(f"  ch{ch:02d} TTS 片尾…")
        generate_scene_audio_and_cues(
            ending_scene.narration, ending_audio, storyboard.tts
        )
    ending_dur = probe_duration_sec(ending_audio)
    ending_rendered = RenderedScene(
        scene=ending_scene,
        audio_path=ending_audio,
        audio_duration_sec=ending_dur,
    )
    print(f"  ch{ch:02d} 渲染片尾镜头 ({ending_dur:.1f}s)…")
    render_scene_segment(
        ending_rendered, storyboard, storyboard_path, seg_dir
    )

    segment_paths: list[Path] = []
    rendered_scenes: list[RenderedScene] = []
    for scene in storyboard.all_scenes():
        seg = seg_dir / f"{scene.id}.mp4"
        if not seg.is_file():
            raise FileNotFoundError(f"缺少镜头: {seg}")
        ap = audio_dir / f"{scene.id}.mp3"
        dur = probe_duration_sec(ap) if ap.is_file() else (scene.duration_sec or 3.0)
        segment_paths.append(seg)
        rendered_scenes.append(
            RenderedScene(scene=scene, audio_path=ap, audio_duration_sec=dur)
        )

    comm_filename = storyboard.output.filename
    comm_raw = comm_out_dir / f".{comm_filename}.raw.mp4"
    comm_final = comm_out_dir / comm_filename
    print(f"  ch{ch:02d} 重拼讲解段…")
    concat_segments(segment_paths, comm_raw)
    mixed = mix_bgm_into_video(
        comm_raw,
        ROOT,
        storyboard.bgm,
        rendered_scenes,
        out_path=comm_final,
    )
    if mixed.resolve() != comm_final.resolve():
        shutil.copy2(mixed, comm_final)
    comm_raw.unlink(missing_ok=True)

    read_seg = work / "segments" / f"ch{ch:02d}-read.mp4"
    if not read_seg.is_file() and cfg.get("read_video"):
        read_seg = (ROOT / cfg["read_video"]).resolve()
    if not read_seg.is_file():
        raise FileNotFoundError(f"缺少朗读段: {read_seg}")

    hybrid_concat = work / "hybrid_concat.mp4"
    print(f"  ch{ch:02d} 重拼 hybrid + BGM…")
    _concat_videos(require_ffmpeg(), [read_seg, comm_final], hybrid_concat)

    out = ROOT / f"output/daodejing-ch{ch:02d}-hybrid.mp4"
    read_duration = probe_duration_sec(read_seg)
    bgm_cfg = storyboard.bgm
    if bgm_cfg.enabled or bgm_cfg.tracks:
        bgm = BgmConfig(
            enabled=True,
            tracks=bgm_cfg.tracks,
            volume=bgm_cfg.volume,
            crossfade_sec=bgm_cfg.crossfade_sec,
            fade_in_sec=bgm_cfg.fade_in_sec,
            fade_out_sec=bgm_cfg.fade_out_sec,
            switch_at_scene=bgm_cfg.switch_at_scene,
        )
        bgm_scenes = build_hybrid_bgm_scenes(
            read_id=f"ch{ch:02d}-read",
            read_duration=read_duration,
            storyboard=storyboard,
            comm_work=comm_work,
        )
        mix_bgm_into_video(hybrid_concat, ROOT, bgm, bgm_scenes, out_path=out)
    else:
        shutil.copy2(hybrid_concat, out)

    print(f"  ch{ch:02d} 完成 → {out.relative_to(ROOT)}")


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chapter", type=int, default=None)
    parser.add_argument("--chapters", default="1-81")
    parser.add_argument(
        "--ending-audio-from",
        type=int,
        default=None,
        help="复用指定章节的 ending.mp3（CTA 文案相同时跳过 TTS）",
    )
    args = parser.parse_args()

    load_chapter_config = _import_hybrid_helpers()
    chapters = [args.chapter] if args.chapter else parse_chapters(args.chapters)

    ok = fail = 0
    for ch in chapters:
        print(f"=== ch{ch:02d} ===")
        try:
            refresh_chapter(
                ch,
                load_chapter_config,
                ending_audio_from=args.ending_audio_from,
            )
            ok += 1
        except Exception as exc:
            fail += 1
            print(f"  ch{ch:02d} FAILED: {exc}", file=sys.stderr)

    print(f"\n完成 ok={ok} fail={fail}")
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
