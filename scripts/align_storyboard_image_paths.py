#!/usr/bin/env python3
"""将 storyboard scenes[].image 对齐为磁盘上实际存在的 assets/DaoDeJing 路径。

用法:
  python3 scripts/align_storyboard_image_paths.py --chapters 62-70
  python3 scripts/align_storyboard_image_paths.py --chapters 1-81 --dry-run
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.image_resolve import (  # noqa: E402
    align_image_path,
    clear_index_cache,
    get_index,
)


def parse_chapters(spec: str) -> list[int]:
    out: list[int] = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            out.extend(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return sorted(set(out))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chapters", default="1-81")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    chapters = parse_chapters(args.chapters)
    clear_index_cache()
    idx = get_index(ROOT)

    total = changed = missing = 0
    missing_detail: list[str] = []

    for ch in chapters:
        path = ROOT / f"examples/storyboard-daodejing-ch{ch:02d}-commentary.json"
        if not path.is_file():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        ch_changed = 0
        for s in data.get("scenes", []):
            old = s.get("image", "")
            if not old or "avatar" in old:
                continue
            total += 1
            if (ROOT / old).is_file():
                continue
            new_rel, resolved = align_image_path(old, ROOT, index=idx)
            if not new_rel:
                missing += 1
                missing_detail.append(f"ch{ch:02d} {s['id']}: {Path(old).name}")
                continue
            if new_rel != old:
                ch_changed += 1
                changed += 1
                if args.verbose:
                    print(f"  ch{ch:02d} {s['id']}: {Path(old).name} -> {Path(new_rel).name}")
                s["image"] = new_rel

        if ch_changed and not args.dry_run:
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if ch_changed:
            print(f"ch{ch:02d}: 对齐 {ch_changed} 镜")

    print(
        f"\n{'[dry-run] ' if args.dry_run else ''}"
        f"检查 {total} 镜, 对齐 {changed}, 仍缺失 {missing}"
    )
    if missing_detail:
        print("\n无法映射:")
        for line in missing_detail[:20]:
            print(f"  {line}")
        if len(missing_detail) > 20:
            print(f"  … +{len(missing_detail) - 20}")

    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
