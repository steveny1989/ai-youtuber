#!/usr/bin/env python3
"""批量上传 hybrid 章节到 YouTube + B 站，支持定时发布。

示例（第 6–10 章，5 月 30 日起每天 8:00 公开）：
  python3 scripts/upload_hybrid_batch.py --chapters 6-10 \\
    --publish-start 2026-05-30T08:00:00+08:00 --interval-days 1

每天 5 集、同一天内每隔 3 小时公开一集（09:00 / 12:00 / …）：
  python3 scripts/upload_hybrid_batch.py --chapters 6-35 \\
    --publish-start 2026-05-30T09:00:00+08:00 --per-day 5 --slot-hours 3

仅打印计划（不上传）：
  python3 scripts/upload_hybrid_batch.py --chapters 6-10 --dry-run \\
    --publish-start 2026-05-30T08:00:00+08:00
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.env_util import load_dotenv  # noqa: E402
from pipeline.youtube_upload import parse_publish_datetime  # noqa: E402


def parse_chapters(spec: str) -> list[int]:
    spec = spec.strip()
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


def publish_at_for_chapter(
    ch: int,
    start: datetime,
    *,
    per_day: int,
    slot_hours: float,
    interval_days: int,
    base_ch: int,
    first_day_count: int = 0,
) -> datetime:
    idx = ch - base_ch
    if idx < 0:
        raise ValueError(f"chapter {ch} < base-chapter {base_ch}")
    per_day = max(1, per_day)
    if first_day_count > 0:
        if idx < first_day_count:
            if first_day_count == 1:
                return start
            return start + timedelta(hours=idx * slot_hours)
        rem = idx - first_day_count
        day_off = rem // per_day + 1
        slot = rem % per_day
        day_anchor = start.replace(hour=9, minute=0, second=0, microsecond=0)
        return day_anchor + timedelta(days=day_off) + timedelta(hours=slot * slot_hours)
    if per_day > 1:
        day_off = idx // per_day
        slot = idx % per_day
        return start + timedelta(days=day_off) + timedelta(hours=slot * slot_hours)
    return start + timedelta(days=idx * interval_days)


def effective_bilibili_publish_at(dt: datetime) -> datetime | None:
    """B 站定时发布须在 5 分钟～15 天内；超出则先投稿，稍后在创作中心补设定时。"""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("Asia/Shanghai"))
    now = datetime.now(dt.tzinfo)
    max_at = now + timedelta(days=15) - timedelta(minutes=5)
    min_at = now + timedelta(minutes=6)
    if dt > max_at:
        return None
    if dt < min_at:
        return min_at
    return dt


def _storyboard_upload_args(
    sb: Path,
    video: Path,
    audio: Path,
    read: Path,
    *,
    publish_at: datetime | None,
) -> list[str]:
    args = [
        str(sb),
        "--video",
        str(video),
        "--audio-dir",
        str(audio),
        "--read-video",
        str(read),
    ]
    if publish_at is not None:
        args.extend(["--publish-at", publish_at.isoformat()])
    return args


def uploaded_chapters_from_log(path: Path) -> set[int]:
    """从上传日志解析已成功投稿的章号（按「即将上传 B 站」→「投稿完成」配对）。"""
    if not path.is_file():
        return set()
    ok: set[int] = set()
    cur: int | None = None
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if "即将上传 B 站" in line:
            cur = None
        m = re.search(r"daodejing-ch(\d+)-hybrid", line)
        if m and ("视频:" in line or "即将上传" in line):
            cur = int(m.group(1))
        if cur and ("投稿完成:" in line or "上传完成:" in line):
            if "bilibili.com" in line or "youtube.com" in line:
                ok.add(cur)
                cur = None
    return ok


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chapters", default="6-10", help="如 6-10 或 6,7,8")
    parser.add_argument(
        "--publish-start",
        default="2026-05-30T08:00:00+08:00",
        help="第一章定时公开时间（ISO8601）",
    )
    parser.add_argument(
        "--interval-days",
        type=int,
        default=1,
        help="各章公开间隔天数（--per-day 为 1 时生效，默认每天一集）",
    )
    parser.add_argument(
        "--per-day",
        type=int,
        default=1,
        help="每天定时公开的视频数（默认 1；与 --slot-hours 配合）",
    )
    parser.add_argument(
        "--slot-hours",
        type=float,
        default=3.0,
        help="同一天内各章公开时间间隔（小时，默认 3）",
    )
    parser.add_argument(
        "--first-day-count",
        type=int,
        default=0,
        help="首日定时公开数量（如 1：今天只发 1 集，其余按 --per-day 从次日 09:00 起）",
    )
    parser.add_argument(
        "--base-chapter",
        type=int,
        default=1,
        help="定时发布序号基准章（默认 1：第 N 章公开时间按 N-1 槽位计算）",
    )
    parser.add_argument(
        "--delay-sec",
        type=float,
        default=0,
        help="各章上传间隔秒数（减轻 B 站 406 限频）",
    )
    parser.add_argument(
        "--resume-log",
        type=Path,
        default=None,
        help="跳过日志中已「投稿完成」的章",
    )
    parser.add_argument("--youtube-only", action="store_true")
    parser.add_argument("--bilibili-only", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    chapters = parse_chapters(args.chapters)
    start = parse_publish_datetime(args.publish_start)
    do_yt = not args.bilibili_only
    do_bili = not args.youtube_only
    done = uploaded_chapters_from_log(args.resume_log) if args.resume_log else set()

    plan: list[tuple[int, datetime]] = []
    per_day = max(1, args.per_day)
    for ch in chapters:
        dt = publish_at_for_chapter(
            ch,
            start,
            per_day=per_day,
            slot_hours=args.slot_hours,
            interval_days=args.interval_days,
            base_ch=args.base_chapter,
            first_day_count=max(0, args.first_day_count),
        )
        plan.append((ch, dt))

    print("上传计划：")
    for ch, dt in plan:
        iso = dt.isoformat()
        video = ROOT / f"output/daodejing-ch{ch:02d}-hybrid.mp4"
        sb = ROOT / f"examples/storyboard-daodejing-ch{ch:02d}-commentary.json"
        ok = "✓" if video.is_file() else "✗ 缺成片"
        skip = "（已传，跳过）" if ch in done else ""
        print(f"  第{ch:02d}章  公开 {iso}  {video.name} {ok}{skip}")
    print()

    if args.dry_run:
        return 0

    first = True
    for ch, dt in plan:
        if ch in done:
            print(f"[ch{ch:02d}] 跳过（resume-log 已成功）")
            continue
        if not first and args.delay_sec > 0:
            print(f"等待 {args.delay_sec:.0f}s（限频间隔）…", flush=True)
            time.sleep(args.delay_sec)
        first = False
        iso = dt.isoformat()
        video = ROOT / f"output/daodejing-ch{ch:02d}-hybrid.mp4"
        sb = ROOT / f"examples/storyboard-daodejing-ch{ch:02d}-commentary.json"
        audio = ROOT / f"output/ch{ch:02d}-hybrid/commentary.work/audio"
        read = ROOT / f"output/ch{ch:02d}-hybrid/segments/ch{ch:02d}-read.mp4"

        if not video.is_file():
            print(f"[ch{ch:02d}] 跳过：成片不存在 {video}", file=sys.stderr)
            continue
        if not sb.is_file():
            print(f"[ch{ch:02d}] 跳过：分镜不存在 {sb}", file=sys.stderr)
            continue

        common = _storyboard_upload_args(sb, video, audio, read, publish_at=dt)
        bili_dt = effective_bilibili_publish_at(dt)
        bili_args = _storyboard_upload_args(sb, video, audio, read, publish_at=bili_dt)

        if do_yt:
            print(f"[ch{ch:02d}] YouTube 上传（定时 {iso}）…")
            yt_env = os.environ.copy()
            yt_env.setdefault("PYTHONUNBUFFERED", "1")
            rc = subprocess.call(
                [
                    sys.executable,
                    str(ROOT / "scripts/upload_youtube.py"),
                    *common,
                    "--privacy",
                    "private",
                ],
                cwd=ROOT,
                env=yt_env,
            )
            if rc != 0:
                print(f"[ch{ch:02d}] YouTube 失败 exit={rc}", file=sys.stderr)
                if args.delay_sec > 0:
                    extra = min(600.0, args.delay_sec * 3)
                    print(f"退避，额外等待 {extra:.0f}s…", flush=True)
                    time.sleep(extra)

        if do_bili:
            if bili_dt is None:
                print(
                    f"[ch{ch:02d}] B 站上传（计划 {iso} 超出15天，先投稿不设定时）…",
                    flush=True,
                )
            else:
                print(
                    f"[ch{ch:02d}] B 站上传（定时 {bili_dt.isoformat()}）…",
                    flush=True,
                )
            bili_env = os.environ.copy()
            bili_env.setdefault("BILIBILI_CLEAR_PROXY", "1")
            bili_env.setdefault("PYTHONUNBUFFERED", "1")
            rc = subprocess.call(
                [
                    sys.executable,
                    str(ROOT / "scripts/upload_bilibili.py"),
                    *bili_args,
                    "--upload",
                ],
                cwd=ROOT,
                env=bili_env,
            )
            if rc != 0:
                print(f"[ch{ch:02d}] B 站失败 exit={rc}，60s 后重试一次…", file=sys.stderr)
                time.sleep(60)
                rc = subprocess.call(
                    [
                        sys.executable,
                        str(ROOT / "scripts/upload_bilibili.py"),
                        *bili_args,
                        "--upload",
                    ],
                    cwd=ROOT,
                    env=bili_env,
                )
            if rc != 0:
                print(f"[ch{ch:02d}] B 站失败 exit={rc}", file=sys.stderr)
                if args.delay_sec > 0:
                    extra = min(600.0, args.delay_sec * 3)
                    print(f"限频退避，额外等待 {extra:.0f}s…", flush=True)
                    time.sleep(extra)

    print("\n批量上传完成。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
