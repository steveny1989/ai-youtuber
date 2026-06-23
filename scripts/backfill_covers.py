#!/usr/bin/env python3
"""为已上传稿件补传封面（YouTube 缩略图 + B 站封面）。

示例：
  export HTTPS_PROXY=http://127.0.0.1:7890   # YouTube 需要
  python3 scripts/backfill_covers.py --chapters 1-39
  python3 scripts/backfill_covers.py --chapters 1-39 --youtube-only
  python3 scripts/backfill_covers.py --chapters 6-39 --dry-run
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.brand import COVER_OUTPUT_DIR  # noqa: E402
from pipeline.env_util import load_dotenv  # noqa: E402
from pipeline.models import Storyboard  # noqa: E402
from pipeline.series_config import registry_by_chapter  # noqa: E402


def parse_chapters(spec: str) -> list[int]:
    spec = spec.strip()
    if "-" in spec:
        a, b = spec.split("-", 1)
        return list(range(int(a), int(b) + 1))
    return [int(x) for x in spec.split(",") if x.strip()]


def storyboard_path(ch: int) -> Path:
    return ROOT / f"examples/storyboard-daodejing-ch{ch:02d}-commentary.json"


def cover_path(ch: int) -> Path:
    return ROOT / COVER_OUTPUT_DIR / f"daodejing-ch{ch:02d}-cover.jpg"


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chapters", default="1-39")
    parser.add_argument("--youtube-only", action="store_true")
    parser.add_argument("--bilibili-only", action="store_true")
    parser.add_argument("--delay-yt", type=float, default=25.0, help="YouTube 章间间隔秒")
    parser.add_argument("--delay-bili", type=float, default=45.0, help="B 站章间间隔秒")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    chapters = parse_chapters(args.chapters)
    do_yt = not args.bilibili_only
    do_bili = not args.youtube_only
    reg = registry_by_chapter(ROOT)

    plan: list[tuple[int, str, str]] = []
    for ch in chapters:
        row = reg.get(ch, {})
        yt_id = str((row.get("youtube") or {}).get("video_id", "")).strip()
        bvid = str((row.get("bilibili") or {}).get("bvid", "")).strip()
        cov = cover_path(ch)
        if not cov.is_file():
            print(f"[ch{ch:02d}] 跳过：封面不存在 {cov.name}", file=sys.stderr)
            continue
        if not storyboard_path(ch).is_file():
            print(f"[ch{ch:02d}] 跳过：分镜不存在", file=sys.stderr)
            continue
        if do_yt and not yt_id:
            print(f"[ch{ch:02d}] 跳过 YouTube：registry 无 video_id", file=sys.stderr)
        if do_bili and not bvid:
            print(f"[ch{ch:02d}] 跳过 B 站：registry 无 bvid", file=sys.stderr)
        if (do_yt and yt_id) or (do_bili and bvid):
            plan.append((ch, yt_id, bvid))

    print(f"补封面计划：{len(plan)} 章")
    for ch, yt_id, bvid in plan:
        parts = []
        if do_yt and yt_id:
            parts.append(f"YT {yt_id}")
        if do_bili and bvid:
            parts.append(f"B站 {bvid}")
        print(f"  ch{ch:02d}  {' | '.join(parts)}  ← {cover_path(ch).name}")

    if args.dry_run or not plan:
        return 0

    rc = 0
    first = True
    for ch, yt_id, bvid in plan:
        if not first:
            time.sleep(1.0)
        first = False
        sb = storyboard_path(ch)
        cov = cover_path(ch)

        if do_yt and yt_id:
            if args.delay_yt > 0 and ch != plan[0][0]:
                print(f"等待 {args.delay_yt:.0f}s（YouTube 限频）…", flush=True)
                time.sleep(args.delay_yt)
            print(f"\n[ch{ch:02d}] YouTube 缩略图…", flush=True)
            proc = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/upload_youtube.py"),
                    str(sb),
                    "--thumbnail-only",
                    "--video-id",
                    yt_id,
                ],
                cwd=ROOT,
            )
            if proc.returncode != 0:
                print(f"[ch{ch:02d}] YouTube 失败 exit={proc.returncode}", file=sys.stderr)
                rc = proc.returncode

        if do_bili and bvid:
            if args.delay_bili > 0 and ch != plan[0][0]:
                print(f"等待 {args.delay_bili:.0f}s（B 站限频）…", flush=True)
                time.sleep(args.delay_bili)
            print(f"\n[ch{ch:02d}] B 站封面…", flush=True)
            try:
                import os

                from pipeline.bilibili_upload import update_video_cover

                os.environ.setdefault("BILIBILI_CLEAR_PROXY", "1")
                storyboard = Storyboard.load(sb)
                update_video_cover(
                    bvid,
                    cov,
                    storyboard,
                    project_root=ROOT,
                )
                print(f"[ch{ch:02d}] B 站封面完成 ✓", flush=True)
            except Exception as exc:
                print(f"[ch{ch:02d}] B 站失败: {exc!r}", file=sys.stderr)
                rc = 1

    print("\n补封面完成。")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
