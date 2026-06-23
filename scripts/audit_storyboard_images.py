#!/usr/bin/env python3
"""审查分镜配图：三章冷却、全系列复用、章内重复、语义低分。

用法:
  python3 scripts/audit_storyboard_images.py --chapters 60-70
  python3 scripts/audit_storyboard_images.py --chapters 1-81
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from image_semantic_util import (  # noqa: E402
    DEFAULT_CHAPTER_COOLDOWN,
    analyze_assignments,
    chapter_tags_in_name,
    load_image_records,
    semantic_only_score,
)

from pipeline.image_resolve import resolve_daodejing_image  # noqa: E402

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
    parser.add_argument("--chapters", default="60-70")
    parser.add_argument("--max-reuse", type=int, default=3)
    parser.add_argument("--chapter-cooldown", type=int, default=DEFAULT_CHAPTER_COOLDOWN)
    parser.add_argument("--low-score", type=float, default=2.0, help="低于此语义分标 WARN")
    args = parser.parse_args()

    chapters = parse_chapters(args.chapters)
    library = [f"assets/DaoDeJing/{p.name}" for p in sorted((ROOT / "assets/DaoDeJing").iterdir())]
    records = {r["file"]: r for r in load_image_records(library)}

    # 全系列用量（用于冷却检查）
    usage = Counter()
    used_at: dict[str, list[int]] = defaultdict(list)
    for ch in range(1, 82):
        path = ROOT / f"examples/storyboard-daodejing-ch{ch:02d}-commentary.json"
        if not path.is_file():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        for s in data.get("scenes", []):
            img = s.get("image", "")
            if img:
                usage[img] += 1
                used_at[img].append(ch)

    summary = analyze_assignments(
        list(range(1, 82)), chapter_cooldown=args.chapter_cooldown
    )
    print(
        f"全系列: 唯一 {summary['unique']} 张, 最高复用 {summary['max_reuse']}x, "
        f"冷却违规 {summary['cooldown_violations']} 处"
    )
    print(f"审查范围: ch{chapters[0]:02d}–ch{chapters[-1]:02d}\n")

    issues = 0
    for ch in chapters:
        path = ROOT / f"examples/storyboard-daodejing-ch{ch:02d}-commentary.json"
        if not path.is_file():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        scenes = data.get("scenes", [])
        imgs = [s.get("image", "") for s in scenes]
        ch_issues: list[str] = []

        if len(set(imgs)) != len(imgs):
            ch_issues.append("章内重复")

        local = sum(1 for img in imgs if ch in chapter_tags_in_name(Path(img).name))
        if local < 3:
            ch_issues.append(f"本章标签仅 {local}/11")

        for img in imgs:
            if usage[img] > args.max_reuse:
                ch_issues.append(f"超 max_reuse: {Path(img).name} ({usage[img]}x)")
            if "avatar" not in img and resolve_daodejing_image(img, ROOT) is None:
                ch_issues.append(f"磁盘缺失: {Path(img).name}")
            for prev in used_at[img]:
                if prev < ch and ch - prev <= args.chapter_cooldown:
                    ch_issues.append(
                        f"冷却违规: {Path(img).name} ch{prev:02d}→ch{ch:02d}"
                    )

        low_scores: list[str] = []
        for s in scenes:
            sid = s["id"]
            img = s.get("image", "")
            rec = records.get(img)
            if not rec:
                continue
            sc = semantic_only_score(sid, s.get("narration", ""), rec, ch)
            if sc < args.low_score:
                low_scores.append(f"{sid}:{Path(img).name}({sc:.1f})")

        if ch_issues or low_scores:
            issues += 1
            print(f"ch{ch:02d}:")
            for msg in ch_issues:
                print(f"  ⚠ {msg}")
            if low_scores:
                print(f"  低语义分: {', '.join(low_scores[:4])}")
        else:
            print(f"ch{ch:02d}: OK (本章标签 {local}/11)")

    print(f"\n{'PASS' if issues == 0 else f'{issues} 章需人工复核'}")
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
