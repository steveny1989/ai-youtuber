---
name: ai-youtuber-daodejing-chapter-hybrid
description: >-
  Hybrid single-chapter 道德经精解: Volcengine read (Chapter_N animation) +
  pipeline commentary (still images, timed subtitles, full-video BGM). Use for
  观念黑盒 chapter hybrid, build_chapter_hybrid.py, ch01/ch02 commentary
  storyboard, 朗读+讲解, or 八十一讲单章精解.
---

# 道德经单章精解 · 混合版

**朗读段**（水墨动画 + 火山慢速原文）+ **讲解段**（静图 + 逐句字幕 + 片尾 avatar）+ **全片 BGM**。

## 成片时长

**目标 ≥5 分钟**（朗读 ~20–40s + 讲解 ≥1150 字 + 片尾 4s）。ch01 级分镜约 1600 字 → ~6 分钟；ch11–15 若仅 ~650 字会只有 ~3 分钟，需加长讲解稿或重生成。

生成脚本校验：`scripts/hybrid_storyboard_util.py` 中 `MIN_COMMENTARY_CHARS = 1150`；镜间 `pause_after_sec` 建议 0.48–0.65。

**讲解稿质检（render 前必跑）**：

```bash
python3 scripts/review_commentary.py --chapters 31-40
# 批量洗稿（只改 narration，保留配图）：
python3 scripts/clean_commentary_batch.py --chapters 31-40 --write
```

见 skill `ai-youtuber-commentary-review`；ch31+ 勿用 `_expand_for_7min` 机械尾句垫字数。加长用 `scripts/commentary_quality.py` 的 `SCENE_ENRICHMENTS` 本章专属句。`write_chapters(..., require_review=True)` 写分镜前会自动跑 review。

## 成片结构（约 5–6 分钟）

| 段 | 时长 | 实现 |
|----|------|------|
| 朗读 | ~20–25s | `Chapter_N_v6.mp4` + 火山 TTS `read_rate: -18%` |
| 过渡 · 总纲 | ~40s | intro-bridge |
| 逐句黑盒解读 | ~3.5min | s1–s5（**勿用 scene_type: chapter**，会覆盖 image） |
| 东西方互证 | ~1min | open-ext1 + 配图 |
| 现代例子 | ~1.5min | open-ext2 + s-ext2 |
| 认知补丁收束 | ~40s | open-close |
| 片尾 | 4s | ending avatar |

## 讲解稿模板（观念黑盒视角）

每章按 **底层认知逻辑** 写，不是文学赏析：

1. **总纲**：本章在 81 章系统中的位置；承上（预告上章）启下
2. **逐句/逐段破译**（5 镜）：直译 → 黑盒隐喻 → 一句现代启示
3. **东西方互证**：1 位西方 + 1 位东方互证，控制在 ~220 字
4. **现代例子**：概念病 / 标签 / 商业，~350 字
5. **四条认知补丁**收束 + 下章预告

**禁止**在延伸段使用 `scene_type: "chapter"`——`prepare.py` 会强制生成章节卡，忽略 `image`。

## 文件约定

| 文件 | 用途 |
|------|------|
| `assets/DaoDeJing/taoteching_full.json` | 原文 |
| `assets/DaoDeJing/daodejing_81_commentary.json` | 各章 `mode: hybrid` 配置 |
| `examples/storyboard-daodejing-chNN-commentary.json` | 讲解分镜（渲染用） |
| `output/chNN-hybrid/segments/chNN-read.mp4` | 朗读段 |
| `output/daodejing-chNN-hybrid.mp4` | 成片 |

`daodejing_81_commentary.json` 每章 hybrid 字段：

```json
"2": {
  "title": "天下皆知美之为美",
  "mode": "hybrid",
  "read_rate": "-18%",
  "storyboard": "examples/storyboard-daodejing-ch02-commentary.json",
  "sections": { "plain": "…", "east_west": "…", "modern": "…", "closing": "…" }
}
```

## 分镜 JSON 要点

```json
{
  "tts": {
    "provider": "volcengine",
    "voice": "zh_male_ruyaqingnian_uranus_bigtts",
    "resource_id": "seed-tts-2.0",
    "emotion": "narrator",
    "rate": "-5%"
  },
  "bgm": {
    "enabled": false,
    "tracks": [
      "assets/BGM/Music_fx_relaxing_chinese_flute.wav",
      "assets/BGM/Music_fx_relaxing_chinese_guzheng.wav"
    ],
    "volume": 0.14,
    "crossfade_sec": 5,
    "fade_in_sec": 2.5,
    "fade_out_sec": 5,
    "switch_at_scene": "open-ext1"
  },
  "cover": { "enabled": false },
  "scenes": [
    { "id": "intro-bridge", "narration": "…", "image": "assets/DaoDeJing/ep02_….jpg" },
    { "id": "s1", "narration": "…", "image": "…" }
  ]
}
```

- 讲解段 `bgm.enabled: false`（避免与全片 BGM 双重混音）；`build_chapter_hybrid.py` 在最终拼接后统一混入
- 配图见下方 **语义配图规则**（勿用亮度排序批量 `--force` 旧脚本）

## 语义配图规则（81 讲讲解段）

图库约 **527 张**（`assets/DaoDeJing/` + `image_catalog.json`）。选配须同时满足：

| 规则 | 说明 |
|------|------|
| **语义匹配** | 旁白 ↔ 图义：中文文件名、`plc_/wat_` 英文补义（`FILENAME_HINTS`）、catalog `description_zh`；不依赖章标签 |
| **三章冷却** | 同图在 **chN** 出现后，**chN+1～chN+3 禁用**，**chN+4** 起可用（例：ch01 用过 → ch05 可用） |
| **本章主图优先** | 下章预告占用过的 `Ch(N+1)` 标签图，回到 chN+1 的 intro/s1 时允许复用（冷却豁免） |
| **预告不抢主图** | `open-close` 禁用带 **Ch(N+1)** 标签的图，留给下一章 intro |
| **max_reuse = 3** | 全系列单图最多 3 次；少量跨章复用可接受，禁止几十章共用一张 |
| **章内 11 镜不重复** | 每章 intro-bridge … open-close 各一图 |
| **路径必须存在** | 分镜 `image` 须能解析到磁盘文件；**默认无图则 render 中止**（需显式 `--allow-missing-images` 才黑底） |

**命令：**

```bash
# 旧路径 → 磁盘「… - chNN - 通用.jpg」对齐（改 storyboard JSON）
python3 scripts/align_storyboard_image_paths.py --chapters 62-70

# 全系列语义重分配（改 scenes[].image，保留 narration/motion）
python3 scripts/redistribute_storyboard_images.py --chapters 1-81 --max-reuse 3

# 审查：冷却 / 语义分 / 磁盘缺失
python3 scripts/audit_storyboard_images.py --chapters 60-70

# 改完分镜后重渲讲解段（无图默认失败）
python3 scripts/build_chapter_hybrid.py --chapter N --skip-tts
# 或批量: ./scripts/rerender_hybrid_chapters.sh 62 70
```

**勿用：** `fix_missing_storyboard_images.py --force` 按亮度补位——会导致「漫天白雪」等少数亮图霸屏。

**手动锁定：** 在 storyboard 里直接写死 `scenes[].image`；重跑 redistribute 会覆盖，需先备份或后续加 `--lock-file`。
- 字幕：`subtitle_max_lines: 1`，`subtitle_font_size: 58`

## 命令

```bash
# 整章出片（朗读 + 讲解 + 全片 BGM）
python3 scripts/build_chapter_hybrid.py --chapter 2

# 仅重录朗读（火山，-18%）
python3 scripts/build_chapter_hybrid.py --chapter 2 --reread --skip-tts

# 仅重渲染讲解（改文案/配图后）
python3 scripts/build_chapter_hybrid.py --chapter 2 --skip-read

# 复用已有 TTS，只换画面
python3 -m pipeline examples/storyboard-daodejing-ch02-commentary.json \
  --work-dir output/ch02-hybrid/commentary.work \
  --output-dir output/ch02-hybrid/commentary --skip-tts
# 然后手动拼接或再跑 hybrid --skip-tts
```

## 新建一章 checklist

1. 写讲解稿（总纲 + 5 段破译 + 互证 + 现代 + 四条补丁）
2. 创建 `examples/storyboard-daodejing-chNN-commentary.json`（参照 ch01）
3. 在 `daodejing_81_commentary.json` 加 `"mode": "hybrid"` 与 storyboard 路径
4. 在 `build_chapter_hybrid.py` 的 `read_narration()` 加该章朗读稿（句号停顿、无「第 N 章」）
5. `python3 scripts/generate_chNN_MM_storyboards.py`（或手写分镜，讲解总字数 ≥1150）
6. `python3 scripts/build_chapter_hybrid.py --chapter N`
7. 试听：总时长 ≥5 分钟、朗读语速、延伸段是否误用章节卡、BGM 切换点（open-ext1）

## 八十一讲连续播放（播放列表 / 合集）

各章仍是独立稿件；连续观看靠 **YouTube 播放列表** + **B 站合集/视频列表**。

1. **YouTube**：Studio 建播放列表「道德经八十一讲」，复制 `playlist_id`（`PL…`）到 `assets/DaoDeJing/series_daodejing_81.json` 的 `youtube_playlist_id`，或设 `YOUTUBE_PLAYLIST_DAODEJING_81`。
2. **B 站（API 可自动）**：`python3 scripts/setup_daodejing_81_series.py --list-bilibili` 查 `series_id`（旧版「视频列表」），写入 `bilibili_series_id`。空间页「合集·XXX」用 `season_id` 对照，排序多在创作中心手动。
3. **写入 ch01–50 分镜**：`python3 scripts/setup_daodejing_81_series.py --patch-storyboards`
4. **新上传**：`upload_youtube.py` / `upload_bilibili.py` 会自动加入列表并登记到 `output/series_daodejing_81_registry.jsonl`。
5. **已上传补登记**：`python3 scripts/setup_daodejing_81_series.py --register 3 --youtube-id VIDEO_ID --bilibili-aid AID`
6. **批量同步进列表**：`python3 scripts/setup_daodejing_81_series.py --sync --chapters 1-50`

## 与其它 skill

- 五讲长片 22 镜：`ai-youtuber-daodejing-episode`
- 分镜字段：`ai-youtuber-storyboard`
- BGM 细节：`ai-youtuber-bgm`
- 讲解段氛围层（浮尘 / 水墨缘晕 / 水面粼光）：`ai-youtuber-ambient`
- 经典版（同章动画循环讲解）：`assets/DaoDeJing/COMMENTARY_SERIES.md`
