#!/usr/bin/env python3
"""合并各期图鉴与磁盘扫描，生成 assets/DaoDeJing/image_catalog.json。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.episode_assets import (  # noqa: E402
    build_master_image_catalog,
    collect_used_images,
    filter_unused_images,
    load_catalog_images,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--episode",
        type=int,
        default=0,
        help="若指定，打印该期可用未用图数量（排除往期已用）",
    )
    args = parser.parse_args()

    out = build_master_image_catalog(ROOT)
    meta = __import__("json").loads(out.read_text(encoding="utf-8"))["meta"]
    print(f"已写入 {out.relative_to(ROOT)}（{meta['image_count']} 张，磁盘补录 {meta['on_disk_only']} 张）")

    if args.episode >= 1:
        used = collect_used_images(ROOT, args.episode)
        all_images = load_catalog_images(out, ROOT)
        pool = filter_unused_images(all_images, used, ROOT)
        print(f"EP{args.episode:02d} 可用池：{len(pool)}/{len(all_images)}（已排除往期 {len(used)} 张）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
