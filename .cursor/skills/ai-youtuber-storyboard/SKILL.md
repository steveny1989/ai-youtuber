---
name: ai-youtuber-storyboard
description: >-
  Builds and edits AI YouTuber storyboard JSON, auto-generates intro/chapter
  slides and renders videos via pipeline. Use when working in this repo on
  storyboard.json, chapters, placeholders, hook_bg, avatar ending, TTS render,
  分镜, 章节, 首页, 片尾, or python -m pipeline.
---

# AI YouTuber 分镜与渲染

本仓库：**storyboard JSON → edge-tts → Pillow 帧 → FFmpeg 成片**。

## 快速命令

```bash
# 环境
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
brew install ffmpeg

# 仅生成占位图（可选）
./scripts/make_placeholder.sh

# 渲染（会自动 prepare 首页/章节图）
python -m pipeline examples/storyboard.example.json
python -m pipeline path/to/storyboard.json --skip-tts   # 复用 .work/audio
```

成片：`output/final.mp4`（含 BGM 混音）；中间：`output/audio/`、`output/segments/`。BGM 见 `ai-youtuber-bgm` skill。

## Storyboard JSON 结构

**必填**：`title`、`scenes[]`（每项至少 `id`、`narration`）。

**推荐完整骨架**：

```json
{
  "title": "本期视频标题",
  "chapters": [
    { "id": "1", "label": "第一章" },
    { "id": "2", "label": "第二章" }
  ],
  "style": {
    "background_color": "#0a1210",
    "subtitle_align": "center",
    "subtitle_font_size": 34,
    "subtitle_color": "#f2f0e8"
  },
  "tts": { "voice": "zh-CN-YunxiNeural", "rate": "+0%" },
  "watermark": { "text": "观念黑盒" },
  "ending": {
    "enabled": true,
    "image": "assets/avatar.webp",
    "duration_sec": 4,
    "narration": ""
  },
  "scenes": [
    { "id": "intro", "scene_type": "intro", "narration": "开场…" },
    {
      "id": "ch1-open",
      "scene_type": "chapter",
      "chapter": "1",
      "narration": "第一节…",
      "duration_sec": 3.5
    },
    { "id": "body", "narration": "正文…", "image": "assets/placeholder.jpg" }
  ]
}
```

## `scene_type` 与自动生成

渲染前 `pipeline/prepare.py` 会处理：

| 写法 | 自动生成 / 行为 |
|------|-----------------|
| `scene_type: "intro"` | `assets/placeholder-home.jpg`（用顶层 `title`，hook 底） |
| `cover.enabled` + `cover.image` | `assets/covers/<本期>-cover.jpg`（片头 + 投稿封面，每期独立） |
| `scene_type: "chapter"` + `chapter: "1"` | `assets/chapters/chapter-1.jpg`（用 `chapters[].label`） |
| `chapter_title: "番外"`（无 chapters 表） | `assets/chapters/chapter-{scene.id}.jpg` |
| 顶层 `chapters[]` | 预生成全部 `chapter-{id}.jpg` |
| 省略 type，有 `image` | 使用指定素材 |
| 顶层 `ending` | 自动追加 `ending` 镜头（除非 scenes 里已有 `id: "ending"`） |

**字幕**：默认 **按句 TTS + 时间轴**（`.work/audio/{id}.cues.json`，渲染时逐句换字拼接），与配音同步；勿把整段 `narration` 烙在画面上。`burn_subtitles: true` + `subtitle` 仅作静态烧录兜底（`brand.SUBTITLE_TIMED=False` 时）。

**不必**为 intro/chapter 手写 `image`，除非要用自定义图覆盖。

## 品牌与素材（`pipeline/brand.py`）

| 常量 / 文件 | 用途 |
|-------------|------|
| `HOOK_BG` `assets/hook_bg.webp` | 首页/章节底图（右对齐宝盒，左区写字） |
| `PLACEHOLDER_HOME_IMAGE` | 首页成片 |
| `PLACEHOLDER_IMAGE` | 正文纯色渐变底 |
| `BRAND_AVATAR` `assets/avatar.webp` | 片尾（图内已有魏碑文案） |
| `BACKGROUND_COLOR` `#0a1210` | 画布底色 / 留边 |
| `WATERMARK_TEXT` `观念黑盒` | 印章右侧品牌字（魏碑） |
| 字体 | 默认 **Weibei SC**；`assets/fonts/WeibeiSC-Bold.otf` 可自备 |

水印：小印章 + 右侧「观念黑盒」；片尾镜头不叠水印。

## 修改代码时的入口

| 任务 | 文件 |
|------|------|
| 分镜数据模型 | `pipeline/models.py` |
| 自动生成首页/章节图 | `pipeline/prepare.py`, `pipeline/slides.py` |
| 单帧：底图、字幕、水印 | `pipeline/frame.py` |
| 渲染 / 拼接 | `pipeline/render.py` |
| 品牌默认值 | `pipeline/brand.py` |
| JSON Schema | `schemas/storyboard.schema.json` |
| 示例 | `examples/storyboard.example.json` |

## 代理工作流

1. 用户给脚本/大纲 → 写成符合上表的 `storyboard.json`（放 `examples/` 或用户路径）。
2. 需要新章节 → 在 `chapters` 增 `{id, label}`，对应镜头 `scene_type: "chapter"` + `chapter: id`。
3. 运行 `python -m pipeline <json>`；失败查 FFmpeg、edge-tts 网络、素材路径。
4. 改视觉默认值 → 优先 `brand.py`，再 `make_placeholder.sh` 或重跑 pipeline（prepare 会覆盖章节图）。

## 详细参考

- 字段说明与更多示例：[reference.md](reference.md)
- 从外部脚本转 JSON 的模板：[examples.md](examples.md)
