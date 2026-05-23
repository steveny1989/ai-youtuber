# AI YouTuber — 模板化视频流水线

从**结构化分镜 JSON**自动生成 YouTube 成片：旁白 TTS → 按镜头时间轴合成 → 硬字幕 → 导出 mp4。

适合：脚本/分镜已由其他工具生成，本仓库专注**稳定、可复现的视频渲染**。

## 流程

```
storyboard.json → edge-tts 配音 → 每镜 FFmpeg 片段 → 拼接 → output/final.mp4
```

## 素材与 Git

`assets/`（含 `素材库/` 等）体积较大，**默认不进入版本库**。克隆仓库后在本机放入素材，或运行 `./scripts/make_placeholder.sh` 生成示例占位图。说明见 `assets/README.md`。

## 环境要求

- Python 3.10+
- [FFmpeg](https://ffmpeg.org/)（含 `ffprobe`）

macOS 安装：

```bash
brew install ffmpeg
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 快速开始

1. 生成占位图（示例分镜需要）：

```bash
chmod +x scripts/make_placeholder.sh
./scripts/make_placeholder.sh
# 可选：自定义首页标题
./scripts/make_placeholder.sh --title "本期视频标题"
```

会生成 `assets/placeholder.jpg`（正文底色）、`assets/placeholder-home.jpg`（首页）、`assets/chapters/chapter-*.jpg`（章节图，色调与首页一致）。自定义章节：`./scripts/make_placeholder.sh --chapter "第四章:chapter-04.jpg"`。

2. 渲染示例视频：

```bash
python -m pipeline examples/storyboard.example.json
```

成片输出：`output/final.mp4`  
中间文件：`.work/audio/`、`.work/segments/`

## 分镜 JSON 格式

见 `schemas/storyboard.schema.json` 与 `examples/storyboard.example.json`。

| 字段 | 说明 |
|------|------|
| `scenes[].narration` | 旁白文案（TTS + 字幕） |
| `scenes[].image` | 本地图片路径，可相对项目根或 storyboard 所在目录 |
| `scenes[].duration_sec` | 可选；省略则按配音时长 |
| `style.font_path` | 可选；中文 subtitle 需系统字体，macOS 默认 PingFang |
| `tts.voice` | edge-tts 音色，如 `zh-CN-YunxiNeural` |
| `ending` | 可选；默认自动追加 `assets/avatar.webp` 片尾（4 秒、无旁白） |

### 品牌水印与片尾

- **水印**：正文每一镜左上角显示 **`assets/Logo.png`**（片尾镜头不叠加）
- **片尾**：自动追加 `assets/avatar.webp`（约 4 秒，文案在图内）
- **首页**：`hook_bg` 背景，标题/品牌偏左中；字幕仍全幅居中

默认风格偏「真人剪辑」：无黑底条、米白字 + 轻阴影、小号左上角品牌字。可在 JSON 或 `pipeline/brand.py` 调整。

**统一画布底色**：`pipeline/brand.py` 中的 `BACKGROUND_COLOR`（默认 `#1a1a2e`）用于留边、无图镜头、片尾垫色；`style.background_color` 可覆盖。占位图请用 `./scripts/make_placeholder.sh` 生成同色底，避免正文与片尾跳色。

```json
"style": {
  "background_color": "#1a1a2e",
  "subtitle_style": "shadow",
  "subtitle_font_size": 34,
  "subtitle_color": "#f2f0e8",
  "subtitle_align": "left"
},
"watermark": {
  "mode": "image",
  "image": "assets/Logo.png",
  "width_ratio": 0.11
}
```

**字体**：片尾 `avatar.webp` 内标题为 **魏碑-简（Weibei SC Bold）**；字幕与首页占位默认自动用同款。macOS 已内置；其他系统可将 `WeibeiSC-Bold.otf` 放到 `assets/fonts/` 或在 JSON 里设 `"font_path"`。

若仍显 AI 感：换 `font_path` 为你本机喜欢的 `.ttf` / `.ttc`，或把 `subtitle_style` 改为 `box` 回到传统黑底。

### 固定片尾

每条成片渲染结束后会自动加上 **`assets/avatar.webp`**（无需写进 `scenes`）。若要关闭或改时长，在 JSON 里设置：

```json
"ending": { "enabled": true, "duration_sec": 4 }
```

默认常量见 `pipeline/brand.py`。

### 首页 / 章节（JSON 自动生成图）

渲染前会根据 JSON **自动生成**首页与章节 JPG，无需手写 `image`：

```json
{
  "title": "本期视频标题",
  "chapters": [
    { "id": "1", "label": "第一章" },
    { "id": "2", "label": "第二章" }
  ],
  "scenes": [
    { "id": "intro", "scene_type": "intro", "narration": "开场白…" },
    { "id": "ch1", "scene_type": "chapter", "chapter": "1", "narration": "第一节…" },
    { "id": "body", "narration": "正文…", "image": "assets/placeholder.jpg" }
  ]
}
```

| `scene_type` | 行为 |
|--------------|------|
| `intro` | 用 `title` 生成 `assets/placeholder-home.jpg` |
| `chapter` | 用 `chapter` 或 `chapter_title` 生成 `assets/chapters/chapter-{id}.jpg` |
| （省略） | 使用 `image` 指定素材 |

### 对接你现有的脚本

把现有脚本转成上述 JSON 即可。最小结构：

```json
{
  "title": "视频标题",
  "scenes": [
    { "id": "s1", "narration": "第一句旁白", "image": "assets/s1.jpg" }
  ]
}
```

可用任意语言写转换器（Node/Python），输出到 `examples/` 或自定义路径后调用本 pipeline。

## CLI

```bash
python -m pipeline <storyboard.json> [--work-dir DIR] [--output-dir DIR] [--skip-tts]
```

- `--skip-tts`：复用 `.work/audio/` 里已有 mp3，只重渲染画面（改模板/字幕时用）

## 目录结构

```
├── examples/          # 示例分镜
├── schemas/           # JSON Schema
├── pipeline/          # 渲染核心
├── assets/            # 本地图片素材（已 gitignore，不提交）
├── scripts/           # 辅助脚本
├── output/            # 成片（git 忽略）
└── .work/             # 中间文件（git 忽略）
```

## 后续可扩展

- 片头片尾模板、BGM 轨、转场
- 从脚本 Markdown 自动生成 `storyboard.json`
- 替换为 Remotion 获得更复杂动效（接口保持 JSON 不变）
