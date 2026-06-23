---
name: ai-youtuber-daodejing-episode
description: >-
  End-to-end workflow for 道德经五讲 episodes: write narration, ep02 image
  catalog, 22-beat storyboard, Edge/Volcengine render, cover/subtitle tuning,
  YouTube and Bilibili upload. Use for EP02+, 第二讲, ep02_image_catalog,
  为道日损, draft render, or publishing 观念黑盒 series.
---

# 道德经五讲 · 单期制作

## 系列结构（减法链）

| 期 | 主题 | 核心原文 |
|----|------|----------|
| EP01 | 地图不是道 / 上善若水 / 生产者牢笼 | 道可道非常道 |
| EP02 | 为道日损 / 身份加法 / 欲望只增不减 | 为学日益，为道日损 |
| EP03 | 知足与知止 | 知足不辱，知止不殆 |
| EP04 | 简单 / 见素抱朴 | 少则得，多则惑 |
| EP05 | 执一 / 五讲合链（收官） | 载营魄抱一 |

每期骨架：**intro×2 → open×3 论点 → open-4 协议 → closing**；成片用 **22 节拍**（与 EP01 同节奏）。

## 封面（每期独立）

| 用途 | 路径 | 配置 |
|------|------|------|
| 成片片头 3 秒 | `assets/covers/daodejing-epNN-cover.jpg` | 分镜 `cover.image` + `cover.hook` |
| B 站缩略图 | 同上（或 `bilibili.cover_image`） | 默认读 `cover.image` |
| 旧式 intro | `assets/placeholder-home.jpg` | 仅 `scene_type: intro` 正文镜 |

渲染时 `prepare.py` 自动生成 `cover.image`，**不会**再覆盖 `placeholder-home.jpg`。

```json
"cover": {
  "enabled": true,
  "image": "assets/covers/daodejing-ep02-cover.jpg",
  "hook": "你不是缺方法，你缺的是敢删。",
  "subtitle": "观念黑盒 · 道德经五讲"
},
"bilibili": {
  "cover_image": "assets/covers/daodejing-ep02-cover.jpg"
}
```

省略 `cover.image` 时自动：`assets/covers/{成片文件名}-cover.jpg`。

## 文件约定

| 文件 | 用途 |
|------|------|
| `examples/storyboard-daodejing-epNN.json` | 粗分镜（大段 narration） |
| `examples/storyboard-daodejing-epNN-22beats.json` | **渲染用**：22 镜 + 配图 + cover/youtube/bilibili |
| `examples/epNN_beats.json` | 节拍 keywords（配图匹配） |
| `examples/epNN_image_matches.json` | 配图结果清单 |
| `assets/DaoDeJing/image_catalog.json` | **统一图库**（合并各期 catalog + 磁盘扫描） |
| `assets/DaoDeJing/epNN_image_catalog.json` | 各期原始图鉴（可选，合并进统一图库） |
| `assets/DaoDeJing/epNN_*.jpg` | 配图素材（gitignore，本地） |

**跨期规则**：往期成片已用图自动排除；EP03+ 可从 EP01/EP02 **未用图** 中挑选，不必每期新拍 22 张。

```bash
# 合并/刷新统一图库
python3 scripts/build_image_catalog.py
python3 scripts/build_image_catalog.py --episode 3   # 顺带看 EP03 可用池
```

## 文案

- 语气： uncomfortable 提问 + 现代类比（AI、App、身份标签），非国学腔
- 每期收束带 **协议三步** + **下期预告**
- 先导承接上期；closing 回顾三件事

## 配图

```bash
# 图鉴格式（ep02）：filename + scene_concept；脚本会自动补 file 路径
python3 scripts/match_storyboard_images.py \
  assets/DaoDeJing/ep02_image_catalog.json \
  examples/ep02_beats.json \
  -o examples/ep02_image_matches.json
```

自动打分在 `description` 为空时效果差 → **按 scene_concept 语义手动定稿**，写入 `epNN_image_matches.json` 后批量更新 22beats 的 `image` 字段。

## 一键出片（EP03+）

```bash
# 1. 配图预览（从统一图库挑未用图，自动排除 EP01/EP02 已用）
python3 scripts/make_episode.py 3

# 2. 确认 examples/ep03_image_matches.json 后渲染（Edge TTS）
python3 scripts/make_episode.py 3 --render

# 新增 ep03_*.jpg 后刷新图库
python3 scripts/make_episode.py 3 --refresh-catalog
```

脚本会：扫描图库 → 去重 → 写 matches → 生成 22beats → `output/ep03-draft/` 成片 + `assets/covers/daodejing-ep03-cover.jpg`。

## 渲染（手动）

```bash
# 草稿：Edge TTS（分镜 tts 仅 voice + rate，不写 provider）
python3 -m pipeline examples/storyboard-daodejing-ep02-22beats.json \
  --work-dir output/ep02-draft/.work \
  --output-dir output/ep02-draft

# 定稿：Volcengine（与 EP01 一致）
# "tts": { "provider": "volcengine", "voice": "zh_male_ruyaqingnian_uranus_bigtts", ... }

# 只换画面/字幕：--skip-tts；改 cues 时删 .work/audio/*.cues.json
```

## 封面与字幕（brand 默认）

| 常量 | 值 | 说明 |
|------|-----|------|
| `COVER_HOOK_FONT_SIZE` | 104 | 片头 hook 大字 |
| `COVER_SUBTITLE_FONT_SIZE` | 52 | 系列名 |
| `COVER_BRAND_SEAL_RATIO` | 0.065 | 片头红色印章 |
| `SUBTITLE_FONT_SIZE` | 58 | 单行大字幕 |
| `SUBTITLE_MAX_LINES` | 1 | 禁止两行 |
| `SUBTITLE_MAX_WIDTH_RATIO` | 0.94 | 尽量一行放下 |

片头 cover：`render_cover_hook_slide` 在系列名前加 **Logo 红色印章**（`prepare.py` 传入 `logo_path`）。

## 发布

成片若在 `output/ep02-draft/`，上传时 **必须** 指定 `--video` 与 `--audio-dir`：

```bash
VIDEO="output/ep02-draft/观念黑盒——道德经五讲之二.mp4"
AUDIO="output/ep02-draft/.work/audio"
SB="examples/storyboard-daodejing-ep02-22beats.json"

# YouTube（OAuth：credentials/youtube_token.json）
python3 scripts/upload_youtube.py "$SB" --video "$VIDEO" --audio-dir "$AUDIO"

# B 站（凭据：credentials/bilibili_credential.json）
python3 scripts/upload_bilibili.py "$SB" --video "$VIDEO" --audio-dir "$AUDIO" --upload
```

元数据来自分镜 `youtube` / `bilibili` / `cover` 字段；时间轴依赖 `audio_dir` 下各 scene 的 mp3 时长。

## 与其它 skill

- 分镜字段：`ai-youtuber-storyboard`
- BGM：`ai-youtuber-bgm`
- YouTube OAuth 细节：`ai-youtuber-youtube`
