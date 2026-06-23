#!/usr/bin/env python3
"""批量洗稿：用生成器干净稿覆盖 narration，保留配图与元数据。

  python3 scripts/clean_commentary_batch.py --chapters 22-30 --write
  python3 scripts/clean_commentary_batch.py --chapters 31-40 --write
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from commentary_quality import apply_scene_enrichments  # noqa: E402
from review_commentary import PASS_SCORE, format_report, review_storyboard  # noqa: E402

EXAMPLES = ROOT / "examples"


def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


def clean_narrations_for_chapter(ch: int) -> dict[str, str]:
    """从 CHAPTER_META + 实质 enrich 生成干净旁白（无套话垫字）。"""
    if 21 <= ch <= 25:
        meta = _load_module("g21", "generate_ch21_25_storyboards.py").CHAPTER_META[ch]
    elif 26 <= ch <= 30:
        meta = _load_module("g26", "generate_ch26_30_storyboards.py").CHAPTER_META[ch]
    elif 31 <= ch <= 35:
        meta = _load_module("g31", "generate_ch31_35_storyboards.py").CHAPTER_META[ch]
    elif 36 <= ch <= 40:
        meta = _load_module("g36", "generate_ch36_40_storyboards.py").CHAPTER_META[ch]
    else:
        raise ValueError(f"无生成器元数据: ch{ch}")
    scenes = apply_scene_enrichments(meta["scenes"], ch)
    return dict(scenes)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chapters", default="31-40")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    spec = args.chapters.strip()
    if "-" in spec:
        a, b = spec.split("-", 1)
        chapters = list(range(int(a), int(b) + 1))
    else:
        chapters = [int(x) for x in spec.split(",") if x.strip()]

    if not args.write:
        print("预览：仅显示洗稿后质检（加 --write 写回 narration）\n")

    failed = 0
    for ch in chapters:
        path = EXAMPLES / f"storyboard-daodejing-ch{ch:02d}-commentary.json"
        if not path.is_file():
            print(f"跳过 ch{ch:02d}: 无 {path.name}")
            continue

        clean = clean_narrations_for_chapter(ch)
        sb = json.loads(path.read_text(encoding="utf-8"))

        if args.write:
            for scene in sb.get("scenes", []):
                sid = scene.get("id")
                if sid in clean:
                    scene["narration"] = clean[sid]
            path.write_text(json.dumps(sb, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        review = review_storyboard(path.resolve())
        print(format_report(review))
        if not review.passed:
            failed += 1

    if args.write:
        print("已更新 narration（配图/tts/youtube 等未动）。")
    if failed:
        print(f"\n{failed} 章未达 {PASS_SCORE} 分。")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
