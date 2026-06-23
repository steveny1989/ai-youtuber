#!/usr/bin/env python3
"""将 ch36_40_narrations 写入分镜 JSON（保留配图，更新 narration + 起号 CTA）。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from ch36_40_narrations import NARRATIONS  # noqa: E402
from pipeline.brand import GROWTH_CTA_DESCRIPTION, GROWTH_CTA_NARRATION  # noqa: E402

EXAMPLES = ROOT / "examples"
GROWTH_DYNAMIC_SUFFIX = "观念黑盒起号中，欢迎点个关注，八十一讲我们会讲完。"

SCENE_ORDER = [
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
]


def _load_ch40_from_file() -> dict[str, str]:
    path = EXAMPLES / "storyboard-daodejing-ch40-commentary.json"
    sb = json.loads(path.read_text(encoding="utf-8"))
    return {s["id"]: s["narration"] for s in sb["scenes"]}


def apply_chapter(ch: int) -> None:
    path = EXAMPLES / f"storyboard-daodejing-ch{ch:02d}-commentary.json"
    if not path.is_file():
        raise SystemExit(f"缺少 {path}")

    narrs = NARRATIONS.get(ch) or {}
    if ch == 40 and not narrs:
        narrs = _load_ch40_from_file()

    sb = json.loads(path.read_text(encoding="utf-8"))
    by_id = {s["id"]: s for s in sb["scenes"]}

    for sid in SCENE_ORDER:
        if sid not in by_id:
            raise SystemExit(f"ch{ch} 缺少镜位 {sid}")
        if sid not in narrs:
            raise SystemExit(f"ch{ch} 缺少 narration[{sid}]")
        by_id[sid]["narration"] = narrs[sid]

    sb["scenes"] = [by_id[sid] for sid in SCENE_ORDER]

    sb.setdefault("ending", {})
    sb["ending"]["enabled"] = True
    sb["ending"]["image"] = sb["ending"].get("image") or "assets/avatar.webp"
    sb["ending"]["duration_sec"] = 0
    sb["ending"]["narration"] = GROWTH_CTA_NARRATION

    yt = sb.setdefault("youtube", {})
    yt["description_footer"] = GROWTH_CTA_DESCRIPTION

    bili = sb.setdefault("bilibili", {})
    base = (bili.get("dynamic") or "").split("观念黑盒起号")[0].strip()
    if base.endswith("。"):
        bili["dynamic"] = f"{base}{GROWTH_DYNAMIC_SUFFIX}"
    elif base:
        bili["dynamic"] = f"{base}。{GROWTH_DYNAMIC_SUFFIX}"
    else:
        bili["dynamic"] = GROWTH_DYNAMIC_SUFFIX

    path.write_text(json.dumps(sb, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    total = sum(len(s["narration"]) for s in sb["scenes"])
    print(f"ch{ch:02d}  {total} 字  →  {path.relative_to(ROOT)}")


def main() -> int:
    for ch in range(36, 41):
        apply_chapter(ch)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
