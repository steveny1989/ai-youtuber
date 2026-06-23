#!/usr/bin/env python3
"""从登记册删除已上传的 YouTube / B 站视频。

示例（仅 B 站，第 1–39 章登记册内全部唯一 bvid）：
  BILIBILI_CLEAR_PROXY=1 python3 scripts/delete_uploaded_videos.py \\
    --platform bilibili --chapters 1-39 --dry-run
  BILIBILI_CLEAR_PROXY=1 python3 scripts/delete_uploaded_videos.py \\
    --platform bilibili --chapters 1-39 --confirm --delay-sec 45
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.bilibili_upload import BilibiliCaptchaRequiredError  # noqa: E402
from pipeline.env_util import load_dotenv  # noqa: E402
from pipeline.series_config import load_registry, registry_path  # noqa: E402


def parse_chapters(spec: str | None) -> set[int] | None:
    if not spec:
        return None
    spec = spec.strip()
    out: set[int] = set()
    if "-" in spec:
        a, b = spec.split("-", 1)
        out.update(range(int(a), int(b) + 1))
    else:
        for part in spec.split(","):
            part = part.strip()
            if part:
                out.add(int(part))
    return out


def collect_bilibili_targets(
    *,
    chapter_filter: set[int] | None,
) -> list[dict]:
    """登记册内全部 B 站条目，按 bvid 去重（保留最新 aid）。"""
    by_bvid: dict[str, dict] = {}
    for row in load_registry(ROOT):
        if row.get("platform") != "bilibili":
            continue
        ch = int(row.get("chapter", 0))
        if chapter_filter is not None and ch not in chapter_filter:
            continue
        bvid = str(row.get("bvid", "")).strip()
        aid = int(row.get("aid", 0) or 0)
        if not bvid and aid <= 0:
            continue
        key = bvid or f"aid:{aid}"
        by_bvid[key] = {
            "chapter": ch,
            "bvid": bvid,
            "aid": aid,
            "url": row.get("url", ""),
            "ts": row.get("ts", ""),
        }
    return sorted(by_bvid.values(), key=lambda r: (r["chapter"], r["bvid"]))


def collect_youtube_targets(
    *,
    chapter_filter: set[int] | None,
) -> list[dict]:
    by_vid: dict[str, dict] = {}
    for row in load_registry(ROOT):
        if row.get("platform") != "youtube":
            continue
        ch = int(row.get("chapter", 0))
        if chapter_filter is not None and ch not in chapter_filter:
            continue
        vid = str(row.get("video_id", "")).strip()
        if not vid:
            continue
        by_vid[vid] = {
            "chapter": ch,
            "video_id": vid,
            "url": row.get("url", ""),
            "ts": row.get("ts", ""),
        }
    return sorted(by_vid.values(), key=lambda r: (r["chapter"], r["video_id"]))


def main() -> int:
    load_dotenv()
    os.environ.setdefault("BILIBILI_CLEAR_PROXY", "1")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--platform",
        choices=("youtube", "bilibili", "both"),
        default="bilibili",
        help="删除目标平台（默认 bilibili）",
    )
    parser.add_argument(
        "--chapters",
        default="1-39",
        help="章号范围，如 1-39 或 6,7,8；留空表示登记册全部章",
    )
    parser.add_argument("--dry-run", action="store_true", help="仅列出待删条目")
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="确认执行删除（否则仅 dry-run）",
    )
    parser.add_argument(
        "--delay-sec",
        type=float,
        default=45.0,
        help="各条删除间隔秒数（默认 45，减轻 B 站限频）",
    )
    parser.add_argument(
        "--stop-on-captcha",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="遇 B 站验证码风控（340022）时立即停止（默认开启）",
    )
    args = parser.parse_args()

    chapter_filter = parse_chapters(args.chapters) if args.chapters else None
    reg = registry_path(ROOT)
    if not reg.is_file():
        print(f"登记册不存在: {reg}", file=sys.stderr)
        return 1

    do_delete = args.confirm and not args.dry_run
    if not args.dry_run and not args.confirm:
        print("未指定 --confirm，将以 dry-run 模式列出待删条目。", flush=True)

    deleted = 0
    failures: list[dict] = []

    if args.platform in ("youtube", "both"):
        from pipeline.youtube_upload import delete_video as delete_yt_video

        targets = collect_youtube_targets(chapter_filter=chapter_filter)
        print(f"YouTube 待删 {len(targets)} 个唯一 video_id（登记册 {reg.name}）")
        for i, row in enumerate(targets):
            label = f"ch{row['chapter']:02d} {row['video_id']}"
            if not do_delete:
                print(f"  [dry-run] {label}  {row.get('url', '')}")
                continue
            if i > 0 and args.delay_sec > 0:
                print(f"等待 {args.delay_sec:.0f}s…", flush=True)
                time.sleep(args.delay_sec)
            try:
                delete_yt_video(ROOT, row["video_id"])
                deleted += 1
            except Exception as exc:
                print(f"  失败 {label}: {exc!r}", file=sys.stderr)
                failures.append({"platform": "youtube", **row, "error": repr(exc)})

    if args.platform in ("bilibili", "both"):
        from pipeline.bilibili_upload import delete_video as delete_bili_video

        targets = collect_bilibili_targets(chapter_filter=chapter_filter)
        print(f"B 站待删 {len(targets)} 个唯一 bvid（登记册 {reg.name}）")
        for i, row in enumerate(targets):
            label = f"ch{row['chapter']:02d} {row['bvid']} aid={row['aid']}"
            if not do_delete:
                print(f"  [dry-run] {label}  {row.get('url', '')}")
                continue
            if i > 0 and args.delay_sec > 0:
                print(f"等待 {args.delay_sec:.0f}s…", flush=True)
                time.sleep(args.delay_sec)
            try:
                delete_bili_video(
                    ROOT,
                    aid=row["aid"] if row["aid"] > 0 else None,
                    bvid=row["bvid"] or None,
                )
                deleted += 1
            except BilibiliCaptchaRequiredError as exc:
                print(f"  失败 {label}: {exc!r}", file=sys.stderr)
                failures.append({"platform": "bilibili", **row, "error": repr(exc)})
                if args.stop_on_captcha:
                    print(
                        "\nB 站要求验证码：请在浏览器打开创作中心稿件列表，"
                        "手动删除一条或完成验证后重新导出 Cookie：\n"
                        "  python3 scripts/upload_bilibili.py --auth-only\n",
                        file=sys.stderr,
                    )
                    break
            except Exception as exc:
                print(f"  失败 {label}: {exc!r}", file=sys.stderr)
                failures.append({"platform": "bilibili", **row, "error": repr(exc)})

    print()
    print(f"删除完成: 成功 {deleted}，失败 {len(failures)}")
    if failures:
        print("失败列表:", flush=True)
        for f in failures:
            print(f"  {json.dumps(f, ensure_ascii=False)}", flush=True)

    if args.platform in ("bilibili", "both"):
        print()
        print("B 站重新上传 ch1–81（仅 B 站，定时发布示例）：")
        print(
            "  BILIBILI_CLEAR_PROXY=1 python3 scripts/upload_hybrid_batch.py "
            "--chapters 1-81 --bilibili-only "
            "--publish-start 2026-06-10T09:00:00+08:00 --delay-sec 120"
        )

    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
