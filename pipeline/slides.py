"""首页 / 章节幻灯片生成（与 placeholder-home 同系视觉）。"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .brand import (
    BACKGROUND_COLOR,
    COVER_BRAND_SEAL_RATIO,
    COVER_HOOK_FONT_SIZE,
    COVER_SUBTITLE_FONT_SIZE,
    FONT_PATH,
    HOME_TITLE_FONT_SIZE,
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


def render_cover_hook_slide(
    hook: str,
    subtitle: str,
    out_path: Path,
    *,
    width: int = 1920,
    height: int = 1080,
    hook_path: Path | None = None,
    logo_path: Path | None = None,
) -> Path:
    """片头：大号钩子 + 红色印章 + 系列名。"""
    hook_path = hook_path or Path(HOOK_BG)
    logo_path = logo_path or Path(WATERMARK_IMAGE)
    base = _hook_canvas(width, height, hook_path)
    margin_x = int(width * 0.08)
    zone_width = width - 2 * margin_x
    block_h = int(height * 0.48)
    y0 = (height - block_h) // 2 - int(height * 0.05)
    y = _draw_zone_title(
        base,
        hook,
        y0,
        margin_x,
        zone_width,
        font_size=COVER_HOOK_FONT_SIZE,
    )
    y += int(height * 0.05)
    if subtitle.strip() and logo_path.exists():
        seal_max = max(48, int(width * COVER_BRAND_SEAL_RATIO))
        brand_font = COVER_SUBTITLE_FONT_SIZE
        draw = ImageDraw.Draw(base)
        label = subtitle.strip()
        label_font = _load_font(brand_font)
        text_w = draw.textlength(label, font=label_font)
        gap = WATERMARK_LABEL_GAP + 4
        brand_w = seal_max + gap + text_w
        brand_x = int(margin_x + (zone_width - brand_w) / 2)
        render_seal_with_label(
            base,
            logo_path,
            label,
            brand_x,
            y,
            seal_max_px=seal_max,
            label_font_size=brand_font,
            font_path=FONT_PATH or default_font_path(),
            font_index=0,
            label_color="#f2f0e8",
            opacity=1.0,
            seal_only=True,
            key_light_bg=WATERMARK_KEY_LIGHT_BG,
            gap=gap,
        )
    elif subtitle.strip():
        draw = ImageDraw.Draw(base)
        sub_font = _load_font(COVER_SUBTITLE_FONT_SIZE)
        fill = _hex_to_rgb("#f2f0e8")
        tw = draw.textlength(subtitle.strip(), font=sub_font)
        x = margin_x + (zone_width - tw) / 2
        _draw_text_shadow(draw, (x, y), subtitle.strip(), sub_font, fill)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    base.save(out_path, format="JPEG", quality=92)
    return out_path


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
    _draw_zone_title(base, title, y, zone_left, zone_width, font_size=HOME_TITLE_FONT_SIZE)
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


def _thumb_gradient_overlay(width: int, height: int) -> Image.Image:
    """中部 + 底部渐暗，保证居中标题可读，右侧背景仍可见。"""
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    px = overlay.load()
    for y in range(height):
        ty = y / max(height - 1, 1)
        bottom = int(165 * max(0.0, (ty - 0.46) / 0.54))
        for x in range(width):
            tx = x / max(width - 1, 1)
            edge = min(tx, 1.0 - tx)
            mid = int(95 * max(0.0, 1.0 - edge / 0.30)) if edge < 0.30 else 0
            alpha = min(255, bottom + mid)
            px[x, y] = (8, 14, 12, alpha)
    return overlay


def _chapter_label_cn(chapter_num: int) -> str:
    """1–81 → 第一章 … 第八十一章"""
    digits = "零一二三四五六七八九"
    n = int(chapter_num)
    if n <= 0:
        return f"第{n}章"
    if n < 10:
        core = digits[n]
    elif n == 10:
        core = "十"
    elif n < 20:
        core = "十" + digits[n % 10]
    elif n < 100:
        tens, ones = divmod(n, 10)
        core = digits[tens] + "十"
        if ones:
            core += digits[ones]
    else:
        core = str(n)
    return f"第{core}章"


def _chapter_badge_size(chapter_num: int, font_size: int) -> tuple[int, int]:
    from .brand import THUMB_CHAPTER_BADGE_PAD_X, THUMB_CHAPTER_BADGE_PAD_Y

    label = _chapter_label_cn(chapter_num)
    font = _load_font(font_size)
    draw = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    bbox = draw.textbbox((0, 0), label, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    pad_x = int(font_size * THUMB_CHAPTER_BADGE_PAD_X)
    pad_y = int(font_size * THUMB_CHAPTER_BADGE_PAD_Y)
    return text_w + pad_x * 2, text_h + pad_y * 2


def _measure_wrapped_lines(
    text: str,
    font_size: int,
    max_width: int,
    *,
    line_height_ratio: float = 1.06,
) -> tuple[list[str], int, ImageFont.FreeTypeFont | ImageFont.ImageFont]:
    draw = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    font = _load_font(font_size)
    lines = _wrap_text(draw, text.strip(), font, max_width)
    line_h = int(font_size * line_height_ratio)
    visible = [ln for ln in lines if ln]
    height = len(visible) * line_h if visible else 0
    return visible, height, font


def _draw_centered_lines(
    draw: ImageDraw.ImageDraw,
    lines: list[str],
    zone_left: int,
    zone_width: int,
    y: int,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    fill: tuple[int, int, int],
    line_height: int,
) -> int:
    for line in lines:
        tw = draw.textlength(line, font=font)
        x = zone_left + (zone_width - tw) / 2
        _draw_text_shadow(
            draw, (x, y), line, font, fill, offsets=((3, 3), (2, 2), (1, 1))
        )
        y += line_height
    return y


def _draw_chapter_badge(
    base: Image.Image,
    chapter_num: int,
    x: int,
    y: int,
    *,
    font_size: int,
) -> int:
    from .brand import (
        THUMB_ACCENT_RED,
        THUMB_CHAPTER_BADGE_PAD_X,
        THUMB_CHAPTER_BADGE_PAD_Y,
        THUMB_CHAPTER_BADGE_RADIUS,
        THUMB_TEXT,
    )

    draw = ImageDraw.Draw(base)
    label = _chapter_label_cn(chapter_num)
    font = _load_font(font_size)
    pad_x = int(font_size * THUMB_CHAPTER_BADGE_PAD_X)
    pad_y = int(font_size * THUMB_CHAPTER_BADGE_PAD_Y)
    bbox = draw.textbbox((0, 0), label, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    box_w = text_w + pad_x * 2
    box_h = text_h + pad_y * 2
    box = [x, y, x + box_w, y + box_h]
    draw.rounded_rectangle(
        box,
        radius=int(font_size * THUMB_CHAPTER_BADGE_RADIUS),
        fill=_hex_to_rgb(THUMB_ACCENT_RED),
    )
    cx = x + box_w / 2
    cy = y + box_h / 2
    draw.text(
        (cx, cy),
        label,
        font=font,
        fill=_hex_to_rgb(THUMB_TEXT),
        anchor="mm",
    )
    return box[3]


def render_chapter_thumbnail(
    *,
    chapter_num: int,
    hook: str,
    sub_hook: str,
    background: Path,
    out_path: Path,
    series_label: str = "道德经 · 八十一讲精解",
    width: int = 1920,
    height: int = 1080,
) -> Path:
    """单章投稿封面：左侧内容区（约 58% 宽）内居中排版，右侧留给背景。"""
    from .brand import (
        THUMB_CHAPTER_FONT_SIZE,
        THUMB_GAP_LG_RATIO,
        THUMB_GAP_SM_RATIO,
        THUMB_HOOK_FONT_SIZE,
        THUMB_MARGIN_BOTTOM_RATIO,
        THUMB_MARGIN_TOP_RATIO,
        THUMB_MARGIN_X_RATIO,
        THUMB_SERIES_FONT_SIZE,
        THUMB_SUB_HOOK_FONT_SIZE,
        THUMB_TEXT,
        THUMB_TEXT_MAX_WIDTH_RATIO,
        THUMB_TEXT_MUTED,
        THUMB_ZONE_WIDTH_RATIO,
    )
    from .frame import fit_background_cover

    bg_rgb = _hex_to_rgb(BACKGROUND_COLOR)
    if background.is_file():
        base = fit_background_cover(Image.open(background), width, height, bg_rgb)
    else:
        base = _tone_gradient_canvas(width, height)

    rgba = base.convert("RGBA")
    rgba = Image.alpha_composite(rgba, _thumb_gradient_overlay(width, height))
    base = rgba.convert("RGB")
    draw = ImageDraw.Draw(base)

    zone_width = width if THUMB_ZONE_WIDTH_RATIO >= 1.0 else int(width * THUMB_ZONE_WIDTH_RATIO)
    zone_left = 0 if THUMB_ZONE_WIDTH_RATIO >= 1.0 else int(width * THUMB_MARGIN_X_RATIO)
    text_max_w = int(width * THUMB_TEXT_MAX_WIDTH_RATIO)
    brand_x = int(width * THUMB_MARGIN_X_RATIO)
    margin_top = int(height * THUMB_MARGIN_TOP_RATIO)
    margin_bottom = int(height * THUMB_MARGIN_BOTTOM_RATIO)
    gap_lg = int(height * THUMB_GAP_LG_RATIO)
    gap_sm = int(height * THUMB_GAP_SM_RATIO)

    series_font = _load_font(THUMB_SERIES_FONT_SIZE)
    series_text = series_label.strip()
    series_bbox = draw.textbbox((0, 0), series_text, font=series_font)
    series_h = series_bbox[3] - series_bbox[1]
    series_w = draw.textlength(series_text, font=series_font)
    footer_y = height - margin_bottom - series_h

    logo_path = Path(WATERMARK_IMAGE)
    brand_bottom = margin_top
    if logo_path.exists():
        seal_max = max(40, int(width * COVER_BRAND_SEAL_RATIO))
        _, brand_h = render_seal_with_label(
            base,
            logo_path,
            WATERMARK_TEXT.strip(),
            brand_x,
            margin_top,
            seal_max_px=seal_max,
            label_font_size=THUMB_SERIES_FONT_SIZE,
            font_path=FONT_PATH or default_font_path(),
            font_index=0,
            label_color=THUMB_TEXT,
            opacity=1.0,
            seal_only=True,
            key_light_bg=WATERMARK_KEY_LIGHT_BG,
            gap=WATERMARK_LABEL_GAP,
        )
        brand_bottom = margin_top + brand_h

    badge_w, badge_h = _chapter_badge_size(chapter_num, THUMB_CHAPTER_FONT_SIZE)
    hook_lines, hook_h, hook_font = _measure_wrapped_lines(
        hook, THUMB_HOOK_FONT_SIZE, text_max_w, line_height_ratio=1.06
    )
    sub_lines: list[str] = []
    sub_h = 0
    sub_font = hook_font
    if sub_hook.strip():
        sub_lines, sub_h, sub_font = _measure_wrapped_lines(
            sub_hook,
            THUMB_SUB_HOOK_FONT_SIZE,
            text_max_w,
            line_height_ratio=1.12,
        )

    content_h = badge_h
    if hook_lines:
        content_h += gap_lg + hook_h
    if sub_lines:
        content_h += gap_sm + sub_h

    content_top = brand_bottom + gap_lg
    footer_top = footer_y - gap_lg
    if content_h < footer_top - content_top:
        content_top += (footer_top - content_top - content_h) // 2

    badge_x = (width - badge_w) // 2
    y = _draw_chapter_badge(
        base, chapter_num, badge_x, content_top, font_size=THUMB_CHAPTER_FONT_SIZE
    )

    if hook_lines:
        y += gap_lg
        hook_line_h = int(THUMB_HOOK_FONT_SIZE * 1.06)
        y = _draw_centered_lines(
            draw,
            hook_lines,
            0,
            width,
            y,
            hook_font,
            _hex_to_rgb(THUMB_TEXT),
            hook_line_h,
        )

    if sub_lines:
        y += gap_sm
        sub_line_h = int(THUMB_SUB_HOOK_FONT_SIZE * 1.12)
        _draw_centered_lines(
            draw,
            sub_lines,
            0,
            width,
            y,
            sub_font,
            _hex_to_rgb(THUMB_TEXT_MUTED),
            sub_line_h,
        )

    if series_text:
        series_x = (width - series_w) / 2
        _draw_text_shadow(
            draw,
            (series_x, footer_y),
            series_text,
            series_font,
            _hex_to_rgb(THUMB_TEXT_MUTED),
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    base.save(out_path, format="JPEG", quality=93)
    return out_path


def render_chapter_thumbnail_vertical(
    *,
    chapter_num: int,
    hook: str,
    sub_hook: str,
    background: Path,
    out_path: Path,
    series_label: str = "道德经 · 八十一讲精解",
    width: int = 1080,
    height: int = 1920,
) -> Path:
    """抖音竖版封面（9:16）。

    布局：全幅背景 + 顶部渐暗 + 底部大字区
    - 顶部 15%：品牌印章
    - 中间：背景图（可见）
    - 下 45%：渐暗区内居中显示章节 badge + hook + sub_hook + 系列名
    """
    from .brand import (
        THUMB_CHAPTER_FONT_SIZE,
        THUMB_GAP_LG_RATIO,
        THUMB_GAP_SM_RATIO,
        THUMB_HOOK_FONT_SIZE,
        THUMB_MARGIN_BOTTOM_RATIO,
        THUMB_MARGIN_TOP_RATIO,
        THUMB_MARGIN_X_RATIO,
        THUMB_SERIES_FONT_SIZE,
        THUMB_SUB_HOOK_FONT_SIZE,
        THUMB_TEXT,
        THUMB_TEXT_MUTED,
    )
    from .frame import fit_background_cover

    # ── 背景 ──────────────────────────────────────────────────────
    bg_rgb = _hex_to_rgb(BACKGROUND_COLOR)
    if background.is_file():
        base = fit_background_cover(Image.open(background), width, height, bg_rgb)
    else:
        base = _tone_gradient_canvas(width, height)

    # ── 竖版渐变遮罩：下半部加深，确保文字可读 ────────────────────
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    px = overlay.load()
    for y_px in range(height):
        t = y_px / max(height - 1, 1)
        # 下 50% 开始渐暗，最深约 200
        if t > 0.50:
            alpha = int(200 * (t - 0.50) / 0.50)
        else:
            alpha = 0
        # 顶部 10% 轻微遮罩
        if t < 0.10:
            alpha = max(alpha, int(80 * (0.10 - t) / 0.10))
        for x_px in range(width):
            px[x_px, y_px] = (8, 14, 12, min(alpha, 210))

    base = Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(base)

    margin_x = int(width * THUMB_MARGIN_X_RATIO)
    text_max_w = int(width * 0.88)   # 竖图可用更宽的文字区
    margin_top = int(height * THUMB_MARGIN_TOP_RATIO)
    margin_bottom = int(height * THUMB_MARGIN_BOTTOM_RATIO)
    gap_lg = int(height * THUMB_GAP_LG_RATIO)
    gap_sm = int(height * THUMB_GAP_SM_RATIO)

    # ── 品牌印章（左上）───────────────────────────────────────────
    logo_path = Path(WATERMARK_IMAGE)
    brand_bottom = margin_top
    if logo_path.exists():
        seal_max = max(40, int(width * COVER_BRAND_SEAL_RATIO))
        _, brand_h = render_seal_with_label(
            base,
            logo_path,
            WATERMARK_TEXT.strip(),
            margin_x,
            margin_top,
            seal_max_px=seal_max,
            label_font_size=THUMB_SERIES_FONT_SIZE,
            font_path=FONT_PATH or default_font_path(),
            font_index=0,
            label_color=THUMB_TEXT,
            opacity=1.0,
            seal_only=True,
            key_light_bg=WATERMARK_KEY_LIGHT_BG,
            gap=WATERMARK_LABEL_GAP,
        )
        brand_bottom = margin_top + brand_h

    # ── 文字区：垂直居中偏上（约 42% 处）──────────────────────────
    series_font = _load_font(THUMB_SERIES_FONT_SIZE)
    series_text = series_label.strip()
    series_bbox = draw.textbbox((0, 0), series_text, font=series_font)
    series_h = series_bbox[3] - series_bbox[1]
    series_w = draw.textlength(series_text, font=series_font)
    footer_y = height - margin_bottom - series_h

    # 竖版 hook 字号适当缩小（否则撑满屏幕）
    v_hook_size = int(THUMB_HOOK_FONT_SIZE * 0.80)
    v_sub_size = int(THUMB_SUB_HOOK_FONT_SIZE * 0.85)
    v_badge_size = int(THUMB_CHAPTER_FONT_SIZE * 0.90)

    badge_w, badge_h = _chapter_badge_size(chapter_num, v_badge_size)
    hook_lines, hook_h, hook_font = _measure_wrapped_lines(
        hook, v_hook_size, text_max_w, line_height_ratio=1.10
    )
    sub_lines, sub_h, sub_font = [], 0, hook_font
    if sub_hook.strip():
        sub_lines, sub_h, sub_font = _measure_wrapped_lines(
            sub_hook, v_sub_size, text_max_w, line_height_ratio=1.15
        )

    content_h = badge_h
    if hook_lines:
        content_h += gap_lg + hook_h
    if sub_lines:
        content_h += gap_sm + sub_h

    # 内容块垂直中心放在画面 42% 处（偏上中心）
    center_y = int(height * 0.42)
    content_top = center_y - content_h // 2
    # 不高于品牌印章底部 + 一个间距
    content_top = max(content_top, brand_bottom + gap_lg)

    # ── 章节 badge ────────────────────────────────────────────────
    badge_x = (width - badge_w) // 2
    y = _draw_chapter_badge(base, chapter_num, badge_x, content_top, font_size=v_badge_size)

    # ── 主 hook ───────────────────────────────────────────────────
    if hook_lines:
        y += gap_lg
        y = _draw_centered_lines(
            draw, hook_lines, 0, width, y,
            hook_font, _hex_to_rgb(THUMB_TEXT), int(v_hook_size * 1.10),
        )

    # ── 副 hook ───────────────────────────────────────────────────
    if sub_lines:
        y += gap_sm
        _draw_centered_lines(
            draw, sub_lines, 0, width, y,
            sub_font, _hex_to_rgb(THUMB_TEXT_MUTED), int(v_sub_size * 1.15),
        )

    # ── 底部系列名 ────────────────────────────────────────────────
    if series_text:
        series_x = (width - series_w) / 2
        _draw_text_shadow(
            draw, (series_x, footer_y), series_text,
            series_font, _hex_to_rgb(THUMB_TEXT_MUTED),
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    base.save(out_path, format="JPEG", quality=93)
    return out_path
