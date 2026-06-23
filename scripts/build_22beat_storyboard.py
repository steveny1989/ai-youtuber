#!/usr/bin/env python3
"""从 ep01 主分镜 + beats + matches 生成 22 镜故事板 JSON。"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[。！？!?；\n])", text.strip())
    return [p.strip() for p in parts if p.strip()]


def split_into_n_chunks(text: str, n: int) -> list[str]:
    """按字数均分句群到 n 段，保证每段非空。"""
    if n <= 1:
        return [text.strip()]
    sents = split_sentences(text)
    if not sents:
        return [text.strip()]

    total = sum(len(s) for s in sents)
    targets = [total * (i + 1) / n for i in range(n - 1)]
    chunks: list[list[str]] = [[] for _ in range(n)]
    acc = 0
    t_idx = 0
    for s in sents:
        chunks[t_idx].append(s)
        acc += len(s)
        if t_idx < n - 1 and acc >= targets[t_idx]:
            t_idx += 1
    result = ["".join(c) for c in chunks if c]
    if not result:
        return [text.strip()]
    # 若桶数不足，合并到最后一段
    while len(result) < n and len(result) > 1:
        result[-2] += result[-1]
        result.pop()
    if len(result) < n:
        result = [text.strip()]
    return result


def main() -> None:
    base = json.loads(
        (ROOT / "examples/storyboard-daodejing-ep01.json").read_text(encoding="utf-8")
    )
    beats_doc = json.loads((ROOT / "examples/ep01_beats.json").read_text(encoding="utf-8"))
    matches_doc = json.loads(
        (ROOT / "examples/ep01_image_matches.json").read_text(encoding="utf-8")
    )
    match_by_beat = {m["beat_id"]: m for m in matches_doc["matches"]}

    section_narration: dict[str, str] = {}
    for sc in base["scenes"]:
        sid = sc["id"]
        if sc.get("narration", "").strip():
            section_narration[sid] = sc["narration"].strip()

    groups: dict[str, list[dict]] = {}
    for b in beats_doc["beats"]:
        groups.setdefault(b["section"], []).append(b)

    scenes: list[dict] = []
    for beat in beats_doc["beats"]:
        sec = beat["section"]
        group = groups[sec]
        idx = group.index(beat)
        text = section_narration.get(sec, "")
        if not text:
            raise SystemExit(f"缺少 section 旁白: {sec}")
        parts = split_into_n_chunks(text, len(group))
        if idx >= len(parts):
            narration = parts[-1]
        else:
            narration = parts[idx]
        narration = narration.strip() or beat["summary"]

        m = match_by_beat[beat["id"]]
        scenes.append(
            {
                "id": beat["id"],
                "narration": narration,
                "image": m["file"],
                "pause_after_sec": 0.35,
            }
        )

    out = {
        "title": base["title"],
        "language": base["language"],
        "chapters": base.get("chapters", []),
        "output": {
            **base["output"],
            "filename": "final.mp4",
        },
        "style": base.get("style", {}),
        "watermark": base.get("watermark", {}),
        "tts": base.get("tts", {}),
        "cover": {"enabled": True, "duration_sec": 5, "narration": ""},
        "ending": base.get("ending", {}),
        "scenes": scenes,
    }

    path = ROOT / "examples/storyboard-daodejing-ep01-22beats.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {path} ({len(scenes)} scenes + ending)")
    for s in scenes:
        print(f"  {s['id']}: {len(s['narration'])} chars")


if __name__ == "__main__":
    main()
