"""首页 / 章节幻灯片生成（与 placeholder-home 同系视觉）。"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .brand import (
    BACKGROUND_COLOR,
    FONT_PATH,
    HOOK_BG,
    HOOK_HOME_ZONE_LEFT_RATIO,
    HOOK_HOME_ZONE_WIDTH_RATIO,
    PLACEHOLDER_CHAPTER_DIR,
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
from .ffmpeg_util import default_font_path
from .frame import (
    _draw_text_shadow,
    _hex_to_rgb,
    _wrap_text,
    fit_hook_background,
    load_brand_logo,
    render_seal_with_label,
)


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    path = FONT_PATH or default_font_path()
    if path and Path(path).exists():
        try:
            return ImageFont.truetype(path, size=size)
        except OSError:
            pass
    return ImageFont.load_default()


def _tone_gradient_canvas(width: int, height: int) -> Image.Image:
    from .brand import PALETTE_ACCENT, PALETTE_BG, PALETTE_MID

    base = _hex_to_rgb(PALETTE_BG)
    mid = _hex_to_rgb(PALETTE_MID)
    accent = _hex_to_rgb(PALETTE_ACCENT)
    img = Image.new("RGB", (width, height), base)
    px = img.load()
    for y in range(height):
        ty = y / max(height - 1, 1)
        for x in range(width):
            tx = x / max(width - 1, 1)
            r = int(
                base[0] * (1 - ty) * (1 - tx * 0.35)
                + mid[0] * ty * 0.45
                + accent[0] * tx * 0.12
            )
            g = int(
                base[1] * (1 - ty) * (1 - tx * 0.35)
                + mid[1] * ty * 0.45
                + accent[1] * tx * 0.12
            )
            b = int(
                base[2] * (1 - ty) * (1 - tx * 0.35)
                + mid[2] * ty * 0.45
                + accent[2] * tx * 0.12
            )
            px[x, y] = (min(r, 40), min(g, 48), min(b, 44))
    return img


def _hook_canvas(width: int, height: int, hook_path: Path | None) -> Image.Image:
    if hook_path and hook_path.exists():
        return fit_hook_background(
            Image.open(hook_path),
            width,
            height,
            _hex_to_rgb(BACKGROUND_COLOR),
        )
    return _tone_gradient_canvas(width, height)


def _title_zone(width: int) -> tuple[int, int]:
    zone_left = int(width * HOOK_HOME_ZONE_LEFT_RATIO)
    zone_width = int(width * HOOK_HOME_ZONE_WIDTH_RATIO)
    return zone_left, zone_width


def _center_in_zone(x_left: int, zone_width: int, block_width: float) -> int:
    return int(x_left + (zone_width - block_width) / 2)


def _draw_brand_row(
    base: Image.Image,
    y: int,
    zone_left: int,
    zone_width: int,
    logo_path: Path,
) -> int:
    if not logo_path.exists() or not WATERMARK_TEXT.strip():
        return y
    draw = ImageDraw.Draw(base)
    seal_max = max(32, int(base.width * WATERMARK_WIDTH_RATIO))
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
    fill = _hex_to_rgb("#f2f0e8")
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


def render_home_slide(
    title: str,
    out_path: Path,
    *,
    width: int = 1920,
    height: int = 1080,
    hook_path: Path | None = None,
    logo_path: Path | None = None,
) -> Path:
    hook_path = hook_path or Path(HOOK_BG)
    logo_path = logo_path or Path(WATERMARK_IMAGE)
    base = _hook_canvas(width, height, hook_path)
    zone_left, zone_width = _title_zone(width)
    y = _draw_brand_row(base, 96, zone_left, zone_width, logo_path)
    _draw_zone_title(base, title, y, zone_left, zone_width, font_size=52)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    base.save(out_path, format="JPEG", quality=92)
    return out_path


def render_chapter_slide(
    chapter_label: str,
    out_path: Path,
    *,
    width: int = 1920,
    height: int = 1080,
    hook_path: Path | None = None,
    logo_path: Path | None = None,
    show_hint: bool = False,
) -> Path:
    hook_path = hook_path or Path(HOOK_BG)
    logo_path = logo_path or Path(WATERMARK_IMAGE)
    base = _hook_canvas(width, height, hook_path)
    zone_left, zone_width = _title_zone(width)
    y = _draw_brand_row(base, 120, zone_left, zone_width, logo_path)
    hint = "章节镜头 · 可在分镜 JSON 中替换 image" if show_hint else None
    _draw_zone_title(
        base,
        chapter_label,
        y,
        zone_left,
        zone_width,
        font_size=72,
        hint=hint,
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    base.save(out_path, format="JPEG", quality=92)
    return out_path


def default_chapter_path(chapter_id: str, file: str | None = None) -> str:
    if file:
        return file
    return f"{PLACEHOLDER_CHAPTER_DIR}/chapter-{chapter_id}.jpg"
