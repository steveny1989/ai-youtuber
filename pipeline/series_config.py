"""单章精解系列：八十一讲播放列表 / B 站视频列表配置与投稿登记。"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

SERIES_CONFIG_REL = "assets/DaoDeJing/series_daodejing_81.json"
REGISTRY_REL = "output/series_daodejing_81_registry.jsonl"


@dataclass
class Daodejing81Series:
    youtube_playlist_id: str = ""
    bilibili_series_id: int = 0
    bilibili_season_id: int = 0
    title_zh: str = "道德经八十一讲"

    @property
    def youtube_configured(self) -> bool:
        return bool(self.youtube_playlist_id.strip())

    @property
    def bilibili_series_configured(self) -> bool:
        return self.bilibili_series_id > 0


def _project_root(project_root: Path | None) -> Path:
    if project_root is not None:
        return project_root.resolve()
    return Path(__file__).resolve().parents[1]


def config_path(project_root: Path | None = None) -> Path:
    return _project_root(project_root) / SERIES_CONFIG_REL


def registry_path(project_root: Path | None = None) -> Path:
    return _project_root(project_root) / REGISTRY_REL


def chapter_from_path(path: Path | str) -> int | None:
    m = re.search(r"ch(\d{1,2})", str(path), re.I)
    if not m:
        return None
    return int(m.group(1))


def load_daodejing_81_series(project_root: Path | None = None) -> Daodejing81Series:
    root = _project_root(project_root)
    data: dict = {}
    cfg_file = config_path(root)
    if cfg_file.is_file():
        data = json.loads(cfg_file.read_text(encoding="utf-8"))

    yt = (
        os.environ.get("YOUTUBE_PLAYLIST_DAODEJING_81", "").strip()
        or str(data.get("youtube_playlist_id", "")).strip()
    )
    series_raw = os.environ.get("BILIBILI_SERIES_DAODEJING_81", "").strip()
    if series_raw:
        bili_series = int(series_raw)
    else:
        bili_series = int(data.get("bilibili_series_id") or 0)
    season_raw = os.environ.get("BILIBILI_SEASON_DAODEJING_81", "").strip()
    if season_raw:
        bili_season = int(season_raw)
    else:
        bili_season = int(data.get("bilibili_season_id") or 0)

    return Daodejing81Series(
        youtube_playlist_id=yt,
        bilibili_series_id=bili_series,
        bilibili_season_id=bili_season,
        title_zh=str(data.get("title_zh") or "道德经八十一讲"),
    )


def resolve_youtube_playlist_id(
    storyboard_playlist_id: str,
    project_root: Path | None = None,
) -> str:
    explicit = (storyboard_playlist_id or "").strip()
    if explicit:
        return explicit
    return load_daodejing_81_series(project_root).youtube_playlist_id


def resolve_bilibili_series_id(
    storyboard_series_id: int,
    project_root: Path | None = None,
) -> int:
    if storyboard_series_id > 0:
        return storyboard_series_id
    return load_daodejing_81_series(project_root).bilibili_series_id


def append_registry(
    *,
    chapter: int,
    platform: str,
    project_root: Path | None = None,
    **fields: str | int,
) -> None:
    root = _project_root(project_root)
    path = registry_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "chapter": chapter,
        "platform": platform,
        "ts": datetime.now(timezone.utc).isoformat(),
        **fields,
    }
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_registry(project_root: Path | None = None) -> list[dict]:
    path = registry_path(_project_root(project_root))
    if not path.is_file():
        return []
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def registry_by_chapter(
    project_root: Path | None = None,
) -> dict[int, dict[str, dict]]:
    """每章合并 youtube / bilibili 登记（后写覆盖先写）。"""
    out: dict[int, dict[str, dict]] = {}
    for row in load_registry(project_root):
        ch = int(row.get("chapter", 0))
        if ch <= 0:
            continue
        plat = str(row.get("platform", ""))
        out.setdefault(ch, {})[plat] = row
    return out


def patch_storyboard_json(data: dict, series: Daodejing81Series) -> bool:
    changed = False
    yt = data.setdefault("youtube", {})
    if series.youtube_playlist_id and yt.get("playlist_id") != series.youtube_playlist_id:
        yt["playlist_id"] = series.youtube_playlist_id
        changed = True
    bili = data.setdefault("bilibili", {})
    if series.bilibili_series_id and bili.get("series_id") != series.bilibili_series_id:
        bili["series_id"] = series.bilibili_series_id
        changed = True
    if series.bilibili_season_id and bili.get("season_id") != series.bilibili_season_id:
        bili["season_id"] = series.bilibili_season_id
        changed = True
    return changed


def commentary_storyboard_paths(project_root: Path | None = None) -> list[Path]:
    root = _project_root(project_root)
    paths = sorted(root.glob("examples/storyboard-daodejing-ch*-commentary.json"))
    return [p for p in paths if chapter_from_path(p) is not None]


def save_daodejing_81_series(
    series: Daodejing81Series,
    project_root: Path | None = None,
) -> Path:
    """把 playlist_id / series_id 写回 series_daodejing_81.json（保留其它字段）。"""
    root = _project_root(project_root)
    path = config_path(root)
    data: dict = {}
    if path.is_file():
        data = json.loads(path.read_text(encoding="utf-8"))
    if series.youtube_playlist_id:
        data["youtube_playlist_id"] = series.youtube_playlist_id
    if series.bilibili_series_id:
        data["bilibili_series_id"] = series.bilibili_series_id
    if series.bilibili_season_id:
        data["bilibili_season_id"] = series.bilibili_season_id
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path
