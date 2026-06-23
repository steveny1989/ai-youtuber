from __future__ import annotations

import argparse
from pathlib import Path

from .env_util import load_dotenv
from .render import render_storyboard


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(
        description="从 storyboard JSON 模板渲染 YouTube 视频"
    )
    parser.add_argument(
        "storyboard",
        type=Path,
        help="分镜 JSON 路径，例如 examples/storyboard.example.json",
    )
    parser.add_argument(
        "--work-dir",
        type=Path,
        default=None,
        help="中间文件目录（默认与 output 相同，即 output/audio、output/segments）",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="成片输出目录（默认 output/）",
    )
    parser.add_argument(
        "--skip-tts",
        action="store_true",
        help="跳过 TTS，使用 output/audio 里已有 mp3",
    )
    parser.add_argument(
        "--allow-missing-images",
        action="store_true",
        help="允许缺失配图（黑底+字幕，不推荐；默认无图则中止）",
    )
    args = parser.parse_args()

    final = render_storyboard(
        args.storyboard,
        work_dir=args.work_dir,
        output_dir=args.output_dir,
        skip_tts=args.skip_tts,
        allow_missing_images=args.allow_missing_images,
    )
    print(f"渲染完成: {final}")


if __name__ == "__main__":
    main()
