"""道德经五讲 · 单期素材与分镜构建（跨期图片去重）。"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def normalize_asset_path(path: str, project_root: Path | None = None) -> str:
    p = Path(path.strip().replace("\\", "/"))
    if p.is_absolute() and project_root:
        try:
            return p.relative_to(project_root.resolve()).as_posix()
        except ValueError:
            return p.as_posix()
    return p.as_posix().lstrip("./")


def collect_used_images(project_root: Path, before_episode: int) -> set[str]:
    """收集第 1..before_episode-1 期已用配图（matches + 22beats 分镜）。"""
    root = project_root.resolve()
    used: set[str] = set()

    for ep in range(1, before_episode):
        matches_path = root / f"examples/ep{ep:02d}_image_matches.json"
        if matches_path.is_file():
            doc = json.loads(matches_path.read_text(encoding="utf-8"))
            for m in doc.get("matches", []):
                f = m.get("file")
                if f:
                    used.add(normalize_asset_path(f, root))

        storyboard_path = root / f"examples/storyboard-daodejing-ep{ep:02d}-22beats.json"
        if storyboard_path.is_file():
            doc = json.loads(storyboard_path.read_text(encoding="utf-8"))
            for sc in doc.get("scenes", []):
                img = sc.get("image")
                if img:
                    used.add(normalize_asset_path(img, root))

    return used


MASTER_CATALOG_REL = "assets/DaoDeJing/image_catalog.json"


def infer_source_episode(file_path: str) -> int | None:
    m = re.match(r"ep(\d{2})_", Path(file_path).name)
    return int(m.group(1)) if m else None


def master_catalog_path(project_root: Path) -> Path:
    return project_root.resolve() / MASTER_CATALOG_REL


def build_master_image_catalog(project_root: Path) -> Path:
    """合并各期 epNN_image_catalog.json + 磁盘扫描，写入统一 image_catalog.json。"""
    root = project_root.resolve()
    dao = root / "assets/DaoDeJing"
    by_file: dict[str, dict] = {}
    sources: list[str] = []

    for catalog_path in sorted(dao.glob("ep*_image_catalog.json")):
        sources.append(catalog_path.name)
        for img in load_catalog_images(catalog_path, root):
            rel = normalize_asset_path(img["file"], root)
            entry = dict(img)
            entry["file"] = rel
            src_ep = infer_source_episode(rel)
            if src_ep is not None:
                entry.setdefault("source_episode", src_ep)
            by_file.setdefault(rel, entry)

    on_disk_only = 0
    for path in sorted(dao.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
            continue
        rel = path.relative_to(root).as_posix()
        if rel in by_file:
            continue
        on_disk_only += 1
        stem = path.stem
        src_ep = infer_source_episode(path.name)
        entry: dict = {
            "id": stem,
            "file": rel,
            "filename": path.relative_to(dao).as_posix(),
            "description_zh": "",
            "tags": [],
            "source": "disk_scan",
        }
        if src_ep is not None:
            entry["source_episode"] = src_ep
        by_file[rel] = entry

    images = sorted(by_file.values(), key=lambda x: x["file"])
    doc = {
        "meta": {
            "version": 1,
            "sources": sources,
            "image_count": len(images),
            "on_disk_only": on_disk_only,
        },
        "images": images,
    }
    out_path = dao / "image_catalog.json"
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out_path


def ensure_master_catalog(project_root: Path, *, refresh: bool = False) -> Path:
    path = master_catalog_path(project_root)
    if refresh or not path.is_file():
        return build_master_image_catalog(project_root)
    return path


def scan_episode_catalog(episode: int, project_root: Path) -> Path:
    """从 assets/DaoDeJing/epNN_*.jpg 扫描并写入 epNN_image_catalog.json。"""
    root = project_root.resolve()
    dao_dir = root / "assets/DaoDeJing"
    prefix = f"ep{episode:02d}_"
    files = sorted(
        p.relative_to(dao_dir).as_posix()
        for p in dao_dir.rglob("*")
        if p.is_file() and p.name.startswith(prefix) and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
    )
    catalog_path = dao_dir / f"ep{episode:02d}_image_catalog.json"
    catalog = []
    for idx, rel in enumerate(files, start=1):
        name = Path(rel).name
        stem = name.rsplit(".", 1)[0]
        concept = stem.replace(prefix, "", 1) if stem.startswith(prefix) else stem
        catalog.append(
            {
                "id": stem,
                "filename": rel if "/" in rel else name,
                "scene_concept": concept,
                "description": "",
            }
        )
    catalog_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    return catalog_path


def load_catalog_images(catalog_path: Path, project_root: Path) -> list[dict]:
    raw = json.loads(catalog_path.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        items = raw
    else:
        items = raw["images"]
    base = catalog_path.parent
    out: list[dict] = []
    for img in items:
        norm = dict(img)
        if not norm.get("file"):
            filename = norm.get("filename", "")
            if not filename:
                continue
            norm["file"] = str(Path("assets/DaoDeJing") / filename).replace("\\", "/")
        if isinstance(norm.get("id"), int):
            norm["id"] = Path(norm["file"]).stem
        full = project_root / norm["file"]
        if full.is_file():
            out.append(norm)
    return out


def filter_unused_images(images: list[dict], used: set[str], project_root: Path) -> list[dict]:
    unused: list[dict] = []
    for img in images:
        rel = normalize_asset_path(img["file"], project_root)
        if rel not in used:
            unused.append(img)
    return unused


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[。！？!?；\n])", text.strip())
    return [p.strip() for p in parts if p.strip()]


def split_into_n_chunks(text: str, n: int) -> list[str]:
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
    while len(result) < n and len(result) > 1:
        result[-2] += result[-1]
        result.pop()
    if len(result) < n:
        result = [text.strip()]
    return result


def coarse_section_map(coarse: dict) -> dict[str, str]:
    """粗分镜 scene.id → narration。"""
    out: dict[str, str] = {}
    for sc in coarse.get("scenes", []):
        sid = sc.get("id", "")
        text = (sc.get("narration") or "").strip()
        if not text:
            continue
        if sid == "intro":
            parts = split_into_n_chunks(text, 2)
            out["intro-1"] = parts[0]
            out["intro-2"] = parts[1] if len(parts) > 1 else ""
        elif sid == "section-1":
            for i, chunk in enumerate(split_into_n_chunks(text, 5), start=1):
                out[f"s1-{i}"] = chunk
        elif sid == "section-2":
            for i, chunk in enumerate(split_into_n_chunks(text, 4), start=1):
                out[f"s2-{i}"] = chunk
        elif sid == "section-3":
            for i, chunk in enumerate(split_into_n_chunks(text, 3), start=1):
                out[f"s3-{i}"] = chunk
        elif sid == "protocol":
            for i, chunk in enumerate(split_into_n_chunks(text, 3), start=1):
                out[f"protocol-{i}"] = chunk
        elif sid == "closing":
            out["closing-1"] = text
        else:
            out[sid] = text
    return out


def build_22beat_storyboard(
    episode: int,
    coarse: dict,
    beats: list[dict],
    matches: list[dict],
    template: dict,
) -> dict:
    narr = coarse_section_map(coarse)
    match_by = {m["beat_id"]: m for m in matches if m.get("file")}
    scenes: list[dict] = []
    for beat in beats:
        bid = beat["id"]
        text = narr.get(bid, "").strip() or beat.get("summary", "")
        m = match_by.get(bid)
        if not m:
            raise ValueError(f"节拍 {bid} 未配图，请编辑 ep{episode:02d}_image_matches.json 后重试")
        scenes.append(
            {
                "id": bid,
                "narration": text,
                "image": m["file"],
                "pause_after_sec": 0.35,
            }
        )

    ep_tag = f"{episode:02d}"
    out = json.loads(json.dumps(template))  # deep copy
    out["title"] = coarse["title"]
    out["language"] = coarse.get("language", "zh-CN")
    out["chapters"] = coarse.get("chapters", out.get("chapters", []))
    out["scenes"] = scenes

    hook = coarse.get("cover", {}).get("hook", "")
    if isinstance(coarse.get("cover"), dict):
        cover = coarse["cover"]
        out["cover"] = {
            **out.get("cover", {}),
            **cover,
            "image": cover.get("image") or f"assets/covers/daodejing-ep{ep_tag}-cover.jpg",
        }
    out["output"]["filename"] = coarse.get("output", {}).get(
        "filename", f"观念黑盒——道德经五讲之{['一','二','三','四','五'][episode-1]}.mp4"
    )
    out["tts"] = {"voice": "zh-CN-YunxiNeural", "rate": "-5%"}
    if out.get("bilibili"):
        out["bilibili"]["cover_image"] = out["cover"]["image"]
    return out


def print_match_review(matches: list[dict], used_count: int, pool_count: int) -> None:
    print(f"\n配图方案（可用 {pool_count} 张，已排除往期 {used_count} 张）：\n")
    print(f"{'节拍':<14} {'图片':<42} {'分'}")
    print("-" * 62)
    for m in matches:
        fname = Path(m["file"]).name if m.get("file") else "— 未分配 —"
        score = m.get("score", "")
        print(f"{m['beat_id']:<14} {fname:<42} {score}")
    missing = [m for m in matches if not m.get("file")]
    if missing:
        print(f"\n⚠ 有 {len(missing)} 个节拍未配图，请补图或编辑 examples/ep??_image_matches.json")
    else:
        print("\n✓ 22/22 已配图。确认无误后加 --render 出片。")
