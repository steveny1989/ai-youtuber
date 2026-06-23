"""静图缓慢推轨（ffmpeg zoompan）：固定机位 + 匀速左右/上下漂移，增加轻动感。"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from PIL import Image

from .ffmpeg_util import require_ffmpeg

# 画布比输出略大，留出水平/垂直推轨空间（固定缩放，不做 zoom 呼吸）
HEADROOM = 1.10
# 单镜内漂移幅度（0.50 ≈ 慢速横移；过大易显「卡帧感」）
PAN_TRAVEL = 0.50
# x264 推轨片段编码（略高质量，减轻块效应）
MOTION_CRF = 18
MOTION_PRESET = "medium"

MOTION_TYPES = frozenset(
    {
        "static",
        "kenburns_in",
        "kenburns_out",
        "pan_up",
        "pan_down",
        "pan_left",
        "pan_right",
    }
)

# 旧分镜里的 kenburns 缩放 → 慢速左右平移（避免镜间 zoom 来回抖）
_KENBURNS_TO_PAN = {
    "kenburns_in": "pan_left",
    "kenburns_out": "pan_right",
}


def normalize_motion(motion: str) -> str:
    m = motion.strip().lower()
    return _KENBURNS_TO_PAN.get(m, m)


def default_motion_for_scene(scene_id: str) -> str:
    """讲解镜默认：奇偶镜左右缓慢推轨（固定缩放，仅平移）。"""
    if scene_id in ("cover", "ending"):
        return "static"
    if scene_id == "intro-bridge":
        return "pan_right"
    if scene_id == "open-close":
        return "pan_left"
    mapping = {
        "open-1": "pan_left",
        "s1": "pan_left",
        "s2": "pan_right",
        "s3": "pan_left",
        "s4": "pan_right",
        "s5": "pan_left",
        "open-ext1": "pan_right",
        "open-ext2": "pan_left",
        "s-ext2": "pan_right",
    }
    return mapping.get(scene_id, "pan_left")


def resolve_motion(
    scene_motion: str | None,
    *,
    style_motion: str = "auto",
    scene_id: str,
) -> str:
    raw = (scene_motion or "").strip().lower()
    if raw in MOTION_TYPES:
        return normalize_motion(raw)
    style = (style_motion or "auto").strip().lower()
    if style == "static":
        return "static"
    if style == "auto" or not style:
        return default_motion_for_scene(scene_id)
    if style in MOTION_TYPES:
        return normalize_motion(style)
    return default_motion_for_scene(scene_id)


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    c = hex_color.lstrip("#")
    if len(c) != 6:
        return (10, 18, 16)
    return tuple(int(c[i : i + 2], 16) for i in (0, 2, 4))


def _cover_canvas(
    image_path: Path,
    width: int,
    height: int,
    bg_rgb: tuple[int, int, int],
    *,
    headroom: float = HEADROOM,
) -> Image.Image:
    """Cover 裁切到带 zoom 余量的画布（大于输出分辨率）。"""
    cw = max(width, int(width * headroom))
    ch = max(height, int(height * headroom))
    canvas = Image.new("RGB", (cw, ch), bg_rgb)
    src = Image.open(image_path).convert("RGB")
    iw, ih = src.size
    scale = max(cw / iw, ch / ih)
    nw, nh = int(iw * scale), int(ih * scale)
    resized = src.resize((nw, nh), Image.Resampling.LANCZOS)
    x = (cw - nw) // 2
    y = (ch - nh) // 2
    canvas.paste(resized, (x, y))
    return canvas


def _ease_progress(span: int) -> str:
    """zoompan 表达式：ease-in-out，起止更柔，避免线性平移的「顿感」。"""
    return f"(1-cos(PI*on/{span}))/2"


def _zoompan_filter(motion: str, width: int, height: int, fps: int, frames: int) -> str:
    frames = max(frames, 1)
    motion = normalize_motion(motion)
    z_fixed = f"{HEADROOM:.4f}"
    cx = "iw/2-(iw/zoom/2)"
    cy = "ih/2-(ih/zoom/2)"
    span = max(frames - 1, 1)
    ease = _ease_progress(span)
    travel_x = f"({ease})*((iw-iw/zoom)*{PAN_TRAVEL})"
    travel_y = f"({ease})*((ih-ih/zoom)*{PAN_TRAVEL})"

    if motion == "pan_left":
        x = f"max(iw/2-(iw/zoom/2)-{travel_x},0)"
        return f"zoompan=z='{z_fixed}':x='{x}':y='{cy}':d={frames}:s={width}x{height}:fps={fps}"
    if motion == "pan_right":
        x = f"min(iw/2-(iw/zoom/2)+{travel_x},iw-iw/zoom)"
        return f"zoompan=z='{z_fixed}':x='{x}':y='{cy}':d={frames}:s={width}x{height}:fps={fps}"
    if motion == "pan_up":
        y = f"max(ih/2-(ih/zoom/2)-{travel_y},0)"
        return f"zoompan=z='{z_fixed}':x='{cx}':y='{y}':d={frames}:s={width}x{height}:fps={fps}"
    if motion == "pan_down":
        y = f"min(ih/2-(ih/zoom/2)+{travel_y},ih-ih/zoom)"
        return f"zoompan=z='{z_fixed}':x='{cx}':y='{y}':d={frames}:s={width}x{height}:fps={fps}"
    raise ValueError(f"未知 motion: {motion}")


def render_kenburns_video(
    image_path: Path,
    out_path: Path,
    *,
    width: int,
    height: int,
    fps: int,
    duration_sec: float,
    motion: str,
    background_color: str = "#0a1210",
) -> Path:
    """从原图生成带宽缓推轨的无音轨视频（匀速 pan，无 zoom 抖动）。"""
    motion = normalize_motion(motion)
    if motion == "static":
        raise ValueError("render_kenburns_video 不接受 static")

    frames = max(1, int(duration_sec * fps))
    bg_rgb = _hex_to_rgb(background_color)
    canvas = _cover_canvas(image_path, width, height, bg_rgb)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg = require_ffmpeg()
    vf = _zoompan_filter(motion, width, height, fps, frames)

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        canvas.save(tmp_path, format="PNG")
        result = subprocess.run(
            [
                ffmpeg,
                "-y",
                "-loop",
                "1",
                "-framerate",
                str(fps),
                "-i",
                str(tmp_path),
                "-vf",
                vf,
                "-frames:v",
                str(frames),
                "-an",
                "-c:v",
                "libx264",
                "-preset",
                MOTION_PRESET,
                "-crf",
                str(MOTION_CRF),
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
                str(out_path),
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Ken Burns 编码失败:\n{result.stderr[-2000:]}")
    finally:
        tmp_path.unlink(missing_ok=True)

    return out_path
