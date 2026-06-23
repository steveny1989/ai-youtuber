#!/usr/bin/env python3
"""抖音创作者平台自动上传脚本。

使用流程（两步走）：

  第一步：登录保存 Cookie（只需做一次，Cookie 约 30 天有效）
    python3 scripts/upload_douyin.py --auth-only

  第二步：上传视频
    python3 scripts/upload_douyin.py examples/storyboard-zhuangzi-dazongshi.json
    python3 scripts/upload_douyin.py examples/storyboard-zhuangzi-dazongshi.json --upload
    python3 scripts/upload_douyin.py examples/storyboard-zhuangzi-dazongshi.json --upload --video output/dazongshi/zhuangzi-dazongshi-30min.mp4

  其他选项：
    --dry-run          打印元数据，不实际上传
    --check-cookie     检查 Cookie 是否仍有效
    --publish-at '2026-06-25 20:00'   定时发布
    --cover path/to/cover.jpg          指定封面图
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("PYTHONUNBUFFERED", "1")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _check_playwright() -> None:
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except ImportError as exc:
        raise SystemExit(
            "缺少 playwright，请运行：\n"
            "  pip3 install playwright\n"
            "  python3 -m playwright install chromium\n"
            "（如已安装系统 Chrome，可跳过第二步）"
        ) from exc


from pipeline.env_util import load_dotenv  # noqa: E402
from pipeline.models import Storyboard  # noqa: E402


def _resolve_video(args, storyboard: Storyboard, project_root: Path) -> Path:
    """按优先级解析视频路径：--video 参数 > storyboard.output.filename。"""
    if args.video:
        p = Path(args.video)
        p = p if p.is_absolute() else project_root / p
        if not p.is_file():
            raise FileNotFoundError(f"视频不存在: {p}")
        return p.resolve()

    filename = storyboard.output.filename
    if not filename:
        raise ValueError("storyboard.output.filename 未设置，请用 --video 指定视频路径")

    # 常见输出目录：output/<stem>/<filename> 或 output/<filename>
    stem = Path(filename).stem
    candidates = [
        project_root / "output" / stem / filename,
        project_root / "output" / filename,
        project_root / filename,
    ]
    for p in candidates:
        if p.is_file():
            return p.resolve()

    checked = "\n  ".join(str(c) for c in candidates)
    raise FileNotFoundError(
        f"未找到视频文件，尝试了：\n  {checked}\n请用 --video 明确指定路径。"
    )


def _resolve_cover(args, storyboard: Storyboard, project_root: Path) -> Path | None:
    """解析封面图路径：--cover 参数 > storyboard 中配置的封面。"""
    if args.cover:
        p = Path(args.cover)
        p = p if p.is_absolute() else project_root / p
        if p.is_file():
            return p.resolve()
        print(f"⚠️  指定封面不存在: {p}，跳过封面上传", flush=True)
        return None

    # 从 storyboard 解析封面（与 bilibili/youtube 上传逻辑一致）
    try:
        from pipeline.bilibili_upload import resolve_upload_cover
        return resolve_upload_cover(storyboard, project_root, storyboard.bilibili)
    except Exception:
        return None


def main() -> int:
    load_dotenv()

    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "storyboard",
        nargs="?",
        type=Path,
        default=ROOT / "examples/storyboard-zhuangzi-dazongshi.json",
        help="分镜 JSON 文件路径（默认: examples/storyboard-zhuangzi-dazongshi.json）",
    )
    parser.add_argument(
        "--video",
        type=Path,
        default=None,
        metavar="PATH",
        help="视频文件路径（覆盖 storyboard.output.filename 自动推断）",
    )
    parser.add_argument(
        "--cover",
        type=Path,
        default=None,
        metavar="PATH",
        help="封面图片路径（JPG/PNG）",
    )
    parser.add_argument(
        "--auth-only",
        action="store_true",
        help="打开浏览器让用户手动登录，保存 Cookie 后退出",
    )
    parser.add_argument(
        "--upload",
        action="store_true",
        help="执行上传（不加此参数默认为 --dry-run）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只打印元数据，不实际上传",
    )
    parser.add_argument(
        "--check-cookie",
        action="store_true",
        help="检查已保存的 Cookie 是否仍有效",
    )
    parser.add_argument(
        "--publish-at",
        default=None,
        metavar="'YYYY-MM-DD HH:MM'",
        help="定时发布时间，如 '2026-06-25 20:00'",
    )
    args = parser.parse_args()

    _check_playwright()

    from pipeline.douyin_upload import (
        auth_and_save_cookie,
        cookie_path,
        upload_video,
        verify_cookie,
    )

    storyboard_path = args.storyboard.resolve()
    if not storyboard_path.is_file():
        raise SystemExit(f"分镜文件不存在: {storyboard_path}")

    storyboard = Storyboard.load(storyboard_path)
    project_root = storyboard_path.parent.parent

    # ── --auth-only ──────────────────────────────────────────────────────────
    if args.auth_only:
        existing = cookie_path(project_root)
        if existing.is_file():
            print(f"提示：已有 Cookie 文件 {existing}")
            print("  验证: python3 scripts/upload_douyin.py --check-cookie")
            print("  继续登录将覆盖旧 Cookie…\n")
        auth_and_save_cookie(project_root)
        return 0

    # ── --check-cookie ───────────────────────────────────────────────────────
    if args.check_cookie:
        path = cookie_path(project_root)
        if not path.is_file():
            raise SystemExit(
                f"未找到 Cookie: {path}\n请先运行: python3 scripts/upload_douyin.py --auth-only"
            )
        print("检查 Cookie 有效性（会短暂打开无头浏览器）…")
        ok = verify_cookie(project_root)
        if ok:
            print("✓ Cookie 有效，可以上传")
        else:
            print("✗ Cookie 已失效，请重新登录：python3 scripts/upload_douyin.py --auth-only")
        return 0 if ok else 1

    # ── 解析视频 & 封面 ──────────────────────────────────────────────────────
    video = _resolve_video(args, storyboard, project_root)
    cover = _resolve_cover(args, storyboard, project_root)

    # 没有 --upload 时默认 dry-run，保护用户不误上传
    is_dry_run = args.dry_run or (not args.upload)

    if is_dry_run and not args.dry_run:
        print("提示：未传 --upload，以 dry-run 模式运行（只预览元数据）")
        print("      加 --upload 参数才会真实上传\n")

    # ── 上传 ─────────────────────────────────────────────────────────────────
    result = upload_video(
        video,
        storyboard,
        project_root=project_root,
        cover_path=cover,
        publish_at=args.publish_at,
        dry_run=is_dry_run,
    )

    if not is_dry_run:
        print("\n── 上传结果 ──────────────────────────────────────────")
        print(json.dumps(result, ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
