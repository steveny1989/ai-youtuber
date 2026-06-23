#!/usr/bin/env python3
"""生成单章投稿封面（YouTube / B 站缩略图）。

示例：
  python3 scripts/make_chapter_cover.py --chapter 40
  python3 scripts/make_chapter_cover.py --chapter 40 --hook "反者道之动" --sub-hook "弱者道之用"
  python3 scripts/make_chapter_cover.py --chapters 1-81
  python3 scripts/make_chapter_cover.py --chapter 40 --preview
"""

from __future__ import annotations

import argparse
import importlib.util
import re
import sys
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PIL import Image  # noqa: E402

from pipeline.brand import COVER_OUTPUT_DIR  # noqa: E402
from pipeline.image_resolve import get_index, resolve_daodejing_image  # noqa: E402
from pipeline.models import Storyboard  # noqa: E402
from pipeline.slides import render_chapter_thumbnail, render_chapter_thumbnail_vertical  # noqa: E402

_RENDER_ARTIFACT = re.compile(r"(_base\.png$|/segments/|/commentary\.work/)", re.I)


def parse_chapters(spec: str) -> list[int]:
    spec = spec.strip()
    if "-" in spec:
        a, b = spec.split("-", 1)
        return list(range(int(a), int(b) + 1))
    return [int(x) for x in spec.split(",") if x.strip()]


def _image_label(path: Path) -> str:
    stem = path.stem
    part = stem.split(" - ")[0].strip()
    return part if part else stem


@lru_cache(maxsize=1)
def _chapter_texts() -> dict[int, str]:
    spec = importlib.util.spec_from_file_location(
        "build_daodejing_81_full",
        ROOT / "scripts" / "build_daodejing_81_full.py",
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod.load_chapter_texts()


def _classic_hooks(chapter: int) -> tuple[str, str]:
    """从 taoteching 原文提取主/副标题（如 反者道之动 / 弱者道之用）。"""
    raw = _chapter_texts()[chapter]
    raw = re.sub(rf"^第{chapter}章[。．]?", "", raw)
    head = raw.split("。")[0].split("；")[0]
    parts = [p.strip() for p in head.split("，") if p.strip()]

    def join_pair(i: int, *, max_len: int = 8) -> str:
        a = re.sub(r"\s+", "", parts[i])
        if i + 1 < len(parts) and len(a) <= 4:
            b = re.sub(r"\s+", "", parts[i + 1])
            combined = a + b
            if len(combined) <= max_len:
                return combined
        return a[:max_len]

    hook = join_pair(0) if parts else ""
    sub = ""
    if len(parts) >= 2:
        if len(parts[0]) <= 4 and len(parts) >= 4:
            sub = join_pair(2)
        elif len(parts[0]) <= 4 and len(parts) > 2:
            sub = re.sub(r"\s+", "", parts[2])[:8]
        else:
            sub = re.sub(r"\s+", "", parts[1])[:8]
    return hook, sub


def _resolve_scene_image(
    storyboard: Storyboard,
    scene_id: str,
    project_root: Path,
) -> Path | None:
    for scene in storyboard.scenes:
        if scene.id != scene_id or not scene.image:
            continue
        hit = resolve_daodejing_image(scene.image, project_root, index=get_index(project_root))
        if hit and hit.is_file() and not _RENDER_ARTIFACT.search(str(hit)):
            return hit.resolve()
    return None


def _pick_background(
    storyboard: Storyboard,
    chapter: int,
    project_root: Path,
    *,
    hook: str = "",
) -> Path:
    hook_key = hook.strip().replace(" ", "")
    idx = get_index(project_root)

    if hook_key:
        pat = re.compile(rf"ch0?{chapter}\b", re.I)
        for f in idx.all_files:
            if pat.search(f.name) and hook_key in _image_label(f).replace(" ", ""):
                return f.resolve()

    for sid in ("open-1", "intro-bridge", "s1", "s2"):
        hit = _resolve_scene_image(storyboard, sid, project_root)
        if hit is not None:
            return hit

    pat = re.compile(rf"-\s*ch0?{chapter}\b", re.I)
    for f in idx.all_files:
        if pat.search(f.name.lower()):
            return f.resolve()

    ph = project_root / "assets" / "placeholder.jpg"
    return ph.resolve() if ph.is_file() else idx.all_files[0].resolve()


def _derive_hooks(
    storyboard: Storyboard,
    chapter: int,
    background: Path,
    project_root: Path,
    *,
    hook: str = "",
    sub_hook: str = "",
) -> tuple[str, str]:
    if hook.strip():
        return hook.strip(), sub_hook.strip()

    cover_hook = (storyboard.cover.hook or "").strip()
    if cover_hook:
        return cover_hook, sub_hook.strip() or (storyboard.cover.subtitle or "").strip()

    classic_main, classic_sub = _classic_hooks(chapter)
    primary = classic_main
    secondary = sub_hook.strip() or classic_sub
    return primary, secondary


def cover_output_path(chapter: int, project_root: Path, *, vertical: bool = False) -> Path:
    suffix = "-douyin" if vertical else ""
    return project_root / COVER_OUTPUT_DIR / f"daodejing-ch{chapter:02d}-cover{suffix}.jpg"


def storyboard_path(chapter: int, project_root: Path) -> Path:
    return project_root / f"examples/storyboard-daodejing-ch{chapter:02d}-commentary.json"


def make_cover(
    chapter: int,
    *,
    project_root: Path,
    hook: str = "",
    sub_hook: str = "",
    series_label: str = "道德经 · 八十一讲精解",
    preview: bool = False,
    vertical: bool = False,
) -> Path:
    sb_path = storyboard_path(chapter, project_root)
    if not sb_path.is_file():
        raise FileNotFoundError(f"分镜不存在: {sb_path}")
    storyboard = Storyboard.load(sb_path)
    main_hook, sub = _derive_hooks(
        storyboard, chapter, Path(), project_root, hook=hook, sub_hook=sub_hook
    )
    background = _pick_background(
        storyboard, chapter, project_root, hook=main_hook
    )
    main_hook, sub = _derive_hooks(
        storyboard, chapter, background, project_root, hook=hook, sub_hook=sub_hook
    )
    out = cover_output_path(chapter, project_root, vertical=vertical)

    if vertical:
        render_chapter_thumbnail_vertical(
            chapter_num=chapter,
            hook=main_hook,
            sub_hook=sub,
            background=background,
            out_path=out,
            series_label=series_label,
        )
    else:
        render_chapter_thumbnail(
            chapter_num=chapter,
            hook=main_hook,
            sub_hook=sub,
            background=background,
            out_path=out,
            series_label=series_label,
        )

    if preview:
        if vertical:
            prev = out.with_name(out.stem + "-preview-360.jpg")
            img = Image.open(out).convert("RGB")
            img = img.resize((360, 640), Image.Resampling.LANCZOS)
        else:
            prev = out.with_name(out.stem + "-preview-640.jpg")
            img = Image.open(out).convert("RGB")
            img = img.resize((640, 360), Image.Resampling.LANCZOS)
        img.save(prev, format="JPEG", quality=90)
        print(f"  手机预览: {prev}")

    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chapter", type=int, default=None)
    parser.add_argument("--chapters", default=None)
    parser.add_argument("--hook", default="")
    parser.add_argument("--sub-hook", default="")
    parser.add_argument("--series-label", default="道德经 · 八十一讲精解")
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--vertical", action="store_true", help="生成抖音竖版封面（1080×1920）")
    args = parser.parse_args()

    if args.chapters:
        chapters = parse_chapters(args.chapters)
    elif args.chapter is not None:
        chapters = [args.chapter]
    else:
        parser.error("请指定 --chapter 或 --chapters")

    for ch in chapters:
        out = make_cover(
            ch,
            project_root=ROOT,
            hook=args.hook if len(chapters) == 1 else "",
            sub_hook=args.sub_hook if len(chapters) == 1 else "",
            series_label=args.series_label,
            preview=args.preview,
            vertical=args.vertical,
        )
        sb = Storyboard.load(storyboard_path(ch, ROOT))
        hook, sub = _derive_hooks(sb, ch, Path(), ROOT)
        bg = _pick_background(sb, ch, ROOT, hook=hook)
        print(f"ch{ch:02d} 封面 → {out}")
        print(f"       主标题: {hook}")
        print(f"       副标题: {sub}")
        print(f"       背景: {bg.name}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
