#!/usr/bin/env python3
"""为 ch01–39 讲解分镜写入 pan 推轨 + ambient 氛围层（保留 narration / 配图 / 元数据）。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from pipeline.motion import default_motion_for_scene  # noqa: E402

AMBIENT = {
    "enabled": True,
    "dust_opacity": 0.15,
    "ink_opacity": 0.07,
    "water_opacity": 0.09,
}


def fix_chapter(ch: int, *, write: bool = True) -> bool:
    path = ROOT / f"examples/storyboard-daodejing-ch{ch:02d}-commentary.json"
    if not path.is_file():
        print(f"skip ch{ch:02d}: no storyboard")
        return False

    data = json.loads(path.read_text(encoding="utf-8"))
    for scene in data.get("scenes", []):
        scene["motion"] = default_motion_for_scene(scene["id"])

    data.setdefault("style", {})["motion"] = "auto"
    data["ambient"] = dict(AMBIENT)

    if write:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"updated ch{ch:02d}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chapters", default="1-39", help="如 1-39 或 5,10,20")
    parser.add_argument("--dry-run", action="store_true", help="只统计，不写文件")
    args = parser.parse_args()

    spec = args.chapters.strip()
    if "-" in spec:
        a, b = spec.split("-", 1)
        chapters = list(range(int(a), int(b) + 1))
    else:
        chapters = [int(x) for x in spec.split(",") if x.strip()]

    n = sum(1 for ch in chapters if fix_chapter(ch, write=not args.dry_run))
    print(f"\n{'would update' if args.dry_run else 'updated'} {n} chapter(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
