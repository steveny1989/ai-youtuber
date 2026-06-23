#!/usr/bin/env python3
"""B 站投稿：导出元数据或 bilibili-api 上传（国内网络通常比 YouTube API 稳）。"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# 终端实时输出进度
os.environ.setdefault("PYTHONUNBUFFERED", "1")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _check_bilibili_api() -> None:
    try:
        import bilibili_api  # noqa: F401
    except ImportError as exc:
        raise SystemExit(
            "缺少 B 站上传依赖，请运行：\n"
            "  pip install bilibili-api-python\n"
            "仅导出元数据不需要此包，但 --auth-only / 上传 需要。"
        ) from exc


from pipeline.env_util import load_dotenv  # noqa: E402
from pipeline.models import Storyboard  # noqa: E402
from pipeline.series_config import append_registry, chapter_from_path  # noqa: E402
from pipeline.bilibili_upload import (  # noqa: E402
    build_metadata,
    export_metadata_package,
)
from pipeline.youtube_upload import (  # noqa: E402
    parse_publish_datetime,
    publish_at_unix,
    resolve_audio_dir,
    resolve_output_video,
)
from pipeline.ffmpeg_util import probe_duration_sec  # noqa: E402


def _resolve_time_offset_sec(args, project_root: Path) -> float:
    if args.time_offset_sec is not None:
        return max(0.0, args.time_offset_sec)
    if args.read_video:
        p = args.read_video if args.read_video.is_absolute() else project_root / args.read_video
        return probe_duration_sec(p.resolve())
    return 0.0


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "storyboard",
        nargs="?",
        type=Path,
        default=ROOT / "examples/storyboard-daodejing-ep01-22beats.json",
    )
    parser.add_argument("--video", type=Path, default=None)
    parser.add_argument(
        "--export-metadata",
        action="store_true",
        help="导出创作中心手动投稿包（默认行为，可不传视频 API）",
    )
    parser.add_argument(
        "--auth-only",
        action="store_true",
        help="B 站 App 扫码登录，保存 credentials/bilibili_credential.json",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="打印元数据 JSON",
    )
    parser.add_argument(
        "--upload",
        action="store_true",
        help="调用 bilibili-api 上传（需有效凭据）",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="上传前额外验证凭据（较慢；默认跳过，建议用 --check-credential）",
    )
    parser.add_argument(
        "--check-credential",
        action="store_true",
        help="检查 credentials/bilibili_credential.json 是否仍有效",
    )
    parser.add_argument(
        "--import-cookies",
        action="store_true",
        help="从浏览器 Cookie 导入凭据（见 credentials/README-bilibili.md）",
    )
    parser.add_argument(
        "--audio-dir",
        type=Path,
        default=None,
        help="各镜 mp3 目录（默认 output/audio，用于简介时间轴）",
    )
    parser.add_argument(
        "--read-video",
        type=Path,
        default=None,
        help="hybrid 成片前的朗读段 mp4，用于简介时间戳偏移",
    )
    parser.add_argument(
        "--time-offset-sec",
        type=float,
        default=None,
        help="简介章节时间戳整体偏移秒数（覆盖 --read-video）",
    )
    parser.add_argument(
        "--publish-at",
        dest="publish_at",
        default=None,
        help="定时发布（ISO8601，如 2026-05-30T08:00:00+08:00）",
    )
    args = parser.parse_args()

    storyboard_path = args.storyboard.resolve()
    storyboard = Storyboard.load(storyboard_path)
    project_root = storyboard_path.parent.parent

    if args.video:
        video = args.video.resolve()
        if not video.is_file():
            raise FileNotFoundError(f"视频不存在: {video}")
    else:
        video = resolve_output_video(project_root, storyboard.output.filename)

    audio_dir = resolve_audio_dir(project_root, args.audio_dir)
    time_offset_sec = _resolve_time_offset_sec(args, project_root)
    bili_publish_unix = None
    if args.publish_at:
        bili_publish_unix = publish_at_unix(parse_publish_datetime(args.publish_at))

    meta = build_metadata(
        storyboard,
        project_root=project_root,
        video_path=video,
        audio_dir=audio_dir,
        time_offset_sec=time_offset_sec,
    )

    if args.dry_run:
        print(json.dumps(meta, ensure_ascii=False, indent=2))
        return 0

    if args.import_cookies:
        _check_bilibili_api()
        print(
            "从浏览器登录 bilibili.com → 开发者工具 → Application → Cookies，复制：\n"
            "  SESSDATA、bili_jct、buvid3、DedeUserID\n"
        )
        sess = input("SESSDATA: ").strip()
        jct = input("bili_jct: ").strip()
        buvid3 = input("buvid3 (可回车跳过): ").strip()
        uid = input("DedeUserID (可回车跳过): ").strip()
        from pipeline.bilibili_upload import import_credential_from_cookies

        import_credential_from_cookies(
            project_root,
            sessdata=sess,
            bili_jct=jct,
            buvid3=buvid3,
            dedeuserid=uid,
        )
        return 0

    if args.check_credential:
        _check_bilibili_api()
        from pipeline.bilibili_upload import credential_path, verify_credential

        if not credential_path(project_root).is_file():
            raise SystemExit(f"未找到凭据: {credential_path(project_root)}")
        who = verify_credential(project_root)
        print(f"凭据有效: {who['name']} (uid {who['uid']})")
        return 0

    if args.auth_only:
        _check_bilibili_api()
        from bilibili_api import sync
        from pipeline.bilibili_upload import auth_with_qrcode, credential_path

        if credential_path(project_root).is_file():
            print(
                f"提示: 已有凭据 {credential_path(project_root)}。\n"
                "  上传用: python3 scripts/upload_bilibili.py --upload\n"
                "  检查凭据: --check-credential\n"
                "  浏览器 Cookie 导入（比扫码稳）: --import-cookies"
            )
        sync(auth_with_qrcode(project_root))
        return 0

    if args.upload:
        _check_bilibili_api()
        from pipeline.bilibili_upload import credential_path, upload_video

        if not credential_path(project_root).is_file():
            raise SystemExit(
                "未找到 B 站凭据。请先单独运行（两行分开执行）：\n"
                "  python3 scripts/upload_bilibili.py --auth-only\n"
                "  python3 scripts/upload_bilibili.py --upload"
            )

        print("即将上传 B 站：")
        print(f"  视频: {video}")
        print(f"  标题: {meta['title']}")
        print(f"  分区: {meta['tid']} {meta['tid_name']}")
        if bili_publish_unix:
            print(f"  定时发布: {args.publish_at}")
        print()
        result = upload_video(
            video,
            storyboard,
            project_root=project_root,
            skip_credential_check=not args.verify,
            audio_dir=audio_dir,
            time_offset_sec=time_offset_sec,
            publish_at_unix=bili_publish_unix,
        )
        print(f"\n投稿完成: {result.get('url') or result}")
        ch = chapter_from_path(args.storyboard)
        if ch is not None and result.get("aid"):
            append_registry(
                chapter=ch,
                platform="bilibili",
                project_root=project_root,
                aid=int(result["aid"]),
                bvid=result.get("bvid", ""),
                url=result.get("url", ""),
            )
        return 0

    # 默认：导出手动投稿包（不依赖 bilibili-api）
    out = export_metadata_package(
        storyboard, project_root=project_root, video_path=video
    )
    print(f"已导出 B 站投稿包: {out}")
    print(f"  视频: {video}")
    print(f"  元数据: {out / 'studio-paste.txt'}")
    print(f"  说明: {out / 'README.txt'}")
    print()
    print("自动上传: pip install bilibili-api-python")
    print("  python3 scripts/upload_bilibili.py --check-credential")
    print("  python3 scripts/upload_bilibili.py --upload")
    print("凭据: --import-cookies（推荐）或 --auth-only（扫码，勿设 BILIBILI_HTTP_CLIENT=httpx）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
