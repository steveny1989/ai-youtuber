"""全片氛围层：浮尘光束 / 水墨缘晕 / 水面粼光（黑底素材 + colorkey 叠在最上层）。"""

from __future__ import annotations

import math
import random
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from .ffmpeg_util import require_ffmpeg
from .models import AmbientConfig, Storyboard

LOOP_SEC = 8.0
LOOP_FPS = 30
LOOP_VERSION = 5

# colorkey 容差（screen 混合前抠黑底）
_COLORKEY_SIM = 0.18
_COLORKEY_BLEND = 0.08

PRESET_DUST = "dust_light"
PRESET_INK = "ink_mist"
PRESET_WATER = "water_shimmer"

WATER_THEME_CHAPTERS: frozenset[int] = frozenset(
    {8, 10, 28, 43, 55, 61, 66, 76, 78}
)
WATER_SHIMMER_SCENES: frozenset[str] = frozenset({"s2", "open-ext2"})
SKIP_AMBIENT_SCENES: frozenset[str] = frozenset({"cover", "ending"})


@dataclass(frozen=True)
class AmbientLayer:
    preset: str
    opacity: float


def parse_chapter_number(storyboard: Storyboard) -> int | None:
    m = re.search(r"第(\d+)章", storyboard.title)
    if m:
        return int(m.group(1))
    m = re.search(r"ch(\d+)", storyboard.output.filename, re.I)
    if m:
        return int(m.group(1))
    return None


def resolve_ambient_layer(
    storyboard: Storyboard,
    scene_id: str,
    *,
    config: AmbientConfig | None = None,
) -> AmbientLayer | None:
    cfg = config or AmbientConfig()
    if not cfg.enabled or scene_id in SKIP_AMBIENT_SCENES:
        return None

    ch = parse_chapter_number(storyboard)
    if (
        ch is not None
        and ch in (cfg.water_chapters or WATER_THEME_CHAPTERS)
        and scene_id in WATER_SHIMMER_SCENES
    ):
        return AmbientLayer(PRESET_WATER, cfg.water_opacity)

    if scene_id in ("intro-bridge", "open-close"):
        return AmbientLayer(PRESET_INK, cfg.ink_opacity)

    if scene_id in {
        "open-1",
        "s1",
        "s2",
        "s3",
        "s4",
        "s5",
        "open-ext1",
        "open-ext2",
        "s-ext2",
    }:
        return AmbientLayer(PRESET_DUST, cfg.dust_opacity)

    return None


def ambient_loop_path(project_root: Path, preset: str, width: int, height: int) -> Path:
    rel = (
        Path("assets/ambient/loops")
        / f"{preset}_{width}x{height}_v{LOOP_VERSION}.mp4"
    )
    return (project_root / rel).resolve()


def ensure_ambient_loops(project_root: Path, width: int, height: int) -> None:
    loops_dir = project_root / "assets/ambient/loops"
    loops_dir.mkdir(parents=True, exist_ok=True)
    for old in loops_dir.glob("*.webm"):
        old.unlink(missing_ok=True)
    for old in loops_dir.glob(f"*_{width}x{height}.mp4"):
        if f"_v{LOOP_VERSION}" not in old.name:
            old.unlink(missing_ok=True)
    for preset in (PRESET_DUST, PRESET_INK, PRESET_WATER):
        path = ambient_loop_path(project_root, preset, width, height)
        if not path.is_file() or path.stat().st_size < 5000:
            _encode_loop(path, preset=preset, width=width, height=height)


def _encode_loop(out_path: Path, *, preset: str, width: int, height: int) -> None:
    frames = max(1, int(LOOP_SEC * LOOP_FPS))
    ffmpeg = require_ffmpeg()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        for i in range(frames):
            frame = _render_loop_frame(preset, width, height, i, frames)
            # 黑底 RGB（透明区=黑），供 colorkey 抠图
            rgb = Image.new("RGB", frame.size, (0, 0, 0))
            rgb.paste(frame, mask=frame.split()[3])
            rgb.save(tmp_dir / f"frame_{i:04d}.png")

        result = subprocess.run(
            [
                ffmpeg,
                "-y",
                "-framerate",
                str(LOOP_FPS),
                "-i",
                str(tmp_dir / "frame_%04d.png"),
                "-c:v",
                "libx264",
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
            raise RuntimeError(f"氛围循环编码失败 ({preset}):\n{result.stderr[-2000:]}")


def _render_loop_frame(
    preset: str,
    width: int,
    height: int,
    frame_idx: int,
    total_frames: int,
) -> Image.Image:
    if preset == PRESET_DUST:
        return _frame_dust(width, height, frame_idx, total_frames, seed=42)
    if preset == PRESET_INK:
        return _frame_ink_mist(width, height, frame_idx, total_frames)
    if preset == PRESET_WATER:
        return _frame_water_shimmer(width, height, frame_idx, total_frames)
    raise ValueError(f"未知氛围 preset: {preset}")


def _frame_dust(
    width: int,
    height: int,
    frame_idx: int,
    total_frames: int,
    *,
    seed: int,
) -> Image.Image:
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    t = frame_idx / max(total_frames, 1)

    # 斜向光束（慢漂移）
    beam_rng = random.Random(seed + 9001)
    for bi in range(3):
        br = random.Random(seed + bi * 4441)
        cx = (br.uniform(-0.2, 1.2) * width + math.sin(2 * math.pi * (t + bi * 0.31)) * width * 0.04) % width
        cy = br.uniform(-0.1, 0.85) * height
        bw = br.uniform(width * 0.08, width * 0.16)
        bh = height * 1.25
        alpha = int(38 + 22 * math.sin(2 * math.pi * (t * 0.55 + bi * 0.2)))
        draw.ellipse((cx - bw, cy - bh * 0.5, cx + bw, cy + bh * 0.5), fill=(255, 245, 220, alpha))

    count = max(90, (width * height) // 12000)
    for i in range(count):
        r_rng = random.Random(seed + i * 9973)
        x0 = r_rng.uniform(0, width)
        y0 = r_rng.uniform(0, height)
        vx = r_rng.uniform(-18, 18)
        vy = r_rng.uniform(-10, 8)
        x = (x0 + vx * t * LOOP_SEC) % width
        y = (y0 + vy * t * LOOP_SEC) % height
        radius = r_rng.uniform(2.5, 6.5)
        twinkle = 0.5 + 0.5 * math.sin(2 * math.pi * (t * 0.7 + i * 0.13))
        alpha = int(255 * twinkle)
        draw.ellipse(
            (x - radius, y - radius, x + radius, y + radius),
            fill=(255, 248, 230, alpha),
        )
    return img.filter(ImageFilter.GaussianBlur(radius=1.0))


def _frame_ink_mist(
    width: int,
    height: int,
    frame_idx: int,
    total_frames: int,
) -> Image.Image:
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    t = frame_idx / max(total_frames, 1)
    drift = math.sin(2 * math.pi * t) * width * 0.018
    patches = [
        (int(-width * 0.10 + drift), int(height * 0.50), int(width * 0.62), height + 50, 235),
        (int(width * 0.40 - drift * 0.6), int(-height * 0.10), width + 50, int(height * 0.50), 220),
        (int(-width * 0.08 - drift * 0.4), int(-height * 0.12), int(width * 0.46), int(height * 0.40), 200),
        (int(width * 0.52 + drift * 0.3), int(height * 0.58), width + 40, height + 40, 215),
    ]
    for x0, y0, x1, y1, alpha in patches:
        draw.ellipse((x0, y0, x1, y1), fill=(220, 228, 215, alpha))
    return img.filter(ImageFilter.GaussianBlur(radius=width // 120 + 12))


def _frame_water_shimmer(
    width: int,
    height: int,
    frame_idx: int,
    total_frames: int,
) -> Image.Image:
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    t = frame_idx / max(total_frames, 1)
    band_top = int(height * 0.78)
    lines = 20
    for i in range(lines):
        y = band_top + i * max(2, (height - band_top) // lines)
        phase = t * 2 * math.pi + i * 0.55
        amp = 5 + (i % 3)
        points: list[tuple[float, float]] = []
        x = 0.0
        while x <= width + 20:
            yy = y + math.sin(phase + x * 0.010) * amp
            points.append((x, yy))
            x += 22
        if len(points) >= 2:
            alpha = 200 + (i % 5) * 11
            draw.line(points, fill=(220, 250, 245, min(alpha, 255)), width=3)
    return img.filter(ImageFilter.GaussianBlur(radius=0.9))


def _screen_blend_filter(
    base_label: str,
    ambient_label: str,
    *,
    opacity: float,
    out_label: str,
) -> str:
    alpha = min(max(opacity, 0.02), 1.0)
    return (
        f"[{base_label}][{ambient_label}]blend=all_mode=screen:all_opacity={alpha:.4f},"
        f"format=yuv420p[{out_label}]"
    )


def composite_ambient_on_video(
    src_video: Path,
    dst_video: Path,
    *,
    project_root: Path,
    preset: str,
    opacity: float,
    duration_sec: float,
    width: int,
    height: int,
    fps: int = 30,
) -> None:
    """推轨成片后单独烘焙氛围（screen 混合，避免 overlay+低 alpha 不可见）。"""
    ensure_ambient_loops(project_root, width, height)
    loop = ambient_loop_path(project_root, preset, width, height)
    ffmpeg = require_ffmpeg()
    amb = "ambk"
    filt = (
        f"[1:v]trim=duration={duration_sec:.3f},setpts=PTS-STARTPTS,"
        f"fps={fps},scale={width}:{height},"
        f"colorkey=0x000000:{_COLORKEY_SIM}:{_COLORKEY_BLEND}[{amb}];"
        + _screen_blend_filter("0:v", amb, opacity=opacity, out_label="vout")
    )
    result = subprocess.run(
        [
            ffmpeg,
            "-y",
            "-i",
            str(src_video),
            "-stream_loop",
            "-1",
            "-i",
            str(loop),
            "-filter_complex",
            filt,
            "-map",
            "[vout]",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(dst_video),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"氛围烘焙失败 ({preset}):\n{result.stderr[-2000:]}")


def blend_ambient_filter(
    base_label: str,
    ambient_input: int,
    *,
    duration_sec: float,
    opacity: float,
    out_label: str = "vamb",
) -> tuple[str, str]:
    """抠除黑底后 screen 混合到背景之上。"""
    amb = f"amb{ambient_input}"
    filt = (
        f"[{ambient_input}:v]trim=duration={duration_sec:.3f},setpts=PTS-STARTPTS,"
        f"colorkey=0x000000:{_COLORKEY_SIM}:{_COLORKEY_BLEND}[{amb}];"
        + _screen_blend_filter(base_label, amb, opacity=opacity, out_label=out_label)
    )
    return filt, out_label
