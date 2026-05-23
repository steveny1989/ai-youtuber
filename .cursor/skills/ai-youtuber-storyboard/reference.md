# Storyboard 字段参考

## 顶层

| 字段 | 类型 | 说明 |
|------|------|------|
| `title` | string | 必填；`intro` 镜头首页主标题 |
| `language` | string | 默认 `zh-CN` |
| `chapters` | array | 章节表，见下 |
| `scenes` | array | 镜头列表，见下 |
| `output` | object | `width` `height` `fps` `filename` |
| `style` | object | 字幕与 `background_color` |
| `tts` | object | `voice` `rate`（edge-tts） |
| `watermark` | object | 左上角印章+品牌字 |
| `ending` | object | 自动片尾 |

## `chapters[]`

```json
{ "id": "1", "label": "第一章", "file": "assets/chapters/custom.jpg" }
```

- `file` 可选；默认 `assets/chapters/chapter-{id}.jpg`

## `scenes[]`

| 字段 | 说明 |
|------|------|
| `id` | 唯一；对应 `.work/audio/{id}.mp3` |
| `narration` | TTS + 底部硬字幕（全幅，受 `style` 控制） |
| `image` | 本地路径；`intro`/`chapter` 类型可省略 |
| `duration_sec` | 固定镜头时长；省略则跟配音 |
| `pause_after_sec` | 镜末静音，默认 0.3 |
| `scene_type` | `intro` \| `chapter` \| `body` |
| `chapter` | 引用 `chapters[].id` |
| `chapter_title` | 直接指定章节名（不查 chapters 表） |

## `style`

| 字段 | 默认 |
|------|------|
| `background_color` | `#0a1210` |
| `subtitle_align` | `center` |
| `subtitle_font_size` | 34 |
| `subtitle_color` | `#f2f0e8` |
| `subtitle_style` | `shadow`（`box` = 黑底条） |
| `subtitle_max_width_ratio` | 0.78 |
| `font_path` | null → Weibei SC |

## `ending`

```json
{
  "enabled": true,
  "image": "assets/avatar.webp",
  "duration_sec": 4,
  "narration": ""
}
```

- `narration` 空 → 静音轨，时长用 `duration_sec`
- `scenes` 中已有 `"id": "ending"` 时不再自动追加

## 素材路径解析

`image` 相对路径依次尝试：storyboard 所在目录 → 项目根。

## 视觉布局说明

- **hook_bg**：`fit_hook_background` 右对齐铺满；左侧暗区放标题（首页/章节幻灯片）。
- **字幕**：不限制在左半边，走全幅 `subtitle_align` / `max_width_ratio`。
- **片尾 avatar**：居中 contain，图内已有「打开观念黑盒，重新认识自己」。

## CLI

```bash
python -m pipeline <storyboard.json> [--work-dir DIR] [--output-dir DIR] [--skip-tts]
```
