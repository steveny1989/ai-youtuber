#!/usr/bin/env python3
"""生成庄子系列投稿封面（YouTube / B 站缩略图）。

示例：
  python3 scripts/make_zhuangzi_cover.py
  python3 scripts/make_zhuangzi_cover.py --hook "真正的自由" --sub-hook "从不再证明自己开始"
  python3 scripts/make_zhuangzi_cover.py --background assets/DaoDeJing/kun_22_galaxy_wings.jpg
  python3 scripts/make_zhuangzi_cover.py --preview
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PIL import Image, ImageDraw  # noqa: E402
from pipeline.brand import (  # noqa: E402
    BACKGROUND_COLOR,
    COVER_BRAND_SEAL_RATIO,
    COVER_OUTPUT_DIR,
    FONT_PATH,
    THUMB_ACCENT_RED,
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
    THUMB_TEXT_MAX_WIDTH_RATIO,
    WATERMARK_IMAGE,
    WATERMARK_KEY_LIGHT_BG,
    WATERMARK_LABEL_GAP,
    WATERMARK_TEXT,
)
from pipeline.ffmpeg_util import default_font_path  # noqa: E402
from pipeline.frame import (  # noqa: E402
    _draw_text_shadow,
    _hex_to_rgb,
    _wrap_text,
    fit_background_cover,
    render_seal_with_label,
)
from pipeline.slides import _thumb_gradient_overlay, _load_font, _draw_centered_lines  # noqa: E402


# 默认背景图优先级：震撼的鲲鹏系图
DEFAULT_BACKGROUNDS = [
    "assets/DaoDeJing/kun_22_galaxy_wings.jpg",
    "assets/DaoDeJing/kun_20_heading_south.jpg",
    "assets/DaoDeJing/kun_14_wings_cover_sky.jpg",
    "assets/DaoDeJing/kun_11_breach_explosion.jpg",
    "assets/DaoDeJing/kun_17_cyclone_vortex.jpg",
]

OUTPUT_PATH = f"{COVER_OUTPUT_DIR}/zhuangzi-xiaoyaoyou-cover.jpg"


def make_zhuangzi_cover(
    *,
    hook: str = "真正的自由",
    sub_hook: str = "从不再证明自己开始",
    series_label: str = "观念黑盒 · 庄子",
    background: Path | None = None,
    out_path: Path | None = None,
    width: int = 1920,
    height: int = 1080,
    preview: bool = False,
) -> Path:
    out = out_path or (ROOT / OUTPUT_PATH)
    out.parent.mkdir(parents=True, exist_ok=True)

    # 选背景图
    bg_path: Path | None = background
    if bg_path is None:
        for candidate in DEFAULT_BACKGROUNDS:
            p = ROOT / candidate
            if p.is_file():
                bg_path = p
                break
    if bg_path is None or not bg_path.is_file():
        bg_path = ROOT / "assets/placeholder.jpg"

    bg_rgb = _hex_to_rgb(BACKGROUND_COLOR)
    base = fit_background_cover(Image.open(bg_path), width, height, bg_rgb)
    rgba = base.convert("RGBA")
    rgba = Image.alpha_composite(rgba, _thumb_gradient_overlay(width, height))
    base = rgba.convert("RGB")
    draw = ImageDraw.Draw(base)

    margin_x = int(width * THUMB_MARGIN_X_RATIO)
    text_max_w = int(width * THUMB_TEXT_MAX_WIDTH_RATIO)
    margin_top = int(height * THUMB_MARGIN_TOP_RATIO)
    margin_bottom = int(height * THUMB_MARGIN_BOTTOM_RATIO)
    gap_lg = int(height * THUMB_GAP_LG_RATIO)
    gap_sm = int(height * THUMB_GAP_SM_RATIO)

    # 品牌印章 + 观念黑盒
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

    # 「庄子·逍遥游」红色 badge（替代道德经的章节 badge）
    badge_label = "庄子 · 逍遥游"
    badge_font_size = 56
    badge_font = _load_font(badge_font_size)
    pad_x = int(badge_font_size * 0.72)
    pad_y = int(badge_font_size * 0.42)
    bbox = draw.textbbox((0, 0), badge_label, font=badge_font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    badge_w = text_w + pad_x * 2
    badge_h = text_h + pad_y * 2
    badge_x = (width - badge_w) // 2
    badge_y = brand_bottom + gap_lg

    draw.rounded_rectangle(
        [badge_x, badge_y, badge_x + badge_w, badge_y + badge_h],
        radius=int(badge_font_size * 0.42),
        fill=_hex_to_rgb(THUMB_ACCENT_RED),
    )
    draw.text(
        (badge_x + badge_w / 2, badge_y + badge_h / 2),
        badge_label,
        font=badge_font,
        fill=_hex_to_rgb(THUMB_TEXT),
        anchor="mm",
    )
    y = badge_y + badge_h

    # 主 hook
    hook_lines, hook_h, hook_font = _measure_text(hook, THUMB_HOOK_FONT_SIZE, text_max_w)
    if hook_lines:
        y += gap_lg
        hook_line_h = int(THUMB_HOOK_FONT_SIZE * 1.06)
        y = _draw_centered_lines(
            draw, hook_lines, 0, width, y, hook_font,
            _hex_to_rgb(THUMB_TEXT), hook_line_h,
        )

    # 副 hook
    if sub_hook.strip():
        sub_lines, _, sub_font = _measure_text(sub_hook, THUMB_SUB_HOOK_FONT_SIZE, text_max_w)
        if sub_lines:
            y += gap_sm
            sub_line_h = int(THUMB_SUB_HOOK_FONT_SIZE * 1.12)
            _draw_centered_lines(
                draw, sub_lines, 0, width, y, sub_font,
                _hex_to_rgb(THUMB_TEXT_MUTED), sub_line_h,
            )

    # 底部系列名
    if series_label.strip():
        ser_font = _load_font(THUMB_SERIES_FONT_SIZE)
        ser_w = draw.textlength(series_label, font=ser_font)
        ser_bbox = draw.textbbox((0, 0), series_label, font=ser_font)
        ser_h = ser_bbox[3] - ser_bbox[1]
        ser_x = (width - ser_w) / 2
        ser_y = height - margin_bottom - ser_h
        _draw_text_shadow(
            draw, (ser_x, ser_y), series_label,
            ser_font, _hex_to_rgb(THUMB_TEXT_MUTED),
        )

    base.save(out, format="JPEG", quality=93)
    print(f"封面已生成: {out}")
    print(f"  背景: {bg_path.name}")
    print(f"  主标题: {hook}")
    print(f"  副标题: {sub_hook}")

    if preview:
        prev = out.with_name(out.stem + "-preview-640.jpg")
        img = Image.open(out).convert("RGB")
        img = img.resize((640, 360), Image.Resampling.LANCZOS)
        img.save(prev, format="JPEG", quality=90)
        print(f"  预览: {prev}")

    return out


def _measure_text(
    text: str, font_size: int, max_width: int
) -> tuple[list[str], int, object]:
    draw = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    font = _load_font(font_size)
    lines = _wrap_text(draw, text.strip(), font, max_width)
    line_h = int(font_size * 1.06)
    visible = [ln for ln in lines if ln]
    return visible, len(visible) * line_h, font


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hook", default="真正的自由")
    parser.add_argument("--sub-hook", default="从不再证明自己开始")
    parser.add_argument("--series-label", default="观念黑盒 · 庄子")
    parser.add_argument("--background", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--preview", action="store_true")
    args = parser.parse_args()

    bg = args.background
    if bg and not bg.is_absolute():
        bg = ROOT / bg

    make_zhuangzi_cover(
        hook=args.hook,
        sub_hook=args.sub_hook,
        series_label=args.series_label,
        background=bg,
        out_path=args.output,
        preview=args.preview,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
