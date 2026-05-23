from __future__ import annotations

import json
import platform
import shutil
import subprocess
from pathlib import Path


def require_ffmpeg() -> str:
    path = shutil.which("ffmpeg")
    if not path:
        raise RuntimeError(
            "未找到 ffmpeg。请先安装：macOS 可运行 `brew install ffmpeg`"
        )
    return path


def create_silent_audio(duration_sec: float, out_path: Path) -> Path:
    require_ffmpeg()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            require_ffmpeg(),
            "-y",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=44100:cl=stereo",
            "-t",
            str(duration_sec),
            "-c:a",
            "libmp3lame",
            "-q:a",
            "9",
            str(out_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return out_path


def probe_duration_sec(media_path: Path) -> float:
    require_ffmpeg()
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            str(media_path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    data = json.loads(result.stdout)
    return float(data["format"]["duration"])


def find_weibei_font() -> str | None:
    """魏碑-简（Weibei SC），与片尾 avatar.webp 内嵌标题字一致。"""
    explicit = [
        Path("/System/Library/AssetsV2/com_apple_MobileAsset_Font8")
        / "c745f84f5eb15b1f594d3769dc86146fccee61ff.asset"
        / "AssetData"
        / "WeibeiSC-Bold.otf",
        Path("assets/fonts/WeibeiSC-Bold.otf"),
        Path("assets/fonts/WeibeiSC.otf"),
    ]
    for path in explicit:
        if path.exists():
            return str(path.resolve())

    search_roots = [
        Path("/System/Library/AssetsV2/com_apple_MobileAsset_Font8"),
        Path("/Library/Fonts"),
        Path("/System/Library/Fonts"),
        Path.home() / "Library/Fonts",
    ]
    patterns = ("WeibeiSC*.otf", "WeibeiTC*.otf", "*魏碑*.ttf", "*魏碑*.otf", "*Weibei*.ttf")
    for root in search_roots:
        if not root.exists():
            continue
        for pattern in patterns:
            for path in root.rglob(pattern):
                return str(path.resolve())
    return None


def default_font_path() -> str | None:
    """优先魏碑（片尾同款），再回退到系统中文字体。"""
    weibei = find_weibei_font()
    if weibei:
        return weibei

    candidates = [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/Supplemental/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    ]
    for path in candidates:
        if Path(path).exists():
            return path
    if platform.system() == "Darwin":
        return "/System/Library/Fonts/STHeiti Light.ttc"
    return None


def escape_drawtext(text: str) -> str:
    """Escape text for ffmpeg drawtext filter."""
    return (
        text.replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "\\'")
        .replace("%", "\\%")
        .replace("\n", " ")
    )
