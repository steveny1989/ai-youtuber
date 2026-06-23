#!/usr/bin/env python3
"""Batch overlay top-left brand watermark on chapter MP4s."""

from __future__ import annotations

import argparse
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.brand import WATERMARK_IMAGE  # noqa: E402
from pipeline.ffmpeg_util import require_ffmpeg  # noqa: E402
from pipeline.frame import render_brand_watermark_rgba  # noqa: E402
from pipeline.models import StyleConfig, WatermarkConfig  # noqa: E402

DEFAULT_DIR = ROOT / "assets/DaoDeJing/animations/final_81_chapters"
FRAME_WIDTH = 1920
FRAME_HEIGHT = 1080


def overlay_watermark(
    input_mp4: Path,
    overlay_png: Path,
    output_mp4: Path,
    *,
    crf: int,
) -> None:
    ffmpeg = require_ffmpeg()
    output_mp4.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg,
        "-y",
        "-i",
        str(input_mp4),
        "-i",
        str(overlay_png),
        "-filter_complex",
        "[0:v][1:v]overlay=0:0:format=auto",
        "-map",
        "0:a?",
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        str(crf),
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "copy",
        str(output_mp4),
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def _process_one(
    input_mp4: str,
    overlay_png: str,
    crf: int,
    dry_run: bool,
) -> tuple[str, str | None]:
    inp = Path(input_mp4)
    if dry_run:
        return str(inp), None
    tmp = inp.with_suffix(".wm.tmp.mp4")
    try:
        overlay_watermark(inp, Path(overlay_png), tmp, crf=crf)
        tmp.replace(inp)
        return str(inp), None
    except subprocess.CalledProcessError as exc:
        if tmp.exists():
            tmp.unlink(missing_ok=True)
        err = (exc.stderr or exc.stdout or str(exc)).strip()
        return str(inp), err or "ffmpeg failed"
    except Exception as exc:
        if tmp.exists():
            tmp.unlink(missing_ok=True)
        return str(inp), str(exc)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "directory",
        nargs="?",
        type=Path,
        default=DEFAULT_DIR,
        help="Directory of chapter MP4 files",
    )
    parser.add_argument("--pattern", default="Chapter_*_v6.mp4")
    parser.add_argument("--crf", type=int, default=18)
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    video_dir = args.directory.resolve()
    videos = sorted(video_dir.glob(args.pattern))
    if not videos:
        print(f"No videos matching {args.pattern!r} in {video_dir}", file=sys.stderr)
        return 1

    logo_path = ROOT / WATERMARK_IMAGE
    if not logo_path.exists():
        print(f"Logo not found: {logo_path}", file=sys.stderr)
        return 1

    wm = WatermarkConfig()
    style = StyleConfig()
    overlay = render_brand_watermark_rgba(
        FRAME_WIDTH,
        FRAME_HEIGHT,
        logo_path,
        wm,
        style,
    )
    overlay_png = video_dir / ".brand_watermark_overlay.png"
    overlay.save(overlay_png)

    print(f"Watermark: {logo_path.name} @ ({wm.margin_x}, {wm.margin_y})")
    print(f"Processing {len(videos)} videos in {video_dir} (jobs={args.jobs})")

    failed: list[tuple[str, str]] = []
    overlay_str = str(overlay_png)
    with ProcessPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        futures = [
            pool.submit(_process_one, str(v), overlay_str, args.crf, args.dry_run)
            for v in videos
        ]
        done = 0
        for fut in as_completed(futures):
            path, err = fut.result()
            done += 1
            if err:
                failed.append((path, err))
                print(f"[{done}/{len(videos)}] FAIL {Path(path).name}: {err[:200]}")
            else:
                print(f"[{done}/{len(videos)}] OK {Path(path).name}")

    if not args.dry_run:
        overlay_png.unlink(missing_ok=True)

    if failed:
        print(f"\n{len(failed)} failed.", file=sys.stderr)
        return 1
    print(f"\nDone. {len(videos)} videos watermarked.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
