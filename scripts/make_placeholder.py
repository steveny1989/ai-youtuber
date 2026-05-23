#!/usr/bin/env python3
"""生成占位图：正文底色、首页、章节图（色调与 placeholder-home 一致）。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.brand import (  # noqa: E402
    BACKGROUND_COLOR,
    DEFAULT_CHAPTER_PLACEHOLDERS,
    FONT_PATH,
    HOOK_BG,
    HOOK_HOME_ZONE_LEFT_RATIO,
    HOOK_HOME_ZONE_WIDTH_RATIO,
    PALETTE_ACCENT,
    PALETTE_BG,
    PALETTE_MID,
    PLACEHOLDER_CHAPTER_DIR,
    PLACEHOLDER_HOME_IMAGE,
    PLACEHOLDER_IMAGE,
    SUBTITLE_COLOR,
    WATERMARK_COLOR,
    WATERMARK_FONT_SIZE,
    WATERMARK_IMAGE,
    WATERMARK_KEY_LIGHT_BG,
    WATERMARK_LABEL_GAP,
    WATERMARK_OPACITY,
    WATERMARK_SEAL_ONLY,
    WATERMARK_TEXT,
    WATERMARK_WIDTH_RATIO,
)
from pipeline.ffmpeg_util import default_font_path  # noqa: E402
from pipeline.frame import (  # noqa: E402
    _draw_text_shadow,
    _hex_to_rgb,
    _wrap_text,
    fit_hook_background,
    load_brand_logo,
    render_seal_with_label,
)

WIDTH, HEIGHT = 1920, 1080


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    path = FONT_PATH or default_font_path()
    if path and Path(path).exists():
        try:
            return ImageFont.truetype(path, size=size)
        except OSError:
            pass
    return ImageFont.load_default()


def _tone_gradient_canvas() -> Image.Image:
    """与首页左侧暗区同系的渐变底（无宝盒）。"""
    base = _hex_to_rgb(PALETTE_BG)
    mid = _hex_to_rgb(PALETTE_MID)
    accent = _hex_to_rgb(PALETTE_ACCENT)
    img = Image.new("RGB", (WIDTH, HEIGHT), base)
    px = img.load()
    for y in range(HEIGHT):
        ty = y / max(HEIGHT - 1, 1)
        for x in range(WIDTH):
            tx = x / max(WIDTH - 1, 1)
            r = int(base[0] * (1 - ty) * (1 - tx * 0.35) + mid[0] * ty * 0.45 + accent[0] * tx * 0.12)
            g = int(base[1] * (1 - ty) * (1 - tx * 0.35) + mid[1] * ty * 0.45 + accent[1] * tx * 0.12)
            b = int(base[2] * (1 - ty) * (1 - tx * 0.35) + mid[2] * ty * 0.45 + accent[2] * tx * 0.12)
            px[x, y] = (min(r, 40), min(g, 48), min(b, 44))
    return img


def _home_title_zone() -> tuple[int, int]:
    zone_left = int(WIDTH * HOOK_HOME_ZONE_LEFT_RATIO)
    zone_width = int(WIDTH * HOOK_HOME_ZONE_WIDTH_RATIO)
    return zone_left, zone_width


def _center_in_zone(x_left: int, zone_width: int, block_width: float) -> int:
    return int(x_left + (zone_width - block_width) / 2)


def _load_hook_base() -> Image.Image:
    hook_path = ROOT / HOOK_BG
    if not hook_path.exists():
        return _tone_gradient_canvas()
    return fit_hook_background(
        Image.open(hook_path),
        WIDTH,
        HEIGHT,
        _hex_to_rgb(BACKGROUND_COLOR),
    )


def _draw_brand_row(base: Image.Image, y: int, zone_left: int, zone_width: int) -> int:
    logo_path = ROOT / WATERMARK_IMAGE
    if not logo_path.exists() or not WATERMARK_TEXT.strip():
        return y
    draw = ImageDraw.Draw(base)
    seal_max = max(32, int(WIDTH * WATERMARK_WIDTH_RATIO))
    brand_font = max(WATERMARK_FONT_SIZE + 8, 40)
    seal = load_brand_logo(
        logo_path,
        seal_only=WATERMARK_SEAL_ONLY,
        key_light_bg=WATERMARK_KEY_LIGHT_BG,
    )
    seal.thumbnail((seal_max, seal_max), Image.Resampling.LANCZOS)
    label_font = _load_font(brand_font)
    label = WATERMARK_TEXT.strip()
    text_w = draw.textlength(label, font=label_font)
    brand_w = seal.width + WATERMARK_LABEL_GAP + text_w
    brand_x = _center_in_zone(zone_left, zone_width, brand_w)
    _, brand_h = render_seal_with_label(
        base,
        logo_path,
        label,
        brand_x,
        y,
        seal_max_px=seal_max,
        label_font_size=brand_font,
        font_path=FONT_PATH or default_font_path(),
        font_index=0,
        label_color=WATERMARK_COLOR,
        opacity=WATERMARK_OPACITY,
        seal_only=WATERMARK_SEAL_ONLY,
        key_light_bg=WATERMARK_KEY_LIGHT_BG,
        gap=WATERMARK_LABEL_GAP,
    )
    return y + brand_h + 48


def _draw_zone_title(
    base: Image.Image,
    text: str,
    y: int,
    zone_left: int,
    zone_width: int,
    *,
    font_size: int,
    hint: str | None = None,
) -> int:
    draw = ImageDraw.Draw(base)
    title_font = _load_font(font_size)
    fill = _hex_to_rgb(SUBTITLE_COLOR)
    lines = _wrap_text(draw, text.strip(), title_font, zone_width)
    line_height = int(font_size * 1.2)
    for i, line in enumerate(lines):
        if not line:
            continue
        tw = draw.textlength(line, font=title_font)
        x = _center_in_zone(zone_left, zone_width, tw)
        yy = y + i * line_height
        _draw_text_shadow(draw, (x, yy), line, title_font, fill)
    y = y + len(lines) * line_height + (28 if hint else 0)
    if hint:
        hint_font = _load_font(26)
        hw = draw.textlength(hint, font=hint_font)
        hx = _center_in_zone(zone_left, zone_width, hw)
        draw.text((hx, y), hint, font=hint_font, fill=(90, 98, 94))
        y += 40
    return y


def _body_frame(out_path: Path) -> Path:
    base = _tone_gradient_canvas()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    base.save(out_path, format="JPEG", quality=92)
    return out_path


def _home_frame(out_path: Path, title: str) -> Path:
    base = _load_hook_base()
    zone_left, zone_width = _home_title_zone()
    y_cursor = _draw_brand_row(base, 96, zone_left, zone_width)
    _draw_zone_title(
        base,
        title,
        y_cursor,
        zone_left,
        zone_width,
        font_size=52,
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    base.save(out_path, format="JPEG", quality=92)
    return out_path


def _chapter_frame(out_path: Path, chapter_label: str) -> Path:
    base = _load_hook_base()
    zone_left, zone_width = _home_title_zone()
    y_cursor = _draw_brand_row(base, 120, zone_left, zone_width)
    _draw_zone_title(
        base,
        chapter_label,
        y_cursor,
        zone_left,
        zone_width,
        font_size=72,
        hint="章节镜头 · 可在分镜 JSON 中替换 image",
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    base.save(out_path, format="JPEG", quality=92)
    return out_path


def _default_title() -> str:
    example = ROOT / "examples/storyboard.example.json"
    if example.exists():
        data = json.loads(example.read_text(encoding="utf-8"))
        if title := data.get("title"):
            return str(title)
    return "视频标题"


def main() -> None:
    parser = argparse.ArgumentParser(description="生成 placeholder / 章节占位图")
    parser.add_argument(
        "--title",
        default=None,
        help="首页主标题（默认读取 examples/storyboard.example.json）",
    )
    parser.add_argument(
        "--chapter",
        action="append",
        metavar="LABEL:FILE",
        help='额外章节图，如 --chapter "第四章:chapter-04.jpg"',
    )
    parser.add_argument("--chapters-only", action="store_true", help="只生成章节图")
    parser.add_argument("--no-default-chapters", action="store_true")
    args = parser.parse_args()
    title = args.title or _default_title()

    assets = ROOT / "assets"
    chapters_dir = assets / Path(PLACEHOLDER_CHAPTER_DIR).name
    chapters_dir.mkdir(parents=True, exist_ok=True)

    generated: list[Path] = []

    if not args.chapters_only:
        generated.append(_body_frame(assets / Path(PLACEHOLDER_IMAGE).name))
        generated.append(_home_frame(assets / Path(PLACEHOLDER_HOME_IMAGE).name, title))

    if not args.no_default_chapters:
        for filename, label in DEFAULT_CHAPTER_PLACEHOLDERS:
            path = chapters_dir / filename
            generated.append(_chapter_frame(path, label))

    for spec in args.chapter or []:
        if ":" in spec:
            label, filename = spec.split(":", 1)
        else:
            label, filename = spec, f"chapter-{spec}.jpg"
        generated.append(_chapter_frame(chapters_dir / filename, label))

    for path in generated:
        print(f"已生成: {path}")


if __name__ == "__main__":
    main()
