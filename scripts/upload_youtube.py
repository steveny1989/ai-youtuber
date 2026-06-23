#!/usr/bin/env python3
"""将 output 成片上传到 YouTube（OAuth + 分镜元数据）。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

def _check_youtube_deps() -> None:
    try:
        import google_auth_oauthlib  # noqa: F401
        import googleapiclient  # noqa: F401
    except ImportError as exc:
        raise SystemExit(
            "缺少 YouTube 上传依赖，请运行：\n"
            "  pip install google-api-python-client google-auth-oauthlib google-auth-httplib2\n"
            "或：pip install -r requirements.txt"
        ) from exc


_check_youtube_deps()

from pipeline.env_util import load_dotenv  # noqa: E402
from pipeline.models import Storyboard  # noqa: E402
from pipeline.series_config import (  # noqa: E402
    append_registry,
    chapter_from_path,
    registry_by_chapter,
    resolve_youtube_playlist_id,
)
from pipeline.youtube_upload import (  # noqa: E402
    build_upload_body,
    export_metadata_package,
    format_youtube_publish_at,
    load_youtube_credentials,
    parse_publish_datetime,
    prepare_youtube_thumbnail,
    preview_metadata,
    resolve_audio_dir,
    resolve_output_video,
    resolve_thumbnail_path,
    upload_thumbnail,
    upload_video,
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
    parser.add_argument(
        "--video",
        type=Path,
        default=None,
        help="默认 output/<storyboard.output.filename>",
    )
    parser.add_argument(
        "--privacy",
        choices=("private", "unlisted", "public"),
        default=None,
        help="覆盖 JSON 中的 privacy_status",
    )
    parser.add_argument(
        "--auth-only",
        action="store_true",
        help="仅完成 OAuth 授权，不上传",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只打印标题/简介/标签，不上传",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=600,
        help="HTTP 超时秒数（默认 600）",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=8,
        help="网络失败时的最大重试次数（默认 8）",
    )
    parser.add_argument(
        "--method",
        choices=("requests", "googleapiclient"),
        default="requests",
        help="上传实现（默认 requests，更稳且支持 HTTPS_PROXY）",
    )
    parser.add_argument(
        "--export-metadata",
        action="store_true",
        help="只导出 Studio 手动上传包到 output/youtube-upload/，不传视频",
    )
    parser.add_argument(
        "--audio-dir",
        type=Path,
        default=None,
        help="各镜 mp3 目录（默认 output/audio，用于章节时间戳）",
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
        help="定时公开（ISO8601，如 2026-05-30T08:00:00+08:00）；YouTube 会先 private 再自动公开",
    )
    parser.add_argument(
        "--playlist-id",
        default=None,
        help="覆盖分镜/系列配置，上传后加入该播放列表（PL…）",
    )
    parser.add_argument(
        "--no-thumbnail",
        action="store_true",
        help="不上传自定义缩略图（默认视频传完后自动上传封面图）",
    )
    parser.add_argument(
        "--thumbnail-only",
        action="store_true",
        help="仅补传缩略图（需 registry 或 --video-id 指定已上传视频）",
    )
    parser.add_argument(
        "--video-id",
        default=None,
        help="YouTube video ID（与 --thumbnail-only 联用）",
    )
    args = parser.parse_args()

    storyboard_path = args.storyboard.resolve()
    storyboard = Storyboard.load(storyboard_path)
    project_root = storyboard_path.parent.parent

    if args.privacy:
        storyboard.youtube.privacy_status = args.privacy

    if args.auth_only:
        load_youtube_credentials(project_root)
        print("YouTube OAuth 授权成功，token 已保存到 credentials/youtube_token.json")
        return 0

    if args.thumbnail_only:
        video_id = (args.video_id or "").strip()
        if not video_id:
            ch = chapter_from_path(args.storyboard)
            if ch is not None:
                row = registry_by_chapter(project_root).get(ch, {}).get("youtube") or {}
                video_id = str(row.get("video_id", "")).strip()
        if not video_id:
            raise SystemExit(
                "请指定 --video-id，或确保 registry 中已有该章 YouTube video_id"
            )
        thumb_src = resolve_thumbnail_path(storyboard, project_root)
        if thumb_src is None:
            raise SystemExit("未找到封面图，无法补传缩略图")
        thumbnail_file = prepare_youtube_thumbnail(thumb_src, project_root)
        print(f"补传缩略图 → {video_id}")
        print(f"  源图: {thumb_src}")
        print(f"  压缩: {thumbnail_file} ({thumbnail_file.stat().st_size // 1024} KB)")
        upload_thumbnail(
            video_id,
            thumbnail_file,
            project_root=project_root,
            method=args.method,
            timeout_sec=args.timeout,
            max_retries=args.retries,
        )
        print("缩略图完成 ✓")
        return 0

    if args.video:
        video = args.video.resolve()
        if not video.is_file():
            raise FileNotFoundError(f"视频不存在: {video}")
    else:
        video = resolve_output_video(project_root, storyboard.output.filename)

    audio_dir = resolve_audio_dir(project_root, args.audio_dir)
    time_offset_sec = _resolve_time_offset_sec(args, project_root)
    yt_publish_at = None
    if args.publish_at:
        yt_publish_at = format_youtube_publish_at(parse_publish_datetime(args.publish_at))

    meta = preview_metadata(
        storyboard,
        project_root=project_root,
        video_path=video,
        audio_dir=audio_dir,
        time_offset_sec=time_offset_sec,
        publish_at=yt_publish_at,
    )

    if args.export_metadata:
        out = export_metadata_package(
            storyboard, project_root=project_root, video_path=video
        )
        print(f"已导出手动上传包: {out}")
        print(f"  视频: {video}")
        print(f"  复制元数据: {out / 'studio-paste.txt'}")
        print(f"  说明: {out / 'README.txt'}")
        return 0

    if args.dry_run:
        print(json.dumps(meta, ensure_ascii=False, indent=2))
        return 0

    print("即将上传：")
    print(f"  视频: {video}")
    print(f"  标题: {meta['title']}")
    print(f"  可见: {meta['privacy']}")
    if yt_publish_at:
        print(f"  定时公开: {args.publish_at} → {yt_publish_at}")
    print(f"  标签: {', '.join(meta['tags'][:8])}…")
    thumbnail_file: Path | None = None
    if not args.no_thumbnail:
        thumb_src = resolve_thumbnail_path(storyboard, project_root)
        if thumb_src is not None:
            thumbnail_file = prepare_youtube_thumbnail(thumb_src, project_root)
            kb = thumbnail_file.stat().st_size / 1024
            print(f"  缩略图: {thumb_src.name} → {thumbnail_file.name} ({kb:.0f} KB)")
        else:
            print("  缩略图: （未找到封面图，将使用 YouTube 自动帧）")
    print()

    body = build_upload_body(
        storyboard,
        audio_dir=audio_dir,
        config=storyboard.youtube,
        time_offset_sec=time_offset_sec,
        publish_at=yt_publish_at,
    )
    playlist_id = (args.playlist_id or "").strip()
    if not playlist_id:
        playlist_id = resolve_youtube_playlist_id(
            storyboard.youtube.playlist_id, project_root
        )
    if playlist_id:
        print(f"  播放列表: {playlist_id}", flush=True)
    result = upload_video(
        video,
        body,
        project_root=project_root,
        playlist_id=playlist_id,
        thumbnail_path=thumbnail_file,
        timeout_sec=args.timeout,
        max_retries=args.retries,
        method=args.method,
    )
    print(f"\n上传完成: {result['url']}")
    ch = chapter_from_path(args.storyboard)
    if ch is not None:
        append_registry(
            chapter=ch,
            platform="youtube",
            project_root=project_root,
            video_id=result["id"],
            url=result["url"],
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
