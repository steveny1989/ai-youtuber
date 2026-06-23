#!/usr/bin/env python3
"""修复 ch40–50 讲解分镜：有效配图 + pan 推轨 + ambient 块（保留 narration）。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from ch46_50_images import CHAPTER_SCENE_IMAGES  # noqa: E402
from hybrid_storyboard_util import (  # noqa: E402
    pick_images,
    pick_semantic_images,
    reset_batch_image_tracking,
)
from pipeline.motion import default_motion_for_scene  # noqa: E402

AMBIENT = {
    "enabled": True,
    "dust_opacity": 0.15,
    "ink_opacity": 0.07,
    "water_opacity": 0.09,
}


def _existing_explicit(ch: int) -> dict[str, str]:
    mapping = CHAPTER_SCENE_IMAGES.get(ch, {})
    out: dict[str, str] = {}
    for sid, fn in mapping.items():
        rel = fn if fn.startswith("assets/") else f"assets/DaoDeJing/{fn}"
        if (ROOT / rel).is_file():
            out[sid] = Path(fn).name if not fn.startswith("assets/") else fn
    return out


def fix_chapter(ch: int) -> None:
    path = ROOT / f"examples/storyboard-daodejing-ch{ch:02d}-commentary.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    scene_ids = [s["id"] for s in data["scenes"]]
    explicit = _existing_explicit(ch)
    if len(explicit) >= 3:
        imgs = pick_semantic_images(
            ch, scene_ids, explicit, first_chapter=40, max_chapter=50
        )
    else:
        imgs = pick_images(ch, first_chapter=40, max_chapter=50)

    for i, scene in enumerate(data["scenes"]):
        scene["image"] = imgs[i]
        scene["motion"] = default_motion_for_scene(scene["id"])

    data.setdefault("style", {})["motion"] = "auto"
    data["ambient"] = dict(AMBIENT)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"fixed ch{ch:02d}")


def main() -> None:
    reset_batch_image_tracking()
    for ch in range(40, 51):
        fix_chapter(ch)


if __name__ == "__main__":
    main()
