#!/usr/bin/env python3
"""批量上传道德经 81 章到抖音，定时发布，每天 3 篇。

用法：
  # dry-run 预览排期
  python3 scripts/batch_upload_douyin.py --dry-run

  # 真实上传（从第1章开始）
  python3 scripts/batch_upload_douyin.py

  # 从指定章节开始（断点续传）
  python3 scripts/batch_upload_douyin.py --start 10

  # 只上传指定章节
  python3 scripts/batch_upload_douyin.py --chapters 1,2,3

定时计划：从明天（start_date）开始，每天 08:00 / 12:00 / 20:00 各发 1 篇。
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.env_util import load_dotenv
from pipeline.models import Storyboard

# 每天发布的时间点
DAILY_SLOTS = ["08:00", "12:00", "20:00"]

# 抖音合集名称（需在创作者中心手动创建同名合集）
PLAYLIST = "《道德经》八十一期精讲"

# 从哪天开始（默认明天）
def default_start_date() -> str:
    tomorrow = datetime.now() + timedelta(days=1)
    return tomorrow.strftime("%Y-%m-%d")


def build_schedule(
    chapters: list[int],
    start_date: str,
    slots: list[str] = DAILY_SLOTS,
    start_slot: int = 0,
) -> list[tuple[int, str]]:
    """生成 [(chapter, publish_at)] 列表，publish_at 格式 'YYYY-MM-DD HH:MM'。"""
    schedule = []
    start = datetime.strptime(start_date, "%Y-%m-%d")
    slot_idx = start_slot % len(slots)
    day_offset = 0

    for ch in chapters:
        date = start + timedelta(days=day_offset)
        slot = slots[slot_idx]
        publish_at = f"{date.strftime('%Y-%m-%d')} {slot}"
        schedule.append((ch, publish_at))

        slot_idx += 1
        if slot_idx >= len(slots):
            slot_idx = 0
            day_offset += 1

    return schedule


def storyboard_path(ch: int) -> Path:
    return ROOT / f"examples/storyboard-daodejing-ch{ch:02d}-commentary.json"


def video_path(ch: int) -> Path:
    # 优先用 hybrid 版本
    candidates = [
        ROOT / "output" / f"daodejing-ch{ch:02d}-hybrid.mp4",
        ROOT / "output" / f"ch{ch:02d}-hybrid" / "hybrid_concat.mp4",
    ]
    for p in candidates:
        if p.is_file():
            return p
    raise FileNotFoundError(f"ch{ch:02d} 视频未找到，尝试了: {[str(c) for c in candidates]}")


def cover_path(ch: int) -> Path | None:
    p = ROOT / "assets" / "covers" / f"daodejing-ch{ch:02d}-cover.jpg"
    return p if p.is_file() else None


def main() -> int:
    load_dotenv()

    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--start", type=int, default=1, metavar="N",
                        help="从第 N 章开始（默认 1）")
    parser.add_argument("--end", type=int, default=81, metavar="N",
                        help="到第 N 章结束（默认 81）")
    parser.add_argument("--chapters", default=None,
                        help="指定章节，逗号分隔，如 1,2,3")
    parser.add_argument("--start-date", default=default_start_date(),
                        metavar="YYYY-MM-DD",
                        help=f"排期起始日期（默认明天 {default_start_date()}）")
    parser.add_argument("--start-slot", type=int, default=0, metavar="N",
                        help="从第几个时间槽开始：0=08:00, 1=12:00, 2=20:00（默认 0）")
    parser.add_argument("--playlist", default=PLAYLIST,
                        help=f"抖音合集名称（默认: {PLAYLIST}）")
    parser.add_argument("--dry-run", action="store_true",
                        help="只打印排期，不实际上传")
    parser.add_argument("--interval", type=float, default=30.0,
                        help="两次上传之间的间隔秒数（默认 30s）")
    args = parser.parse_args()

    if args.chapters:
        chapters = [int(x.strip()) for x in args.chapters.split(",")]
    else:
        chapters = list(range(args.start, args.end + 1))

    schedule = build_schedule(chapters, args.start_date, start_slot=args.start_slot)

    print(f"\n── 抖音批量上传排期 ──────────────────────────────")
    print(f"  合集:     {args.playlist}")
    print(f"  总章节:   {len(chapters)} 章（{chapters[0]}~{chapters[-1]}）")
    print(f"  起始日期: {args.start_date}")
    print(f"  完成日期: {schedule[-1][1].split()[0]}")
    print(f"  每日时间: {' / '.join(DAILY_SLOTS)}")
    print(f"──────────────────────────────────────────────────")

    if args.dry_run:
        print("\n排期预览（dry-run）:")
        for ch, pub in schedule:
            try:
                vp = video_path(ch)
                v_status = "✓"
            except FileNotFoundError:
                v_status = "✗ 视频缺失"
            print(f"  ch{ch:02d}  {pub}  {v_status}")
        print("\n（dry-run 模式，不实际上传）")
        return 0

    # ── 真实上传 ──────────────────────────────────────────────────
    from pipeline.douyin_upload import upload_video, cookie_path

    account_file = cookie_path(ROOT)
    if not account_file.is_file():
        print("❌ 未找到 Cookie，请先运行: python3 scripts/upload_douyin.py --auth-only")
        return 1

    success = []
    failed = []

    for i, (ch, pub) in enumerate(schedule):
        print(f"\n[{i+1}/{len(schedule)}] 上传 ch{ch:02d} → 定时 {pub}")

        # 检查视频
        try:
            vp = video_path(ch)
        except FileNotFoundError as e:
            print(f"⚠️  跳过: {e}")
            failed.append(ch)
            continue

        # 读取 storyboard
        sb_path = storyboard_path(ch)
        if not sb_path.is_file():
            print(f"⚠️  分镜不存在: {sb_path}，跳过")
            failed.append(ch)
            continue

        storyboard = Storyboard.load(sb_path)

        # 注入合集名到 douyin config
        storyboard.douyin.playlist = args.playlist

        # 封面
        cp = cover_path(ch)

        try:
            result = upload_video(
                vp,
                storyboard,
                project_root=ROOT,
                cover_path=cp,
                publish_at=pub,
                dry_run=False,
            )
            print(f"  ✓ ch{ch:02d} 发布成功: {result.get('url', '')}")
            success.append(ch)
        except Exception as exc:
            print(f"  ❌ ch{ch:02d} 上传失败: {exc}")
            failed.append(ch)

        # 两次上传之间等待，避免触发风控
        if i < len(schedule) - 1:
            print(f"  等待 {args.interval}s…")
            time.sleep(args.interval)

    print(f"\n── 批量上传完成 ──────────────────────────────────")
    print(f"  成功: {len(success)} 章  {success}")
    print(f"  失败: {len(failed)} 章  {failed}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
