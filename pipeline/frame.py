from __future__ import annotations

import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .brand import (
    BACKGROUND_COLOR,
    ENDING_SCENE_ID,
    HOOK_BG,
    PLACEHOLDER_CHAPTER_DIR,
    PLACEHOLDER_HOME_IMAGE,
    SUBTITLE_TIMED,
)
from .ffmpeg_util import default_font_path
from .models import Scene, StyleConfig, WatermarkConfig


def _load_font(
    size: int,
    font_path: str | None,
    index: int = 0,
) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    path = font_path or default_font_path()
    if path and Path(path).exists():
        try:
            return ImageFont.truetype(path, size=size, index=index)
        except OSError:
            try:
                return ImageFont.truetype(path, size=size)
            except OSError:
                pass
    return ImageFont.load_default()


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    c = hex_color.lstrip("#")
    if len(c) != 6:
        return (26, 26, 46)
    return tuple(int(c[i : i + 2], 16) for i in (0, 2, 4))


def is_prerendered_slide(image_path: Path | None) -> bool:
    """已生成的首页 / 章节 JPEG，直接铺满画布。"""
    if not image_path:
        return False
    if image_path.name == Path(PLACEHOLDER_HOME_IMAGE).name:
        return True
    return image_path.parent.name == Path(PLACEHOLDER_CHAPTER_DIR).name


def is_hook_background(image_path: Path | None) -> bool:
    if not image_path:
        return False
    if is_prerendered_slide(image_path):
        return True
    return image_path.name == Path(HOOK_BG).name


def _fit_image(img: Image.Image, width: int, height: int, bg_rgb: tuple[int, int, int]) -> Image.Image:
    canvas = Image.new("RGB", (width, height), bg_rgb)
    img = img.convert("RGB")
    img.thumbnail((width, height), Image.Resampling.LANCZOS)
    x = (width - img.width) // 2
    y = (height - img.height) // 2
    canvas.paste(img, (x, y))
    return canvas


def fit_hook_background(
    img: Image.Image,
    width: int,
    height: int,
    bg_rgb: tuple[int, int, int],
) -> Image.Image:
    """铺满画布并右对齐，保留右侧宝盒主体。"""
    canvas = Image.new("RGB", (width, height), bg_rgb)
    src = img.convert("RGB")
    iw, ih = src.size
    scale = max(width / iw, height / ih)
    nw, nh = int(iw * scale), int(ih * scale)
    resized = src.resize((nw, nh), Image.Resampling.LANCZOS)
    x = width - nw
    y = (height - nh) // 2
    canvas.paste(resized, (x, y))
    return canvas


def fit_background_image(
    img: Image.Image,
    width: int,
    height: int,
    bg_rgb: tuple[int, int, int],
    *,
    hook_layout: bool = False,
) -> Image.Image:
    if hook_layout:
        return fit_hook_background(img, width, height, bg_rgb)
    return _fit_image(img, width, height, bg_rgb)


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    lines: list[str] = []
    for paragraph in text.split("\n"):
        if not paragraph:
            lines.append("")
            continue
        current = ""
        for char in paragraph:
            trial = current + char
            if draw.textlength(trial, font=font) <= max_width:
                current = trial
            else:
                if current:
                    lines.append(current)
                current = char
        if current:
            lines.append(current)
    return lines or [text]


def _draw_text_shadow(
    draw: ImageDraw.ImageDraw,
    xy: tuple[float, float],
    text: str,
    font: ImageFont.ImageFont,
    fill: tuple[int, int, int],
    *,
    shadow: tuple[int, int, int] = (12, 12, 14),
    offsets: tuple[tuple[int, int], ...] = ((2, 2), (1, 1)),
) -> None:
    x, y = xy
    for dx, dy in offsets:
        draw.text((x + dx, y + dy), text, font=font, fill=shadow)
    draw.text((x, y), text, font=font, fill=fill)


def _draw_text_box(
    draw: ImageDraw.ImageDraw,
    xy: tuple[float, float],
    text: str,
    font: ImageFont.ImageFont,
    fill: tuple[int, int, int],
    font_size: int,
    *,
    pad_x: int = 12,
    pad_y: int = 6,
) -> None:
    x, y = xy
    text_w = draw.textlength(text, font=font)
    draw.rectangle(
        [x - pad_x, y - pad_y, x + text_w + pad_x, y + font_size + pad_y],
        fill=(0, 0, 0),
    )
    draw.text((x, y), text, font=font, fill=fill)


def _line_x(
    align: str,
    width: int,
    margin_x: int,
    line_width: float,
) -> float:
    if align == "left":
        return float(margin_x)
    return (width - line_width) / 2


def prepare_logo_rgba(
    logo: Image.Image,
    *,
    key_light_bg: bool = True,
    threshold: int = 238,
) -> Image.Image:
    """去掉 Logo 浅底（常见白底 PNG），便于叠在深色画布上。"""
    img = logo.convert("RGBA")
    if not key_light_bg:
        return img
    pixels = img.load()
    w, h = img.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = pixels[x, y]
            if a and r >= threshold and g >= threshold and b >= threshold:
                pixels[x, y] = (r, g, b, 0)
    return img


def extract_seal_logo(
    logo: Image.Image,
    *,
    key_light_bg: bool = True,
) -> Image.Image:
    """仅保留红色印章区域；小尺寸水印/首页不展示墨迹笔划。"""
    img = prepare_logo_rgba(logo, key_light_bg=key_light_bg)
    w, h = img.size
    pixels = img.load()
    xs: list[int] = []
    ys: list[int] = []
    for y in range(h):
        for x in range(w):
            r, g, b, a = pixels[x, y]
            if a < 40:
                continue
            if r > 140 and g < 130 and b < 130 and r > g + 30:
                xs.append(x)
                ys.append(y)
    if xs:
        pad = 12
        return img.crop(
            (
                max(0, min(xs) - pad),
                max(0, min(ys) - pad),
                min(w, max(xs) + pad),
                min(h, max(ys) + pad),
            )
        )
    return img.crop((0, 0, int(w * 0.42), h))


def load_brand_logo(
    logo_path: Path,
    *,
    seal_only: bool,
    key_light_bg: bool,
) -> Image.Image:
    src = Image.open(logo_path)
    if seal_only:
        return extract_seal_logo(src, key_light_bg=key_light_bg)
    return prepare_logo_rgba(src, key_light_bg=key_light_bg)


def render_seal_with_label(
    base: Image.Image,
    logo_path: Path,
    label: str,
    x: int,
    y: int,
    *,
    seal_max_px: int,
    label_font_size: int,
    font_path: str | None,
    font_index: int,
    label_color: str,
    opacity: float,
    seal_only: bool,
    key_light_bg: bool,
    gap: int,
) -> tuple[int, int]:
    """印章 + 右侧魏碑字，返回 (总宽, 总高)。"""
    seal = load_brand_logo(
        logo_path,
        seal_only=seal_only,
        key_light_bg=key_light_bg,
    )
    seal.thumbnail((seal_max_px, seal_max_px), Image.Resampling.LANCZOS)
    if opacity < 1.0:
        alpha = seal.split()[3]
        alpha = alpha.point(lambda p: int(p * opacity))
        seal.putalpha(alpha)

    layer = base.convert("RGBA")
    draw = ImageDraw.Draw(layer)
    font = _load_font(label_font_size, font_path, font_index)
    fill = _hex_to_rgb(label_color)
    text_w = draw.textlength(label, font=font)
    bbox = draw.textbbox((0, 0), label, font=font)
    text_h = bbox[3] - bbox[1]

    block_h = max(seal.height, text_h)
    seal_y = y + (block_h - seal.height) // 2
    text_y = y + (block_h - text_h) // 2 - bbox[1]

    layer.paste(seal, (x, seal_y), seal)
    text_x = x + seal.width + gap
    _draw_text_shadow(draw, (text_x, text_y), label, font, fill)

    base.paste(layer.convert("RGB"))
    total_w = seal.width + gap + int(text_w)
    return total_w, block_h


def _apply_image_watermark(
    base: Image.Image,
    logo_path: Path,
    watermark: WatermarkConfig,
    style: StyleConfig,
    frame_width: int,
) -> int:
    """粘贴 Logo，返回 Logo 占用的高度（便于 both 模式排文字）。"""
    x, y = watermark.margin_x, watermark.margin_y
    seal_max = max(32, int(frame_width * watermark.width_ratio))

    if watermark.text.strip() and watermark.seal_only:
        _, h = render_seal_with_label(
            base,
            logo_path,
            watermark.text.strip(),
            x,
            y,
            seal_max_px=seal_max,
            label_font_size=watermark.font_size,
            font_path=style.font_path,
            font_index=watermark.font_index,
            label_color=watermark.color,
            opacity=watermark.opacity,
            seal_only=True,
            key_light_bg=watermark.key_light_bg,
            gap=watermark.label_gap,
        )
        return h

    logo = load_brand_logo(
        logo_path,
        seal_only=watermark.seal_only,
        key_light_bg=watermark.key_light_bg,
    )
    logo.thumbnail((seal_max, seal_max), Image.Resampling.LANCZOS)

    if watermark.opacity < 1.0:
        alpha = logo.split()[3]
        alpha = alpha.point(lambda p: int(p * watermark.opacity))
        logo.putalpha(alpha)

    layer = base.convert("RGBA")

    if watermark.backplate:
        pad = watermark.backplate_pad
        bg_rgb = _hex_to_rgb(style.background_color)
        plate = Image.new("RGBA", layer.size, (0, 0, 0, 0))
        plate_draw = ImageDraw.Draw(plate)
        plate_draw.rounded_rectangle(
            [x - pad, y - pad, x + logo.width + pad, y + logo.height + pad],
            radius=watermark.backplate_radius,
            fill=(*bg_rgb, 230),
        )
        layer = Image.alpha_composite(layer, plate)

    layer.paste(logo, (x, y), logo)
    base.paste(layer.convert("RGB"))
    return logo.height


def _apply_text_watermark(
    base: Image.Image,
    watermark: WatermarkConfig,
    style: StyleConfig,
    frame_width: int,
    *,
    y_offset: int = 0,
) -> None:
    if not watermark.text.strip():
        return
    draw = ImageDraw.Draw(base)
    font_size = watermark.font_size or max(24, int(frame_width * 0.018))
    font = _load_font(font_size, style.font_path, watermark.font_index)
    text = watermark.text
    x = float(watermark.margin_x)
    y = float(watermark.margin_y + y_offset)
    fill = _hex_to_rgb(watermark.color)

    if watermark.style == "box":
        _draw_text_box(draw, (x, y), text, font, fill, font_size, pad_x=10, pad_y=5)
    else:
        _draw_text_shadow(draw, (x, y), text, font, fill)


def _apply_watermark(
    base: Image.Image,
    watermark: WatermarkConfig,
    style: StyleConfig,
    frame_width: int,
    logo_path: Path | None,
) -> None:
    mode = watermark.mode
    logo_h = 0
    if mode in ("image", "both") and logo_path and logo_path.exists():
        logo_h = _apply_image_watermark(
            base, logo_path, watermark, style, frame_width
        )
    if mode in ("text", "both") and not (
        watermark.seal_only and watermark.text.strip() and logo_h
    ):
        gap = 8 if mode == "both" and logo_h else 0
        _apply_text_watermark(base, watermark, style, frame_width, y_offset=logo_h + gap)


def _first_sentence(text: str, max_chars: int) -> str:
    text = text.strip()
    if not text:
        return ""
    parts = re.split(r"(?<=[。！？!?])", text, maxsplit=1)
    head = parts[0].strip() if parts else text
    if len(head) > max_chars:
        return head[: max_chars - 1] + "…"
    return head


def should_burn_subtitles(
    scene: Scene,
    narration: str,
    image_path: Path | None,
    style: StyleConfig,
) -> bool:
    if SUBTITLE_TIMED:
        return False
    if scene.burn_subtitles is False:
        return False
    if scene.burn_subtitles is True:
        return True
    if is_prerendered_slide(image_path):
        return False
    scene_type = (scene.scene_type or "").strip().lower()
    if scene_type in ("intro", "chapter"):
        return False
    if scene.subtitle and scene.subtitle.strip():
        return True
    return len(narration.strip()) <= style.subtitle_max_chars


def _subtitle_text(scene: Scene, narration: str, style: StyleConfig) -> str:
    if scene.subtitle and scene.subtitle.strip():
        return scene.subtitle.strip()
    return _first_sentence(narration, style.subtitle_max_chars)


def _draw_subtitles(
    base: Image.Image,
    text: str,
    style: StyleConfig,
    width: int,
    height: int,
) -> None:
    if not text.strip():
        return
    draw = ImageDraw.Draw(base)
    font = _load_font(style.subtitle_font_size, style.font_path, style.font_index)
    fill = _hex_to_rgb(style.subtitle_color)

    margin_x = 72
    max_width = int(width * style.subtitle_max_width_ratio)
    align = style.subtitle_align

    lines = _wrap_text(draw, text, font, max_width)
    if len(lines) > style.subtitle_max_lines:
        lines = lines[: style.subtitle_max_lines]
    line_height = style.subtitle_font_size + 14
    block_height = len(lines) * line_height
    y_start = height - style.subtitle_margin_bottom - block_height

    for i, line in enumerate(lines):
        if not line:
            continue
        tw = draw.textlength(line, font=font)
        x = _line_x(align, width, margin_x, tw)
        y = y_start + i * line_height
        if style.subtitle_style == "box":
            _draw_text_box(draw, (x, y), line, font, fill, style.subtitle_font_size)
        else:
            _draw_text_shadow(draw, (x, y), line, font, fill)


def render_frame(
    narration: str,
    style: StyleConfig,
    width: int,
    height: int,
    out_path: Path,
    image_path: Path | None = None,
    watermark: WatermarkConfig | None = None,
    watermark_logo_path: Path | None = None,
    scene_id: str | None = None,
    scene: Scene | None = None,
    timed_subtitle: str | None = None,
) -> Path:
    bg_rgb = _hex_to_rgb(style.background_color)
    hook_layout = is_hook_background(image_path)
    if image_path and image_path.exists():
        src = Image.open(image_path)
        if is_prerendered_slide(image_path):
            base = src.convert("RGB").resize((width, height), Image.Resampling.LANCZOS)
        else:
            base = fit_background_image(
                src,
                width,
                height,
                bg_rgb,
                hook_layout=hook_layout,
            )
    else:
        base = Image.new("RGB", (width, height), bg_rgb)

    scene_obj = scene or Scene(id=scene_id or "frame", narration=narration)
    if timed_subtitle and timed_subtitle.strip():
        _draw_subtitles(base, timed_subtitle.strip(), style, width, height)
    elif narration.strip() and should_burn_subtitles(
        scene_obj, narration, image_path, style
    ):
        sub = _subtitle_text(scene_obj, narration, style)
        _draw_subtitles(base, sub, style, width, height)

    wm = watermark or WatermarkConfig()
    if wm.enabled and scene_id != ENDING_SCENE_ID:
        _apply_watermark(base, wm, style, width, watermark_logo_path)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    base.save(out_path, format="PNG")
    return out_path
