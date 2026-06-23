#!/usr/bin/env python3
"""道德经单章精解 ch01–81：八十一讲播放列表 / B 站列表配置与同步。

1) 在平台建好列表后，把 ID 写入 assets/DaoDeJing/series_daodejing_81.json
   或环境变量 YOUTUBE_PLAYLIST_DAODEJING_81 / BILIBILI_SERIES_DAODEJING_81

2) 写入全部分镜：
   python3 scripts/setup_daodejing_81_series.py --patch-storyboards

3) 登记已上传稿件（每章一次）：
   python3 scripts/setup_daodejing_81_series.py --register 3 \\
     --youtube-id VIDEO_ID --bilibili-aid 123456789

4) 按章号顺序补进播放列表 / 视频列表：
   python3 scripts/setup_daodejing_81_series.py --sync --chapters 1-50

5) 列出账号下所有合集/列表（查 season_id / series_id）：
   python3 scripts/setup_daodejing_81_series.py --list-bilibili

6) 用本机 OAuth 自动创建播放列表 + B 站视频列表（需 credentials/）：
   python3 scripts/setup_daodejing_81_series.py --create-all

7) 已在 Studio 建好播放列表，只写入 PL… 并更新分镜：
   python3 scripts/setup_daodejing_81_series.py --set-youtube-playlist PLxxxxxxxx
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.env_util import load_dotenv  # noqa: E402
from pipeline.series_config import (  # noqa: E402
    REGISTRY_REL,
    SERIES_CONFIG_REL,
    Daodejing81Series,
    append_registry,
    chapter_from_path,
    commentary_storyboard_paths,
    config_path,
    load_daodejing_81_series,
    load_registry,
    patch_storyboard_json,
    registry_by_chapter,
    save_daodejing_81_series,
)
from pipeline.youtube_upload import add_video_to_playlist, create_youtube_playlist  # noqa: E402


def parse_chapters(spec: str) -> list[int]:
    spec = spec.strip()
    if "-" in spec:
        a, b = spec.split("-", 1)
        return list(range(int(a), int(b) + 1))
    return [int(x) for x in spec.split(",") if x.strip()]


def cmd_show_config() -> int:
    s = load_daodejing_81_series(ROOT)
    print(f"配置: {config_path(ROOT)}")
    print(f"  YouTube playlist_id: {s.youtube_playlist_id or '（未配置）'}")
    print(f"  B 站 series_id:      {s.bilibili_series_id or '（未配置）'}")
    print(f"  B 站 season_id:      {s.bilibili_season_id or '（未配置，新版合集需创作中心手动）'}")
    rows = load_registry(ROOT)
    print(f"  登记条数: {len(rows)} → {ROOT / REGISTRY_REL}")
    return 0


def cmd_patch_storyboards() -> int:
    series = load_daodejing_81_series(ROOT)
    if not series.youtube_configured and not series.bilibili_series_configured:
        print(
            "警告：youtube_playlist_id 与 bilibili_series_id 均未配置，"
            "只会写入 season_id（若有）。请先编辑：",
            config_path(ROOT),
            file=sys.stderr,
        )
    changed = 0
    for path in commentary_storyboard_paths(ROOT):
        data = json.loads(path.read_text(encoding="utf-8"))
        if patch_storyboard_json(data, series):
            path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            ch = chapter_from_path(path)
            print(f"  已更新 ch{ch:02d}: {path.name}")
            changed += 1
    print(f"\n共更新 {changed} 个分镜（共 {len(commentary_storyboard_paths(ROOT))} 个）。")
    return 0


def cmd_register(args: argparse.Namespace) -> int:
    ch = args.register
    if ch <= 0:
        raise SystemExit("--register 须为正整数章号")
    if args.youtube_id:
        append_registry(
            chapter=ch,
            platform="youtube",
            project_root=ROOT,
            video_id=args.youtube_id.strip(),
        )
        print(f"ch{ch:02d} YouTube → {args.youtube_id}")
    if args.bilibili_aid:
        append_registry(
            chapter=ch,
            platform="bilibili",
            project_root=ROOT,
            aid=int(args.bilibili_aid),
            bvid=(args.bilibili_bvid or "").strip(),
        )
        print(f"ch{ch:02d} B 站 aid → {args.bilibili_aid}")
    if not args.youtube_id and not args.bilibili_aid:
        raise SystemExit("请至少提供 --youtube-id 或 --bilibili-aid")
    return 0


def cmd_sync(args: argparse.Namespace) -> int:
    series = load_daodejing_81_series(ROOT)
    by_ch = registry_by_chapter(ROOT)
    chapters = parse_chapters(args.chapters)
    missing: list[int] = []

    if not args.bilibili_only:
        if not series.youtube_configured:
            print("跳过 YouTube：未配置 playlist_id", file=sys.stderr)
        else:
            for i, ch in enumerate(chapters):
                row = by_ch.get(ch, {}).get("youtube")
                if not row or not row.get("video_id"):
                    missing.append(ch)
                    continue
                vid = str(row["video_id"])
                pos = i if args.order_by_chapter else None
                ok = add_video_to_playlist(
                    ROOT,
                    series.youtube_playlist_id,
                    vid,
                    position=pos,
                    method=args.youtube_method,
                )
                if ok:
                    print(f"  ch{ch:02d} → playlist ({vid})")

    if not args.youtube_only:
        if not series.bilibili_series_configured:
            print(
                "跳过 B 站 API 归集：未配置 bilibili_series_id。"
                "空间页「合集·XXX」请在创作中心手动加入。",
                file=sys.stderr,
            )
        else:
            import asyncio

            from pipeline.bilibili_upload import add_videos_to_bilibili_series

            aids_batch: list[int] = []
            ch_batch: list[int] = []
            for ch in chapters:
                row = by_ch.get(ch, {}).get("bilibili")
                if not row or not row.get("aid"):
                    if ch not in missing:
                        missing.append(ch)
                    continue
                aids_batch.append(int(row["aid"]))
                ch_batch.append(ch)
            if aids_batch:
                asyncio.run(
                    add_videos_to_bilibili_series(
                        series.bilibili_series_id, aids_batch, ROOT
                    )
                )
                print(f"  B 站 batch: ch{ch_batch[0]:02d}–ch{ch_batch[-1]:02d} ({len(aids_batch)} P)")

    if missing:
        uniq = sorted(set(missing))
        print(f"\n未登记章号（需先 --register）: {uniq}", file=sys.stderr)
        return 1
    print("\n同步完成。")
    return 0


def cmd_set_youtube_playlist(args: argparse.Namespace) -> int:
    pid = (args.set_youtube_playlist or "").strip()
    if not pid.startswith("PL") and not pid.startswith("UU"):
        raise SystemExit("播放列表 ID 通常以 PL 开头（Studio → 播放列表 → 分享/URL 中的 list=）")
    series = load_daodejing_81_series(ROOT)
    series.youtube_playlist_id = pid
    save_daodejing_81_series(series, ROOT)
    print(f"已写入 youtube_playlist_id={pid}")
    if args.patch_after_create:
        return cmd_patch_storyboards()
    return 0


def cmd_create_all(args: argparse.Namespace) -> int:
    cfg_path = config_path(ROOT)
    raw = json.loads(cfg_path.read_text(encoding="utf-8")) if cfg_path.is_file() else {}
    title_yt = raw.get("title_youtube") or "观念黑盒 · 道德经八十一讲（单章精解）"
    title_bili = raw.get("title_zh") or "道德经八十一讲"
    desc = "观念黑盒 · 单章精解系列，按《道德经》章次连续观看。"

    series = load_daodejing_81_series(ROOT)

    do_yt = args.create_all or args.create_youtube
    do_bili = args.create_all or args.create_bilibili

    if do_yt:
        if series.youtube_configured and not args.force:
            print(f"YouTube 已有 playlist_id={series.youtube_playlist_id}，跳过（--force 重建）")
        else:
            try:
                pl = create_youtube_playlist(
                    ROOT,
                    title_yt,
                    description=desc,
                    method=args.youtube_method,
                )
                series.youtube_playlist_id = pl["id"]
            except Exception as exc:
                print(
                    f"YouTube API 失败: {exc}\n"
                    "若已在 Studio 建好列表，请用：\n"
                    "  python3 scripts/setup_daodejing_81_series.py --set-youtube-playlist PLxxxxxxxx\n"
                    "或先在本机终端（开代理）执行：python3 scripts/upload_youtube.py --auth-only",
                    file=sys.stderr,
                )
                raise

    if do_bili:
        if series.bilibili_series_configured and not args.force:
            print(f"B 站已有 series_id={series.bilibili_series_id}，跳过（--force 重建）")
        else:
            import asyncio

            from pipeline.bilibili_upload import create_bilibili_video_series

            out = asyncio.run(
                create_bilibili_video_series(
                    ROOT,
                    title_bili,
                    description=desc,
                    keywords=["道德经", "老子", "观念黑盒", "八十一讲"],
                )
            )
            series.bilibili_series_id = int(out["series_id"])

    save_daodejing_81_series(series, ROOT)
    print(f"\n已写入 {cfg_path}")
    if args.patch_after_create:
        return cmd_patch_storyboards()
    return 0


def cmd_list_bilibili() -> int:
    try:
        import asyncio

        from bilibili_api import sync
        from bilibili_api.channel_series import ChannelSeriesType
        from bilibili_api.user import User, get_self_info

        from pipeline.bilibili_upload import load_credential
    except ImportError as exc:
        raise SystemExit("需要: pip install bilibili-api-python") from exc

    cred = load_credential(ROOT)

    async def _run():
        info = await get_self_info(cred)
        user = User(info["mid"], credential=cred)
        channels = await user.get_channels()
        rows = []
        for ch in channels:
            meta = ch.meta or await ch.get_meta()
            rows.append((ch, meta))
        return info, rows

    info, channel_rows = sync(_run())
    print(f"账号: {info['name']} (uid {info['mid']})\n")
    for ch, meta in channel_rows:
        name = meta.get("name") or meta.get("title") or "?"
        if ch.get_type() == ChannelSeriesType.SEASON:
            sid = meta.get("season_id") or ch.get_id()
            print(f"  [合集·SEASON] season_id={sid}  {name}")
        else:
            sid = meta.get("series_id") or ch.get_id()
            print(f"  [视频列表·SERIES] series_id={sid}  {name}")
    print(
        f"\n将 series_id 写入 {SERIES_CONFIG_REL} 的 bilibili_series_id，"
        "然后 --patch-storyboards 与 --sync。"
    )
    return 0


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--show-config", action="store_true", help="显示当前系列 ID 与登记")
    parser.add_argument(
        "--patch-storyboards",
        action="store_true",
        help="把系列 ID 写入 examples/storyboard-daodejing-ch*-commentary.json",
    )
    parser.add_argument("--register", type=int, metavar="CH", help="登记第 N 章已上传 ID")
    parser.add_argument("--youtube-id", default="", help="YouTube video id")
    parser.add_argument("--bilibili-aid", type=int, default=0, help="B 站 aid（整数）")
    parser.add_argument("--bilibili-bvid", default="", help="可选 BV 号")
    parser.add_argument("--sync", action="store_true", help="按登记批量加入列表")
    parser.add_argument("--chapters", default="1-50", help="同步范围，默认 1-50")
    parser.add_argument(
        "--order-by-chapter",
        action="store_true",
        help="YouTube 按章号设置 playlist position（已存在的条目可能需 Studio 内微调）",
    )
    parser.add_argument("--youtube-only", action="store_true")
    parser.add_argument("--bilibili-only", action="store_true")
    parser.add_argument(
        "--youtube-method",
        choices=("requests", "googleapiclient"),
        default="requests",
    )
    parser.add_argument(
        "--list-bilibili",
        action="store_true",
        help="列出账号下 SEASON/SERIES（查 ID）",
    )
    parser.add_argument(
        "--create-all",
        action="store_true",
        help="API 创建 YouTube 播放列表 + B 站视频列表并写入配置文件",
    )
    parser.add_argument("--create-youtube", action="store_true")
    parser.add_argument("--create-bilibili", action="store_true")
    parser.add_argument(
        "--force",
        action="store_true",
        help="即使配置里已有 ID 也重新创建",
    )
    parser.add_argument(
        "--patch-after-create",
        action="store_true",
        default=True,
        help="创建后自动 --patch-storyboards（默认开启）",
    )
    parser.add_argument(
        "--no-patch-after-create",
        action="store_false",
        dest="patch_after_create",
        help="创建后不修改分镜 JSON",
    )
    parser.add_argument(
        "--set-youtube-playlist",
        metavar="PL…",
        help="跳过 API，直接写入已建好的播放列表 ID",
    )
    args = parser.parse_args()

    if args.set_youtube_playlist:
        return cmd_set_youtube_playlist(args)
    if args.show_config:
        return cmd_show_config()
    if args.patch_storyboards:
        return cmd_patch_storyboards()
    if args.register:
        return cmd_register(args)
    if args.sync:
        return cmd_sync(args)
    if args.list_bilibili:
        return cmd_list_bilibili()
    if args.create_all or args.create_youtube or args.create_bilibili:
        return cmd_create_all(args)

    parser.print_help()
    print("\n常用：--show-config → 填 series_daodejing_81.json → --patch-storyboards")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
