from __future__ import annotations

import argparse
from pathlib import Path

from .render import render_storyboard


def main() -> None:
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
        help="中间文件目录（默认项目根目录 .work）",
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
        help="跳过 TTS，使用 .work/audio 里已有 mp3",
    )
    args = parser.parse_args()

    final = render_storyboard(
        args.storyboard,
        work_dir=args.work_dir,
        output_dir=args.output_dir,
        skip_tts=args.skip_tts,
    )
    print(f"渲染完成: {final}")


if __name__ == "__main__":
    main()
