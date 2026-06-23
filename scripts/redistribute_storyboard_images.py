#!/usr/bin/env python3
"""全系列语义配图：旁白↔图鉴打分，三章冷却，全系列 max_reuse。

规则（用户定义）：
  - 同一图在 ch01 出现后，ch02–ch04 禁用，ch05 起可用（冷却 = 3 章）
  - 全系列单图最多 max_reuse 次（默认 3）；少量跨章复用可接受
  - 每章 11 镜不重复；优先本章标签图 + 语义匹配

用法:
  python3 scripts/redistribute_storyboard_images.py --dry-run
  python3 scripts/redistribute_storyboard_images.py --chapters 1-81
  python3 scripts/audit_storyboard_images.py --chapters 60-70
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from image_semantic_util import (  # noqa: E402
    DEFAULT_CHAPTER_COOLDOWN,
    analyze_assignments,
    chapter_tags_in_name,
    load_image_records,
    load_usage_state,
    pick_chapter_images_semantic,
)

SCENE_ORDER = (
    "intro-bridge",
    "open-1",
    "s1",
    "s2",
    "s3",
    "s4",
    "s5",
    "open-ext1",
    "open-ext2",
    "s-ext2",
    "open-close",
)

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}


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


def list_library() -> list[str]:
    dao = ROOT / "assets/DaoDeJing"
    return [
        f"assets/DaoDeJing/{p.name}"
        for p in sorted(dao.iterdir())
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chapters", default="1-81")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max-reuse", type=int, default=3)
    parser.add_argument(
        "--chapter-cooldown",
        type=int,
        default=DEFAULT_CHAPTER_COOLDOWN,
        help="同图冷却章数：chN 用后 chN+1…chN+cooldown 禁用（默认 3 → ch05 可用）",
    )
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    chapters = parse_chapters(args.chapters)
    library = list_library()
    records = load_image_records(library)

    before = analyze_assignments(chapters, chapter_cooldown=args.chapter_cooldown)
    reassign = set(chapters)
    usage, used_chapters = load_usage_state(exclude_chapters=reassign)
    changed = 0

    print(
        f"图库 {len(library)} 张 | 章节 {len(chapters)} | "
        f"max_reuse={args.max_reuse} | 三章冷却={args.chapter_cooldown}"
    )
    print(
        f"修复前: 唯一 {before['unique']} 张, 最高复用 {before['max_reuse']}x, "
        f"冷却违规 {before['cooldown_violations']} 处, "
        f"相邻章重复 {before['adjacent_overlap']} 处"
    )

    for ch in chapters:
        path = ROOT / f"examples/storyboard-daodejing-ch{ch:02d}-commentary.json"
        if not path.is_file():
            print(f"  ch{ch:02d} skip: 无分镜")
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        scenes = data.get("scenes", [])
        if len(scenes) != len(SCENE_ORDER):
            print(f"  ch{ch:02d} skip: {len(scenes)} scenes")
            continue

        scene_pairs = [(s["id"], s.get("narration", "")) for s in scenes]
        picks = pick_chapter_images_semantic(
            ch,
            scene_pairs,
            records,
            usage=usage,
            used_chapters=used_chapters,
            max_reuse=args.max_reuse,
            chapter_cooldown=args.chapter_cooldown,
        )
        imgs = [p[0] for p in picks]

        old = [s.get("image", "") for s in scenes]
        n_diff = sum(1 for a, b in zip(old, imgs) if a != b)
        local = sum(1 for img in imgs if ch in chapter_tags_in_name(Path(img).name))
        if n_diff:
            changed += 1
            avg_score = sum(p[1] for p in picks) / len(picks)
            print(
                f"  ch{ch:02d} {n_diff}/11 镜更换 "
                f"(本章标签 {local}/11, 均分 {avg_score:.1f})"
            )
            if args.verbose or args.dry_run:
                for sid, (old_i, (new_i, sc, kw)) in zip(
                    SCENE_ORDER, zip(old, picks)
                ):
                    if old_i != new_i:
                        kw_s = ",".join(kw[:3]) if kw else "-"
                        print(
                            f"    {sid}: {Path(old_i).name} -> {Path(new_i).name} "
                            f"(+{sc:.1f} {kw_s})"
                        )
        if not args.dry_run and n_diff:
            for i, s in enumerate(scenes):
                s["image"] = imgs[i]
            path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

    if args.dry_run:
        print(f"\n[dry-run] 将更新 {changed} 章分镜")
    else:
        after = analyze_assignments(chapters, chapter_cooldown=args.chapter_cooldown)
        print(
            f"\n修复后: 唯一 {after['unique']} 张, 最高复用 {after['max_reuse']}x, "
            f"冷却违规 {after['cooldown_violations']} 处, "
            f"相邻章重复 {after['adjacent_overlap']} 处"
        )
        print(f"已写入 {changed} 章 storyboard JSON")
        print("审查: python3 scripts/audit_storyboard_images.py --chapters 60-70")
        print("重渲: ./scripts/rerender_hybrid_chapters.sh 1 81")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
