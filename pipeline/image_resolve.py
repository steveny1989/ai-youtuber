"""配图路径解析：分镜旧名 → assets/DaoDeJing 磁盘文件。"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}

# 旧 ep/ch 系列 id → 磁盘文件名（无 ch 前缀的通用图）
LEGACY_ID_MAP: dict[str, str] = {
    "ch46_03_ancient_horse": "Ancient Horse - 通用.jpg",
    "ch48_03_peeling_lacquer": "Peeling Lacquer - 通用.jpg",
    "ch48_04_straw_rope_cut": "Straw Rope Cut - 通用.jpg",
    "ch49_02_communal_stone_mill": "Communal Stone Mill - 通用.jpg",
    "ch49_03_murky_pottery_water": "Murky Pottery Water - 通用.jpg",
    "ch50_03_vine_shield": "Vine Shield - 通用.jpg",
    "ch50_04_stone_oil_lamp": "Stone Oil Lamp - 通用.jpg",
    "ch47_02_wooden_basin_stars": "Wooden Basin Stars - 通用.jpg",
    "ch47_03_paper_window_moon": "Paper Window Moon - 通用.jpg",
    "ep02_49_bowing_official_shadow": "Bowing Official Shad - Ch02.jpg",
}


def _norm(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[\s_\-，、；;：:]+", "", s)
    return s


def _tokens(s: str) -> list[str]:
    s = re.sub(r"[_\-]+", " ", s.lower())
    parts = re.split(r"[\s,，、；;：:]+", s)
    out: list[str] = []
    for p in parts:
        p = p.strip()
        if len(p) >= 2 and p not in {"ch", "jpg", "png", "jpeg", "webp", "通用"}:
            out.append(p)
    for m in re.finditer(r"[\u4e00-\u9fff]{2,}", s):
        out.append(m.group())
    return out


@dataclass
class ImagePathIndex:
    dao_dir: Path
    by_lower: dict[str, Path] = field(default_factory=dict)
    by_plc: dict[int, Path] = field(default_factory=dict)
    by_wat: dict[int, Path] = field(default_factory=dict)
    by_zh_ch: dict[tuple[str, int], Path] = field(default_factory=dict)
    by_stem_norm: dict[str, Path] = field(default_factory=dict)
    all_files: list[Path] = field(default_factory=list)

    @classmethod
    def build(cls, project_root: Path) -> ImagePathIndex:
        dao = project_root / "assets" / "DaoDeJing"
        idx = cls(dao_dir=dao)
        if not dao.is_dir():
            return idx
        for f in sorted(dao.iterdir()):
            if not f.is_file() or f.suffix.lower() not in IMAGE_EXTS:
                continue
            idx.all_files.append(f)
            idx.by_lower[f.name.lower()] = f
            stem = f.stem
            idx.by_stem_norm[_norm(stem)] = f

            m = re.match(r"^plc\s*(\d+)", stem, re.I)
            if m:
                idx.by_plc[int(m.group(1))] = f
                continue
            m = re.match(r"^wat\s*(\d+)", stem, re.I)
            if m:
                idx.by_wat[int(m.group(1))] = f
                continue

            m = re.match(r"^(.+?)\s*-\s*ch(\d+)\s*-\s*通用", stem, re.I)
            if m:
                zh = m.group(1).strip().lower()
                ch = int(m.group(2))
                idx.by_zh_ch[(zh, ch)] = f
                idx.by_zh_ch[(_norm(zh), ch)] = f
                continue

            m = re.match(r"^(.+?)\s*-\s*Ch(\d+)", stem, re.I)
            if m:
                zh = m.group(1).strip().lower()
                ch = int(m.group(2))
                idx.by_zh_ch[(zh, ch)] = f
                idx.by_zh_ch[(_norm(zh), ch)] = f

        return idx


_INDEX_CACHE: dict[str, ImagePathIndex] = {}


def get_index(project_root: Path) -> ImagePathIndex:
    key = str(project_root.resolve())
    if key not in _INDEX_CACHE:
        _INDEX_CACHE[key] = ImagePathIndex.build(project_root)
    return _INDEX_CACHE[key]


def clear_index_cache() -> None:
    _INDEX_CACHE.clear()


def _rel(path: Path, project_root: Path) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def resolve_daodejing_image(
    path_str: str | None,
    project_root: Path,
    *,
    index: ImagePathIndex | None = None,
) -> Path | None:
    """将分镜 image 路径解析为磁盘绝对路径；失败返回 None。"""
    if not path_str or "avatar" in path_str:
        return None

    root = project_root.resolve()
    idx = index or get_index(root)

    p = Path(path_str)
    if p.is_absolute():
        return p if p.is_file() else None

    direct = (root / path_str).resolve()
    if direct.is_file():
        return direct

    name = p.name
    lower = name.lower()
    if lower in idx.by_lower:
        return idx.by_lower[lower]

    stem = p.stem
    stem_lower = stem.lower()

    # plc_05_cooking_fish_tripod.jpg
    m = re.match(r"plc_(\d+)", stem_lower)
    if m:
        hit = idx.by_plc.get(int(m.group(1)))
        if hit:
            return hit

    m = re.match(r"wat_(\d+)", stem_lower)
    if m:
        hit = idx.by_wat.get(int(m.group(1)))
        if hit:
            return hit

    # ch46_03_ancient_horse
    if stem_lower in LEGACY_ID_MAP:
        hit = idx.by_lower.get(LEGACY_ID_MAP[stem_lower].lower())
        if hit:
            return hit

    m = re.match(r"ch\d+_\d+_(.+)", stem_lower)
    if m:
        tail = m.group(1).replace("_", " ")
        best = _fuzzy_by_tokens(idx, _tokens(tail))
        if best:
            return best

    # 中文/英文 - Ch62.jpg / - Ch01.png
    m = re.match(r"^(.+?)\s*-\s*Ch(\d+)(?:\s*\(\d+\))?$", stem, re.I)
    if m:
        label = m.group(1).strip()
        ch = int(m.group(2))
        for key in (label.lower(), _norm(label)):
            hit = idx.by_zh_ch.get((key, ch))
            if hit:
                return hit
        # 无精确章号时：同标签任意章（如 Ch01 变体）
        for (zh, _), fp in idx.by_zh_ch.items():
            if zh == label.lower() or zh == _norm(label):
                return fp
        best = _fuzzy_by_tokens(idx, _tokens(label))
        if best:
            return best

    # 英文 Title Case - Ch02（无 通用 后缀的旧分镜）
    best = _fuzzy_by_tokens(idx, _tokens(stem))
    if best:
        return best

    sn = _norm(stem)
    if sn in idx.by_stem_norm:
        return idx.by_stem_norm[sn]

    return None


def _fuzzy_by_tokens(idx: ImagePathIndex, need: list[str]) -> Path | None:
    if not need:
        return None
    best: Path | None = None
    best_score = 0
    for f in idx.all_files:
        hay = _tokens(f.stem)
        hay_norm = _norm(f.stem)
        score = sum(1 for t in need if t in hay or t in hay_norm)
        if score > best_score and score >= max(1, len(need) // 2 + 1):
            best_score = score
            best = f
    return best


def align_image_path(
    path_str: str,
    project_root: Path,
    *,
    index: ImagePathIndex | None = None,
) -> tuple[str | None, Path | None]:
    """返回 (canonical assets/... 相对路径, 绝对路径)；无法解析则 (None, None)。"""
    resolved = resolve_daodejing_image(path_str, project_root, index=index)
    if not resolved:
        return None, None
    return _rel(resolved, project_root), resolved


def find_missing_storyboard_images(
    storyboard_path: Path,
    project_root: Path | None = None,
) -> list[tuple[str, str]]:
    """返回 [(scene_id, image_path), ...] 无法解析的镜。"""
    root = (project_root or storyboard_path.resolve().parent.parent).resolve()
    import json

    data = json.loads(storyboard_path.read_text(encoding="utf-8"))
    idx = get_index(root)
    missing: list[tuple[str, str]] = []
    for s in data.get("scenes", []):
        img = s.get("image", "")
        if not img or "avatar" in img:
            continue
        if resolve_daodejing_image(img, root, index=idx) is None:
            missing.append((s.get("id", "?"), img))
    return missing


class MissingStoryboardImagesError(RuntimeError):
    """分镜配图无法解析；需修正路径或显式 --allow-missing-images。"""

    def __init__(self, storyboard_path: Path, missing: list[tuple[str, str]]) -> None:
        self.storyboard_path = storyboard_path
        self.missing = missing
        lines = [
            f"分镜 {storyboard_path.name} 有 {len(missing)} 镜配图找不到文件：",
        ]
        for sid, img in missing[:12]:
            lines.append(f"  {sid}: {img}")
        if len(missing) > 12:
            lines.append(f"  … 另有 {len(missing) - 12} 镜")
        lines.append(
            "请运行 python3 scripts/align_storyboard_image_paths.py 对齐路径，"
            "或确认后加 --allow-missing-images（将用黑底，不推荐）。"
        )
        super().__init__("\n".join(lines))
