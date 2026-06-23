#!/usr/bin/env python3
"""每天按顺序各传 3 章到 YouTube + B 站（定时公开，每天 3 集间隔 3 小时）。

用法：
  export HTTPS_PROXY=http://127.0.0.1:7890   # YouTube 需要
  python3 scripts/upload_hybrid_daily_3.py              # 今日各平台 3 集
  python3 scripts/upload_hybrid_daily_3.py --dry-run
  python3 scripts/upload_hybrid_daily_3.py --count 5    # 今日每平台 5 集（慎用 YT 配额）

YouTube 从 ch24 补到与 B 站对齐；B 站从 ch36 起（ch6–35 已批量提交）。
跳过无成片章节（历史空章已补全，现无跳过）。
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.env_util import load_dotenv  # noqa: E402
from pipeline.youtube_upload import parse_publish_datetime  # noqa: E402

BILI_BATCH_LOG = ROOT / "output/hybrid-upload-ch6-35.log"
YT_BACKFILL_LOG = ROOT / "output/youtube-backfill.log"
REGISTRY = ROOT / "output/series_daodejing_81_registry.jsonl"

# B 站 ch6–35 批量计划末章公开时间 → ch36 从次日 09:00 起
BILI_PUBLISH_AFTER_35 = "2026-06-05T09:00:00+08:00"
# YouTube 与 B 站 ch24–35 对齐的公开起点
YT_CATCHUP_START = "2026-06-02T18:00:00+08:00"
SKIP_CHAPTERS: set[int] = set()


def parse_chapters(spec: str) -> list[int]:
    spec = spec.strip()
    if "-" in spec:
        a, b = spec.split("-", 1)
        return list(range(int(a), int(b) + 1))
    return [int(x) for x in spec.split(",") if x.strip()]


def _bili_ok_from_log() -> set[int]:
    if not BILI_BATCH_LOG.is_file():
        return set()
    ok: set[int] = set()
    cur: int | None = None
    for line in BILI_BATCH_LOG.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(r"\[ch(\d{2})\] B 站", line)
        if m:
            cur = int(m.group(1))
        if cur and "投稿完成" in line:
            ok.add(cur)
            cur = None
        if cur and "B 站失败" in line:
            cur = None
    return ok


def _youtube_ok() -> set[int]:
    done: set[int] = set()
    if REGISTRY.is_file():
        for line in REGISTRY.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            if r.get("platform") == "youtube" and r.get("video_id"):
                done.add(int(r["chapter"]))
    for log in (YT_BACKFILL_LOG, BILI_BATCH_LOG):
        if not log.is_file():
            continue
        cur = None
        for line in log.read_text(encoding="utf-8", errors="replace").splitlines():
            m = re.match(r"\[ch(\d{2})\] YouTube", line)
            if m:
                cur = int(m.group(1))
            if cur and "上传完成:" in line and "youtube" in line:
                done.add(cur)
                cur = None
            if cur and "YouTube 失败" in line:
                cur = None
    return done


def _ready_chapters() -> list[int]:
    out: list[int] = []
    for ch in range(6, 82):
        if ch in SKIP_CHAPTERS:
            continue
        if (ROOT / f"output/daodejing-ch{ch:02d}-hybrid.mp4").is_file():
            out.append(ch)
    return out


def _publish_at_for_index(
    start: datetime, index: int, *, per_day: int, slot_hours: float
) -> datetime:
    day_off = index // per_day
    slot = index % per_day
    return start + timedelta(days=day_off) + timedelta(hours=slot * slot_hours)


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=3, help="每平台今日上传集数")
    parser.add_argument("--per-day", type=int, default=3, help="定时公开：每天几集")
    parser.add_argument("--slot-hours", type=float, default=3.0)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--youtube-only", action="store_true")
    parser.add_argument("--bilibili-only", action="store_true")
    args = parser.parse_args()

    ready = _ready_chapters()
    bili_done = _bili_ok_from_log()
    yt_done = _youtube_ok()

    bili_todo = sorted(ch for ch in ready if ch not in bili_done)
    yt_todo = sorted(ch for ch in ready if ch not in yt_done)

    bili_start = parse_publish_datetime(BILI_PUBLISH_AFTER_35)
    yt_start = parse_publish_datetime(YT_CATCHUP_START)

    # B 站主序列从 ch36 起（ch6–35 已批量提交；<36 为历史失败需单独补传）
    bili_retry = [ch for ch in bili_todo if ch < 36]
    bili_main = [ch for ch in bili_todo if ch >= 36]
    bili_batch = bili_main[: max(0, args.count)]
    yt_batch = yt_todo[: max(0, args.count)]

    print("=== 今日上传计划 ===")
    if not args.bilibili_only and yt_batch:
        print("YouTube:")
        for i, ch in enumerate(yt_batch):
            idx = ch - 24 if ch >= 24 else ch - 6
            dt = _publish_at_for_index(
                yt_start, max(0, idx), per_day=args.per_day, slot_hours=args.slot_hours
            )
            print(f"  ch{ch:02d}  定时 {dt.isoformat()}")
    if not args.youtube_only and bili_batch:
        print("B 站:")
        for ch in bili_batch:
            base_idx = ch - 36
            dt = _publish_at_for_index(
                bili_start, base_idx, per_day=args.per_day, slot_hours=args.slot_hours
            )
            print(f"  ch{ch:02d}  定时 {dt.isoformat()}")
    if bili_retry and not args.youtube_only:
        print(f"B 站待补传（<36，需另跑）: {bili_retry}")
    print(f"\nYouTube 待传 {len(yt_todo)} 章 | B 站待传 {len(bili_todo)} 章（主序列 {len(bili_main)}）")
    print()

    if args.dry_run:
        return 0

    rc = 0
    if not args.bilibili_only and yt_batch:
        ch_spec = ",".join(str(c) for c in yt_batch)
        first = yt_batch[0]
        idx = first - 24 if first >= 24 else first - 6
        start_dt = _publish_at_for_index(
            yt_start, max(0, idx), per_day=args.per_day, slot_hours=args.slot_hours
        )
        cmd = [
            sys.executable,
            str(ROOT / "scripts/upload_hybrid_batch.py"),
            "--youtube-only",
            "--chapters",
            ch_spec,
            "--publish-start",
            start_dt.isoformat(),
            "--per-day",
            str(args.per_day),
            "--slot-hours",
            str(args.slot_hours),
        ]
        print("执行:", " ".join(cmd))
        rc = subprocess.call(cmd, cwd=ROOT) or rc

    if not args.youtube_only and bili_batch:
        ch_spec = ",".join(str(c) for c in bili_batch)
        first = bili_batch[0]
        base_idx = first - 36
        start_dt = _publish_at_for_index(
            bili_start, base_idx, per_day=args.per_day, slot_hours=args.slot_hours
        )
        cmd = [
            sys.executable,
            str(ROOT / "scripts/upload_hybrid_batch.py"),
            "--bilibili-only",
            "--chapters",
            ch_spec,
            "--publish-start",
            start_dt.isoformat(),
            "--per-day",
            str(args.per_day),
            "--slot-hours",
            str(args.slot_hours),
        ]
        print("执行:", " ".join(cmd))
        rc = subprocess.call(cmd, cwd=ROOT) or rc

    return rc


if __name__ == "__main__":
    raise SystemExit(main())
