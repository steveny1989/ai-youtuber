#!/usr/bin/env python3
"""将登记册内 B 站稿件设为「仅自己可见」（不删除，便于之后重传新版本）。

示例：
  BILIBILI_CLEAR_PROXY=1 python3 scripts/set_bilibili_self_only.py --chapters 1-39 --dry-run
  BILIBILI_CLEAR_PROXY=1 python3 scripts/set_bilibili_self_only.py --chapters 1-39 --confirm --delay-sec 45
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

from pipeline.bilibili_upload import (  # noqa: E402
    BilibiliCaptchaRequiredError,
    set_archive_self_only,
)
from pipeline.env_util import load_dotenv  # noqa: E402
from pipeline.series_config import registry_path  # noqa: E402
from scripts.delete_uploaded_videos import (  # noqa: E402
    collect_bilibili_targets,
    parse_chapters,
)


def main() -> int:
    load_dotenv()
    os.environ.setdefault("BILIBILI_CLEAR_PROXY", "1")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chapters", default="1-39", help="章号范围，如 1-39")
    parser.add_argument("--dry-run", action="store_true", help="仅列出待处理条目")
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="确认执行（否则仅 dry-run）",
    )
    parser.add_argument(
        "--delay-sec",
        type=float,
        default=45.0,
        help="各条间隔秒数（默认 45）",
    )
    parser.add_argument(
        "--public",
        action="store_true",
        help="改回公开（is_only_self=0），默认设为仅自己可见",
    )
    parser.add_argument(
        "--stop-on-captcha",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="遇验证码风控时立即停止（默认开启）",
    )
    args = parser.parse_args()

    reg = registry_path(ROOT)
    if not reg.is_file():
        print(f"登记册不存在: {reg}", file=sys.stderr)
        return 1

    chapter_filter = parse_chapters(args.chapters) if args.chapters else None
    targets = collect_bilibili_targets(chapter_filter=chapter_filter)
    is_only_self = 0 if args.public else 1
    vis = "公开" if args.public else "仅自己可见"

    do_apply = args.confirm and not args.dry_run
    if not args.dry_run and not args.confirm:
        print("未指定 --confirm，将以 dry-run 模式列出待处理条目。", flush=True)

    print(
        f"B 站待设为{vis}：{len(targets)} 个唯一 bvid（登记册 {reg.name}）",
        flush=True,
    )

    ok = 0
    skipped = 0
    failures: list[dict] = []

    for i, row in enumerate(targets):
        label = f"ch{row['chapter']:02d} {row['bvid']} aid={row['aid']}"
        if not do_apply:
            print(f"  [dry-run] {label}  {row.get('url', '')}")
            continue
        if i > 0 and args.delay_sec > 0:
            print(f"等待 {args.delay_sec:.0f}s…", flush=True)
            time.sleep(args.delay_sec)
        try:
            set_archive_self_only(
                ROOT,
                aid=row["aid"] if row["aid"] > 0 else None,
                bvid=row["bvid"] or None,
                is_only_self=is_only_self,
            )
            ok += 1
        except BilibiliCaptchaRequiredError as exc:
            print(f"  失败 {label}: {exc!r}", file=sys.stderr)
            failures.append({"platform": "bilibili", **row, "error": repr(exc)})
            if args.stop_on_captcha:
                print(
                    "\nB 站要求验证码：请在浏览器打开创作中心完成验证后重新导出 Cookie：\n"
                    "  python3 scripts/upload_bilibili.py --auth-only\n",
                    file=sys.stderr,
                )
                break
        except Exception as exc:
            err = repr(exc)
            if "已是" in err or "跳过" in err:
                skipped += 1
                ok += 1
                continue
            print(f"  失败 {label}: {exc!r}", file=sys.stderr)
            failures.append({"platform": "bilibili", **row, "error": err})

    print()
    print(f"完成: 成功 {ok}（含跳过 {skipped}），失败 {len(failures)}")
    if failures:
        print("失败列表:", flush=True)
        for f in failures:
            print(f"  {json.dumps(f, ensure_ascii=False)}", flush=True)

    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
