#!/usr/bin/env python3
"""Hybrid 单章讲解分镜共用工具（默认 ≥5 分钟；long_form ≥7 分钟）。"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"
CATALOG = ROOT / "assets/DaoDeJing/image_catalog.json"

import sys

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.brand import GROWTH_CTA_DESCRIPTION, GROWTH_CTA_NARRATION
from pipeline.motion import default_motion_for_scene


def _series_config():
    from pipeline.series_config import load_daodejing_81_series

    return load_daodejing_81_series(ROOT)


def _series_playlist_id() -> str:
    return _series_config().youtube_playlist_id


def _series_bilibili_series_id() -> int:
    return _series_config().bilibili_series_id


def _series_bilibili_season_id() -> int:
    return _series_config().bilibili_season_id


# ch01 约 1618 字 → ~6 分钟；1350 字约可稳过 5 分钟（含朗读段+片尾）
# ch01 约 1618 字 → 6 分钟；≥1250 字讲解 + 朗读/片尾，实测可稳过 5 分钟
MIN_COMMENTARY_CHARS = 1050
MIN_COMMENTARY_CHARS_7MIN = 1550

_CN_NUM = (
    "",
    "一",
    "二",
    "三",
    "四",
    "五",
    "六",
    "七",
    "八",
    "九",
    "十",
    "十一",
    "十二",
    "十三",
    "十四",
    "十五",
    "十六",
    "十七",
    "十八",
    "十九",
    "二十",
    "二十一",
    "二十二",
    "二十三",
    "二十四",
    "二十五",
    "二十六",
    "二十七",
    "二十八",
    "二十九",
    "三十",
    "三十一",
    "三十二",
    "三十三",
    "三十四",
    "三十五",
    "三十六",
    "三十七",
    "三十八",
    "三十九",
    "四十",
)


def disk_only_image_files(*, exclude: set[str]) -> list[str]:
    """磁盘上有、且未在 exclude 中的 DaoDeJing 配图（含未入 catalog 的 ep03/ep04）。"""
    dao = ROOT / "assets/DaoDeJing"
    out: list[str] = []
    for ext in ("*.jpg", "*.png", "*.webp"):
        for p in sorted(dao.glob(ext)):
            rel = f"assets/DaoDeJing/{p.name}"
            if rel not in exclude:
                out.append(rel)
    return out


def make_tts_config(provider: str = "volcengine") -> dict:
    if provider.lower() == "edge":
        return {
            "provider": "edge",
            "voice": "zh-CN-YunxiNeural",
            "rate": "-8%",
        }
    return {
        "provider": "volcengine",
        "voice": "zh_male_ruyaqingnian_uranus_bigtts",
        "resource_id": "seed-tts-2.0",
        "emotion": "narrator",
        "rate": "-5%",
    }


def chapter_title_cn(ch: int) -> str:
    if 1 <= ch <= len(_CN_NUM) - 1:
        return _CN_NUM[ch]
    return str(ch)


def pause_after_sec(scene_id: str, *, long_form: bool = False) -> float:
    if long_form:
        if scene_id == "intro-bridge":
            return 0.85
        if scene_id == "open-close":
            return 0.78
        if scene_id in ("open-ext1", "open-ext2", "s-ext2"):
            return 0.72
        return 0.62
    if scene_id == "intro-bridge":
        return 0.65
    if scene_id == "open-close":
        return 0.58
    if scene_id in ("open-ext1", "open-ext2", "s-ext2"):
        return 0.52
    return 0.48


def used_images(max_chapter: int) -> set[str]:
    used: set[str] = set()
    for ch in range(1, max_chapter):
        path = EXAMPLES / f"storyboard-daodejing-ch{ch:02d}-commentary.json"
        if not path.is_file():
            continue
        sb = json.loads(path.read_text(encoding="utf-8"))
        for s in sb.get("scenes", []):
            img = s.get("image")
            if img and "avatar" not in img:
                used.add(img)
    return used


_batch_image_used: set[str] = set()


def reset_batch_image_tracking() -> None:
    _batch_image_used.clear()


def image_on_disk(rel: str) -> bool:
    return (ROOT / rel).is_file()


def _matches_chapter_filename(name: str, ch: int) -> bool:
    import re

    if name.lower().startswith(f"ch{ch:02d}_"):
        return True
    if re.search(rf" - Ch{ch:02d}(?:\.|$)", name, re.I):
        return True
    if ch < 10 and re.search(rf" - Ch{ch}(?:\.|$)", name, re.I):
        return True
    return False


def _spare_image(ch: int, *, seen: set[str], used: set[str]) -> str:
    """为本章选一镜备用图：本章内未用过即可（可跨章）。"""
    dao = ROOT / "assets/DaoDeJing"
    exts = {".jpg", ".jpeg", ".png", ".webp"}
    candidates: list[str] = []
    for p in sorted(dao.iterdir()):
        if p.suffix.lower() not in exts:
            continue
        rel = f"assets/DaoDeJing/{p.name}"
        if rel in seen:
            continue
        candidates.append(rel)
    if not candidates:
        raise SystemExit(f"第 {ch} 章无可用替补配图（本章已用 {len(seen)} 张）")
    for rel in candidates:
        name = Path(rel).name
        if _matches_chapter_filename(name, ch):
            return rel
    for rel in candidates:
        name = Path(rel).name
        if not _matches_chapter_filename(name, ch):
            return rel
    return candidates[0]


def pick_semantic_images(
    ch: int,
    scene_ids: list[str],
    explicit: dict[str, str],
    *,
    first_chapter: int,
    max_chapter: int,
) -> list[str]:
    """语义优先：explicit 映射 → 本章 chNN_* → 旧逻辑兜底；本章 11 镜不重复。"""
    from pathlib import Path as _Path

    dao = ROOT / "assets/DaoDeJing"
    used = used_images(max_chapter) | _batch_image_used
    out: list[str] = []
    seen: set[str] = set()

    def resolve_rel(filename: str) -> str:
        rel = filename if filename.startswith("assets/") else f"assets/DaoDeJing/{filename}"
        if not (_Path(ROOT) / rel).is_file():
            raise SystemExit(f"第 {ch} 章配图不存在: {rel}")
        return rel

    chapter_prefix = f"ch{ch:02d}_"
    chapter_pool = sorted(
        f"assets/DaoDeJing/{p.name}"
        for p in dao.glob(f"{chapter_prefix}*.jpg")
        if f"assets/DaoDeJing/{p.name}" not in seen
    )
    pool_idx = 0

    for sid in scene_ids:
        if sid in explicit:
            rel = resolve_rel(explicit[sid])
        elif chapter_pool:
            rel = chapter_pool[pool_idx % len(chapter_pool)]
            pool_idx += 1
        else:
            rel = ""
        if rel and rel in seen:
            print(
                f"  [ch{ch:02d}] {sid} 配图重复 {Path(rel).name}，改用替补",
                file=sys.stderr,
            )
            rel = _spare_image(ch, seen=seen, used=used)
        if not rel:
            rel = _spare_image(ch, seen=seen, used=used)
        out.append(rel)
        seen.add(rel)
        used.add(rel)

    if len(out) == len(scene_ids) and all(out) and len(seen) == len(out):
        _batch_image_used.update(out)
        local = sum(1 for p in out if f"/ch{ch:02d}_" in p or f"Ch{ch:02d}" in p or f"Ch{ch}" in Path(p).name)
        print(f"  [ch{ch:02d}] 语义配图 {local}/{len(out)} 张本章，{len(seen)} 张不重复")
        return out

    return pick_images(ch, first_chapter=first_chapter, max_chapter=max_chapter)


def pick_images(ch: int, *, first_chapter: int, max_chapter: int) -> list[str]:
    used = used_images(max_chapter) | _batch_image_used
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    catalog_files = [
        img["file"] for img in catalog["images"] if image_on_disk(img["file"])
    ]
    disk_new = disk_only_image_files(exclude=used)
    catalog_new = [f for f in catalog_files if f not in used]
    # 优先从未用过的磁盘图（ep03/ep04 等），再用 catalog 余量
    avail = disk_new + [f for f in catalog_new if f not in disk_new]
    chunk = avail[:11]
    if len(chunk) >= 11:
        _batch_image_used.update(chunk)
        if disk_new[:11]:
            print(f"  [ch{ch:02d}] 新图 {min(11, len(disk_new))} 张（含磁盘未入 catalog）")
        return chunk

    need = 11 - len(chunk)
    # 轮回：优先选用在旧章节里只出现过 1 次的图，且每章尽量来自不同旧章
    from collections import Counter

    img_count: Counter[str] = Counter()
    img_by_source: dict[str, list[int]] = {}
    for old_ch in range(1, max_chapter):
        path = EXAMPLES / f"storyboard-daodejing-ch{old_ch:02d}-commentary.json"
        if not path.is_file():
            continue
        sb = json.loads(path.read_text(encoding="utf-8"))
        for s in sb.get("scenes", []):
            img = s.get("image")
            if img and "avatar" not in img:
                img_count[img] += 1
                img_by_source.setdefault(img, []).append(old_ch)

    candidates = [
        img
        for img, _ in sorted(img_count.items(), key=lambda x: (x[1], x[0]))
        if img not in chunk
        and img not in _batch_image_used
        and image_on_disk(img)
    ]
    recycled: list[str] = []
    used_sources: set[int] = set()
    for img in candidates:
        if len(recycled) >= need:
            break
        sources = img_by_source.get(img, [])
        if sources and all(s in used_sources for s in sources) and len(used_sources) > 3:
            continue
        recycled.append(img)
        used_sources.update(sources[:1])

    if len(recycled) < need:
        for img in candidates:
            if img in recycled:
                continue
            recycled.append(img)
            if len(recycled) >= need:
                break

    if len(chunk) + len(recycled) < 11:
        raise SystemExit(
            f"第 {ch} 章配图不足 11 张（新 {len(avail)} + 轮回 {len(recycled)}）"
        )
    out = chunk + recycled[:need]
    _batch_image_used.update(out)
    parts = []
    if chunk:
        parts.append(f"新 {len(chunk)}")
    if recycled:
        parts.append(f"轮回 {len(recycled)}")
    print(f"  [ch{ch:02d}] 配图 " + "，".join(parts))
    return out


def validate_commentary_length(
    ch: int,
    scenes: list[tuple[str, str]],
    *,
    min_chars: int | None = None,
    target_label: str = "5 分钟",
) -> int:
    floor = min_chars if min_chars is not None else MIN_COMMENTARY_CHARS
    total = sum(len(narr) for _, narr in scenes)
    if total < floor:
        raise SystemExit(
            f"第 {ch} 章讲解字数 {total} < {floor}，"
            f"预计成片不足 {target_label}，请加长 narration。"
        )
    return total


def build_storyboard(
    ch: int,
    meta: dict,
    *,
    first_chapter: int,
    max_chapter: int,
    tts_provider: str = "volcengine",
    long_form: bool = False,
    min_commentary_chars: int | None = None,
    scene_images: dict[str, str] | None = None,
    motion: str = "auto",
) -> dict:
    scene_ids = [sid for sid, _ in meta["scenes"]]
    if scene_images:
        imgs = pick_semantic_images(
            ch,
            scene_ids,
            scene_images,
            first_chapter=first_chapter,
            max_chapter=max_chapter,
        )
    else:
        imgs = pick_images(ch, first_chapter=first_chapter, max_chapter=max_chapter)
    scenes_meta: list[tuple[str, str]] = meta["scenes"]
    min_chars = min_commentary_chars
    if min_chars is None:
        min_chars = MIN_COMMENTARY_CHARS_7MIN if long_form else MIN_COMMENTARY_CHARS
    target_label = "7 分钟" if long_form else "5 分钟"
    total_chars = validate_commentary_length(
        ch, scenes_meta, min_chars=min_chars, target_label=target_label
    )

    scenes = []
    for i, (sid, narr) in enumerate(scenes_meta):
        scene_motion = meta.get("scene_motions", {}).get(sid) or default_motion_for_scene(sid)
        scenes.append(
            {
                "id": sid,
                "narration": narr,
                "image": imgs[i],
                "motion": scene_motion,
                "pause_after_sec": pause_after_sec(sid, long_form=long_form),
            }
        )
    ch_labels = meta["chapters"]
    return {
        "title": f"观念黑盒：《道德经》第{chapter_title_cn(ch)}章精解",
        "language": "zh-CN",
        "chapters": [{"id": str(i + 1), "label": ch_labels[i][0]} for i in range(5)],
        "output": {
            "width": 1920,
            "height": 1080,
            "fps": 30,
            "filename": f"daodejing-ch{ch:02d}-commentary.mp4",
        },
        "style": {
            "background_color": "#0a1210",
            "motion": motion,
            "subtitle_style": "shadow",
            "subtitle_align": "center",
            "subtitle_font_size": 58,
            "subtitle_color": "#f2f0e8",
            "subtitle_margin_bottom": 80,
            "subtitle_max_width_ratio": 0.94,
            "subtitle_max_lines": 1,
        },
        "watermark": {"text": "观念黑盒"},
        "ambient": {
            "enabled": True,
            "dust_opacity": 0.15,
            "ink_opacity": 0.07,
            "water_opacity": 0.09,
        },
        "tts": make_tts_config(tts_provider),
        "cover": {"enabled": False},
        "youtube": {
            "privacy_status": "private",
            "category_id": "27",
            "channel_url": "https://www.youtube.com/@观念黑盒",
            "tags": ["道德经", "老子", "观念黑盒", meta["yt_tag"], "哲学", f"第{ch}章"],
            "description_intro": meta["desc_intro"],
            "timeline_heading": "📌 章节时间轴（点击时间戳跳转）",
            "timeline": [
                {"scene": sid, "label": ch_labels[i][1]}
                for i, sid in enumerate(
                    ["intro-bridge", "open-1", "open-ext1", "open-ext2", "open-close"]
                )
            ],
            "playlist_id": _series_playlist_id(),
            "made_for_kids": False,
            "default_language": "zh-CN",
            "description_footer": GROWTH_CTA_DESCRIPTION,
        },
        "bilibili": {
            "channel_url": "https://space.bilibili.com/481103225",
            "tid": 124,
            "copyright_original": True,
            "tags": ["道德经", "老子", "观念黑盒", meta["yt_tag"], "哲学", f"第{ch}章"],
            "description_intro": meta["desc_intro"],
            "dynamic": meta["bili_dynamic"],
            "series_id": _series_bilibili_series_id(),
            "season_id": _series_bilibili_season_id(),
            "no_reprint": True,
            "open_elec": False,
            "reuse_youtube_timeline": True,
        },
        "bgm": {
            "enabled": False,
            "tracks": [
                "assets/BGM/Music_fx_relaxing_chinese_flute.wav",
                "assets/BGM/Music_fx_relaxing_chinese_guzheng.wav",
            ],
            "volume": 0.14,
            "crossfade_sec": 5,
            "fade_in_sec": 2.5,
            "fade_out_sec": 5,
            "switch_at_scene": "open-ext1",
        },
        "ending": {
            "enabled": True,
            "image": "assets/avatar.webp",
            "duration_sec": 0,
            "narration": GROWTH_CTA_NARRATION,
        },
        "scenes": scenes,
        "_meta": {"commentary_chars": total_chars},
    }


def write_chapters(
    chapter_meta: dict[int, dict],
    *,
    first_chapter: int,
    max_chapter: int,
    tts_provider: str = "volcengine",
    read_rate: str | None = None,
    long_form: bool = False,
    min_commentary_chars: int | None = None,
    require_review: bool = True,
    scene_images_by_chapter: dict[int, dict[str, str]] | None = None,
    motion: str = "auto",
) -> None:
    if require_review:
        from review_commentary import PASS_SCORE, format_report, review_storyboard_data

    commentary_path = ROOT / "assets/DaoDeJing/daodejing_81_commentary.json"
    data = json.loads(commentary_path.read_text(encoding="utf-8"))
    chapters = data.setdefault("chapters", {})

    for ch, meta in chapter_meta.items():
        sb = build_storyboard(
            ch,
            meta,
            first_chapter=first_chapter,
            max_chapter=max_chapter,
            tts_provider=tts_provider,
            long_form=long_form,
            min_commentary_chars=min_commentary_chars,
            scene_images=(scene_images_by_chapter or {}).get(ch),
            motion=motion,
        )
        chars = sb.pop("_meta", {}).get("commentary_chars", 0)
        out = EXAMPLES / f"storyboard-daodejing-ch{ch:02d}-commentary.json"

        if require_review:
            review = review_storyboard_data(
                sb, chapter=ch, path_label=out.name
            )
            if not review.passed:
                print(format_report(review))
                raise SystemExit(
                    f"第 {ch} 章讲解稿未通过质检（{review.score}/{PASS_SCORE}），"
                    f"已拒绝写入 {out.name}"
                )
            print(f"  质检 PASS {review.score}/100")

        out.write_text(json.dumps(sb, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {out.name} ({chars} chars)")

        default_read = "-15%" if tts_provider.lower() == "edge" else "-18%"
        chapters[str(ch)] = {
            "title": meta["title_short"],
            "mode": "hybrid",
            "tts_provider": tts_provider,
            "read_rate": read_rate or default_read,
            "read_video": f"output/ch{ch:02d}-hybrid/segments/ch{ch:02d}-read.mp4",
            "storyboard": f"examples/storyboard-daodejing-ch{ch:02d}-commentary.json",
            "sections": meta["sections"],
        }

    commentary_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Updated {commentary_path.name}")
