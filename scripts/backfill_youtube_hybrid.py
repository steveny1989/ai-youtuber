#!/usr/bin/env python3
"""补传 hybrid 单章到 YouTube（跳过已成功章节，控制频率防 429）。

示例：
  export HTTPS_PROXY=http://127.0.0.1:7890
  export YOUTUBE_PLAYLIST_DAODEJING_81=PLxxxxxxxx

  # 写入播放列表 ID 并 patch 分镜
  python3 scripts/setup_daodejing_81_series.py --set-youtube-playlist PLxxxxxxxx

  # 补传第 16–35 章（默认跳过 log 里已成功的 6–15）
  python3 scripts/backfill_youtube_hybrid.py --chapters 16-35

  # 今天只传 3 集，每集间隔 30 分钟
  python3 scripts/backfill_youtube_hybrid.py --chapters 16-35 --max-per-run 3 --delay-min 30
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.env_util import load_dotenv  # noqa: E402
from pipeline.series_config import (  # noqa: E402
    load_daodejing_81_series,
    registry_by_chapter,
    resolve_youtube_playlist_id,
)


def parse_chapters(spec: str) -> list[int]:
    spec = spec.strip()
    if "-" in spec:
        a, b = spec.split("-", 1)
        return list(range(int(a), int(b) + 1))
    return [int(x) for x in spec.split(",") if x.strip()]


def youtube_success_from_log(log_path: Path) -> dict[int, str]:
    """从 batch log 解析已成功 YouTube 上传：{chapter: video_id}。"""
    if not log_path.is_file():
        return {}
    text = log_path.read_text(encoding="utf-8", errors="replace")
    out: dict[int, str] = {}
    current_ch: int | None = None
    for line in text.splitlines():
        m = re.match(r"\[ch(\d{2})\] YouTube 上传", line)
        if m:
            current_ch = int(m.group(1))
            continue
        if current_ch is not None and "上传完成:" in line:
            vm = re.search(r"watch\?v=([A-Za-z0-9_-]+)", line)
            if vm:
                out[current_ch] = vm.group(1)
            current_ch = None
        if current_ch is not None and ("YouTube 失败" in line or "Traceback" in line):
            # 失败直到下一章标记
            if "YouTube 失败" in line:
                current_ch = None
    return out


def youtube_done_chapters(project_root: Path, log_path: Path) -> dict[int, str]:
    """已上传章节：合并 batch log + registry。"""
    done = youtube_success_from_log(log_path)
    for ch, plat in registry_by_chapter(project_root).items():
        row = plat.get("youtube") or {}
        vid = str(row.get("video_id", "")).strip()
        if vid:
            done[ch] = vid
    return done


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chapters", default="16-35")
    parser.add_argument(
        "--log",
        type=Path,
        default=ROOT / "output/hybrid-upload-ch6-35.log",
        help="批量上传日志，用于跳过已成功章节",
    )
    parser.add_argument(
        "--playlist-id",
        default="",
        help="PL…（默认读 env / series_daodejing_81.json）",
    )
    parser.add_argument(
        "--privacy",
        choices=("private", "unlisted", "public"),
        default="public",
        help="补传默认 public（不再用旧定时）",
    )
    parser.add_argument(
        "--max-per-run",
        type=int,
        default=6,
        help="本次最多上传几集（YouTube 日配额约 6–10，默认 6）",
    )
    parser.add_argument(
        "--delay-min",
        type=float,
        default=20.0,
        help="每集之间的间隔分钟数",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    chapters = parse_chapters(args.chapters)
    done = youtube_done_chapters(ROOT, args.log.resolve())
    playlist_id = (args.playlist_id or "").strip()
    if not playlist_id:
        playlist_id = load_daodejing_81_series(ROOT).youtube_playlist_id
    if not playlist_id:
        print(
            "警告：未配置播放列表 ID。上传仍会继续，但不会自动加入列表。\n"
            "  python3 scripts/setup_daodejing_81_series.py --set-youtube-playlist PLxxxxxxxx",
            file=sys.stderr,
        )

    todo: list[int] = []
    for ch in chapters:
        if ch in done:
            print(f"  跳过 ch{ch:02d}（已上传 v={done[ch]}）")
            continue
        video = ROOT / f"output/daodejing-ch{ch:02d}-hybrid.mp4"
        sb = ROOT / f"examples/storyboard-daodejing-ch{ch:02d}-commentary.json"
        if not video.is_file():
            print(f"  跳过 ch{ch:02d}：缺成片 {video.name}", file=sys.stderr)
            continue
        if not sb.is_file():
            print(f"  跳过 ch{ch:02d}：缺分镜", file=sys.stderr)
            continue
        todo.append(ch)

    if not todo:
        print("没有待补传章节。")
        return 0

    limit = max(1, args.max_per_run)
    batch = todo[:limit]
    print(f"待补传 {len(todo)} 章，本次上传 {len(batch)} 章：{batch}")
    if playlist_id:
        print(f"播放列表: {playlist_id}")
    print(f"可见性: {args.privacy}\n")

    if args.dry_run:
        return 0

    uploaded = 0
    for i, ch in enumerate(batch):
        if i > 0 and args.delay_min > 0:
            sec = int(args.delay_min * 60)
            print(f"等待 {args.delay_min:.0f} 分钟…")
            time.sleep(sec)

        video = ROOT / f"output/daodejing-ch{ch:02d}-hybrid.mp4"
        sb = ROOT / f"examples/storyboard-daodejing-ch{ch:02d}-commentary.json"
        audio = ROOT / f"output/ch{ch:02d}-hybrid/commentary.work/audio"
        read = ROOT / f"output/ch{ch:02d}-hybrid/segments/ch{ch:02d}-read.mp4"

        cmd = [
            sys.executable,
            str(ROOT / "scripts/upload_youtube.py"),
            str(sb),
            "--video",
            str(video),
            "--audio-dir",
            str(audio),
            "--read-video",
            str(read),
            "--privacy",
            args.privacy,
        ]
        if playlist_id:
            cmd.extend(["--playlist-id", playlist_id])

        print(f"[ch{ch:02d}] YouTube 上传…")
        rc = subprocess.call(cmd, cwd=ROOT)
        if rc != 0:
            print(f"[ch{ch:02d}] 失败 exit={rc}", file=sys.stderr)
            if rc != 0:
                print(
                    "若 HTTP 429，说明当日上传配额已满，明天再跑本脚本。",
                    file=sys.stderr,
                )
            return rc
        uploaded += 1

    print(f"\n本次成功上传 {uploaded} 集。")
    if len(todo) > len(batch):
        rest = todo[len(batch) :]
        print(f"剩余 {len(rest)} 章：{rest[:8]}{'…' if len(rest) > 8 else ''}")
        print("明天或配额恢复后继续：")
        print(
            f"  python3 scripts/backfill_youtube_hybrid.py --chapters {rest[0]}-{rest[-1]}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
