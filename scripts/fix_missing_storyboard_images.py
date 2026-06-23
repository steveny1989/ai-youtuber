#!/usr/bin/env python3
"""将分镜中磁盘上已不存在的配图路径，替换为 assets/DaoDeJing 中真实文件。

优先本章标签图（Ch01 / ch01_），不足则用 hybrid_storyboard_util.pick_images。
只改 scenes[].image，保留 narration / motion / ambient 等。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from hybrid_storyboard_util import (  # noqa: E402
    _batch_image_used,
    disk_only_image_files,
    image_on_disk,
    pick_images,
    reset_batch_image_tracking,
    used_images,
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


_BRIGHT_CACHE: dict[str, float] = {}


def _image_brightness(rel: str) -> float:
    if rel in _BRIGHT_CACHE:
        return _BRIGHT_CACHE[rel]
    from PIL import Image

    p = ROOT / rel
    if not p.is_file():
        _BRIGHT_CACHE[rel] = 0.0
        return 0.0
    im = Image.open(p).convert("RGB")
    px = list(im.getdata())
    step = max(1, len(px) // 400)
    val = sum(sum(c) // 3 for c in px[::step]) / max(1, len(px) // step)
    _BRIGHT_CACHE[rel] = val
    return val


def _matches_chapter_filename(name: str, ch: int) -> bool:
    if name.lower().startswith(f"ch{ch:02d}_"):
        return True
    if re.search(rf" - Ch{ch:02d}(?:\.|$)", name, re.I):
        return True
    if ch < 10 and re.search(rf" - Ch{ch}(?:\.|$)", name, re.I):
        return True
    return False


def chapter_tagged_pool(ch: int) -> list[str]:
    dao = ROOT / "assets/DaoDeJing"
    exts = {".jpg", ".jpeg", ".png", ".webp"}
    deprioritize = ("Flat ", "Template ", "Pure ")
    primary: list[str] = []
    fallback: list[str] = []
    for p in sorted(dao.iterdir()):
        if not p.is_file() or p.suffix.lower() not in exts:
            continue
        name = p.name
        if not _matches_chapter_filename(name, ch):
            continue
        rel = f"assets/DaoDeJing/{name}"
        if name.startswith(deprioritize):
            fallback.append(rel)
        else:
            primary.append(rel)
    pool = primary if len(primary) >= len(SCENE_ORDER) else primary + fallback
    pool.sort(key=lambda r: (-_image_brightness(r), Path(r).name))
    return pool


def needs_fix(data: dict) -> bool:
    for s in data.get("scenes", []):
        img = s.get("image", "")
        if img and "avatar" in img:
            continue
        if not image_on_disk(img):
            return True
    return False


def pick_for_chapter(ch: int, *, max_chapter: int) -> list[str]:
    """本章亮图优先，不足则从全库按亮度补齐（不重复）。"""
    need = len(SCENE_ORDER)
    out: list[str] = []
    seen: set[str] = set()

    for rel in chapter_tagged_pool(ch):
        if rel in seen:
            continue
        out.append(rel)
        seen.add(rel)
        if len(out) >= need:
            return out

    used = used_images(max_chapter) | _batch_image_used | seen
    extras = disk_only_image_files(exclude=used)
    extras.sort(key=lambda r: (-_image_brightness(r), Path(r).name))
    for rel in extras:
        if rel in seen:
            continue
        out.append(rel)
        seen.add(rel)
        if len(out) >= need:
            return out

    # 最后兜底：全库最少使用优先（禁止按亮度集中复用同一批雪/光图）
    dao = ROOT / "assets/DaoDeJing"
    exts = {".jpg", ".jpeg", ".png", ".webp"}
    all_files = [
        f"assets/DaoDeJing/{p.name}"
        for p in sorted(dao.iterdir())
        if p.is_file() and p.suffix.lower() in exts and f"assets/DaoDeJing/{p.name}" not in seen
    ]
    global_usage: Counter[str] = Counter()
    for old_ch in range(1, max_chapter):
        op = ROOT / f"examples/storyboard-daodejing-ch{old_ch:02d}-commentary.json"
        if not op.is_file():
            continue
        for s in json.loads(op.read_text(encoding="utf-8")).get("scenes", []):
            img = s.get("image", "")
            if img and "avatar" not in img:
                global_usage[img] += 1
    all_files.sort(
        key=lambda r: (
            r.startswith("assets/DaoDeJing/Flat ")
            or "Template " in Path(r).name
            or "Pure " in Path(r).name,
            global_usage.get(r, 0),
            Path(r).name,
        )
    )
    for rel in all_files:
        out.append(rel)
        seen.add(rel)
        if len(out) >= need:
            break

    if len(out) < need:
        return pick_images(ch, first_chapter=1, max_chapter=max_chapter)
    return out


def fix_chapter(ch: int, *, max_chapter: int, dry_run: bool = False, force: bool = False) -> bool:
    path = ROOT / f"examples/storyboard-daodejing-ch{ch:02d}-commentary.json"
    if not path.is_file():
        return False
    data = json.loads(path.read_text(encoding="utf-8"))
    if not force and not needs_fix(data):
        return False

    scenes = data.get("scenes", [])
    if len(scenes) != len(SCENE_ORDER):
        print(f"  ch{ch:02d} skip: {len(scenes)} scenes (expected {len(SCENE_ORDER)})")
        return False

    imgs = pick_for_chapter(ch, max_chapter=max_chapter)
    if len(imgs) < len(scenes):
        print(f"  ch{ch:02d} skip: only {len(imgs)} images")
        return False

    old = [Path(s["image"]).name for s in scenes]
    new = [Path(imgs[i]).name for i in range(len(scenes))]
    print(f"  ch{ch:02d} remap: {sum(1 for o,n in zip(old,new) if o!=n)} scenes")
    if dry_run:
        for sid, n in zip(SCENE_ORDER, new):
            print(f"    {sid}: {n}")
        return True

    for i, s in enumerate(scenes):
        s["image"] = imgs[i]
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chapters", default="1-81", help="如 1-81 或 1,5,10")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--force",
        action="store_true",
        help="即使路径存在也重新配图（用于换掉过暗/占位图）",
    )
    args = parser.parse_args()

    spec = args.chapters.strip()
    if "-" in spec:
        a, b = spec.split("-", 1)
        chapters = list(range(int(a), int(b) + 1))
    else:
        chapters = [int(x) for x in re.split(r"[,\\s]+", spec) if x.strip()]

    max_ch = max(chapters) if chapters else 81
    reset_batch_image_tracking()
    n = 0
    for ch in chapters:
        if fix_chapter(ch, max_chapter=max_ch, dry_run=args.dry_run, force=args.force):
            n += 1
    print(f"\n{'would fix' if args.dry_run else 'fixed'} {n} chapter(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
