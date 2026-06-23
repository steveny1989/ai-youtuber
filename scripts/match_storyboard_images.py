#!/usr/bin/env python3
"""
节拍 ↔ 配图 打分匹配（每张图在一个 episode 内不重复使用）。

用法:
  python scripts/match_storyboard_images.py \\
    assets/DaoDeJing/ep01_image_catalog.json \\
    examples/ep01_beats.json \\
    -o examples/ep01_image_matches.json

可选: --min-score 3  低于此分的配对会留空，便于人工补图。
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def _tokens(text: str) -> set[str]:
    text = text.strip().lower()
    if not text:
        return set()
    parts = re.split(r"[\s,，、；;：:]+", text)
    out: set[str] = set()
    for p in parts:
        p = p.strip()
        if len(p) >= 2:
            out.add(p)
    # 中文连续片段：保留原句中的 2~6 字窗口（简化）
    for m in re.finditer(r"[\u4e00-\u9fff]{2,6}", text):
        out.add(m.group())
    return out


def _normalize_catalog(catalog_raw: list | dict, catalog_path: Path) -> list[dict]:
    if isinstance(catalog_raw, list):
        images = catalog_raw
    else:
        images = catalog_raw["images"]

    base = catalog_path.parent
    out: list[dict] = []
    for img in images:
        norm = dict(img)
        if not norm.get("file"):
            filename = norm.get("filename", "")
            if not filename:
                continue
            norm["file"] = str(Path("assets/DaoDeJing") / filename).replace("\\", "/")
        if isinstance(norm.get("id"), int):
            norm["id"] = Path(norm["file"]).stem
        out.append(norm)
    return out


def _image_tokens(img: dict) -> set[str]:
    concept = img.get("scene_concept", "")
    filename = Path(img.get("filename") or img.get("file", "")).stem
    chunks = [
        img.get("description_zh", ""),
        img.get("description", ""),
        " ".join(img.get("tags", [])),
        " ".join(img.get("themes", [])),
        " ".join(img.get("match_keywords", [])),
        str(img.get("id", "")).replace("ep01_", "").replace("ep02_", "").replace("ep03_", ""),
        concept.replace("_", " "),
        filename.replace("ep02_", "").replace("ep03_", "").replace("_", " "),
    ]
    tokens: set[str] = set()
    for c in chunks:
        tokens |= _tokens(c)
    return tokens


def score_pair(beat: dict, img: dict) -> tuple[float, list[str]]:
    beat_kw = set(beat.get("keywords", []))
    beat_kw |= _tokens(beat.get("summary", ""))
    beat_section = beat.get("section", "")

    img_tokens = _image_tokens(img)
    themes = set(img.get("themes", []))

    matched = [k for k in beat_kw if k in img_tokens or any(k in t for t in img_tokens)]
    overlap = len(matched)

    section_bonus = 0.0
    if beat_section and beat_section in themes:
        section_bonus = 4.0
    elif beat_section and any(beat_section.startswith(t) for t in themes):
        section_bonus = 2.0

    # 风格惩罚：intro 节拍避免纯毁城宽景（可调）
    style_penalty = 0.0
    if beat_section == "intro" and img.get("visual_style") == "v3_wide":
        tags = img.get("tags", [])
        if "火" in tags or "废墟" in tags:
            style_penalty = 2.0

    raw = overlap * 2.0 + section_bonus - style_penalty
    return raw, matched


def greedy_match(
    beats: list[dict],
    images: list[dict],
    *,
    min_score: float = 0.0,
    exclude_files: set[str] | None = None,
) -> list[dict]:
    exclude = exclude_files or set()
    images = [img for img in images if img.get("file") not in exclude]
    pairs: list[tuple[float, int, int, list[str]]] = []
    for bi, beat in enumerate(beats):
        for ii, img in enumerate(images):
            sc, matched = score_pair(beat, img)
            pairs.append((sc, bi, ii, matched))

    pairs.sort(key=lambda x: x[0], reverse=True)

    used_beats: set[int] = set()
    used_images: set[int] = set()
    assignment: dict[int, tuple[int, float, list[str]]] = {}

    for sc, bi, ii, matched in pairs:
        if bi in used_beats or ii in used_images:
            continue
        if sc < min_score:
            continue
        used_beats.add(bi)
        used_images.add(ii)
        assignment[bi] = (ii, sc, matched)

    results: list[dict] = []
    for bi, beat in enumerate(beats):
        if bi in assignment:
            ii, sc, matched = assignment[bi]
            img = images[ii]
            results.append(
                {
                    "beat_id": beat["id"],
                    "section": beat.get("section"),
                    "summary": beat.get("summary"),
                    "image_id": img["id"],
                    "file": img["file"],
                    "score": round(sc, 2),
                    "matched_keywords": matched,
                }
            )
        else:
            results.append(
                {
                    "beat_id": beat["id"],
                    "section": beat.get("section"),
                    "summary": beat.get("summary"),
                    "image_id": None,
                    "file": None,
                    "score": 0,
                    "matched_keywords": [],
                    "note": "未分到图（提高节拍数或降低 --min-score）",
                }
            )
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="节拍与配图打分匹配（不重复）")
    parser.add_argument("catalog", type=Path, help="图鉴 JSON，如 ep01_image_catalog.json")
    parser.add_argument("beats", type=Path, help="节拍 JSON，如 ep01_beats.json")
    parser.add_argument("-o", "--output", type=Path, required=True)
    parser.add_argument(
        "--min-score",
        type=float,
        default=0.0,
        help="最低接受分数，低于则不分配",
    )
    parser.add_argument(
        "--exclude-file",
        action="append",
        default=[],
        help="排除的图片相对路径（可重复）",
    )
    args = parser.parse_args()

    catalog_raw = json.loads(args.catalog.read_text(encoding="utf-8"))
    beats_doc = json.loads(args.beats.read_text(encoding="utf-8"))
    beats = beats_doc["beats"]
    images = _normalize_catalog(catalog_raw, args.catalog)
    images = [img for img in images if Path(img["file"]).exists()]

    if len(beats) > len(images):
        raise SystemExit(
            f"节拍数({len(beats)}) 大于 图片数({len(images)})，无法做到每张图不重复。"
        )

    matches = greedy_match(
        beats,
        images,
        min_score=args.min_score,
        exclude_files=set(args.exclude_file),
    )

    out = {
        "meta": {
            "catalog": str(args.catalog),
            "beats": str(args.beats),
            "beat_count": len(beats),
            "image_count": len(images),
            "pool_count": len(images) - len(set(args.exclude_file)),
            "excluded": len(set(args.exclude_file)),
            "assigned": sum(1 for m in matches if m.get("file")),
            "min_score": args.min_score,
            "algorithm": "greedy_max_score_no_reuse",
        },
        "matches": matches,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"已写入 {args.output}（{out['meta']['assigned']}/{len(beats)} 个节拍已配图）")


if __name__ == "__main__":
    main()
