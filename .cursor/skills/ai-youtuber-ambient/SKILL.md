---
name: ai-youtuber-ambient
description: >-
  Add ambient atmosphere layers (浮尘光束 / 水墨缘晕 / 水面粼光) to pipeline
  commentary videos via screen-blend baking on pan motion. Use when tuning
  ambient, 氛围层, 浮尘, dust_light, ink_mist, water_shimmer, ambient.py,
  motion_amb, or making hybrid chapter visuals more atmospheric.
---

# 氛围层（Ambient）

讲解段推轨画面之上叠加轻量动态氛围。实现于 `pipeline/ambient.py`，在 `pipeline/render.py` 推轨完成后 **单独烘焙** 进 `{scene}_motion_amb.mp4`，再叠水印/字幕。

**朗读段不加氛围**（hybrid 仅 commentary storyboard 生效）。

## Storyboard 配置

```json
"ambient": {
  "enabled": true,
  "dust_opacity": 0.15,
  "ink_opacity": 0.07,
  "water_opacity": 0.09
}
```

| 字段 | 说明 |
|------|------|
| `enabled` | 总开关；`false` 跳过全部氛围 |
| `dust_opacity` | 浮尘光束 screen 强度（当前推荐 **0.15**；曾验 0.10 偏淡） |
| `ink_opacity` | 水墨缘晕（intro-bridge / open-close） |
| `water_opacity` | 水面粼光（水柔章 + 指定镜头） |
| `water_chapters` | 可选；默认见下表内置列表 |

新建 hybrid 分镜时 `scripts/hybrid_storyboard_util.py` 已写入上述 `ambient` 块。

## 三种 preset

| preset | 中文 | 视觉 |
|--------|------|------|
| `dust_light` | 浮尘光束 | 斜向柔光 + 飘动微粒 |
| `ink_mist` | 水墨缘晕 | 缘边淡雾慢漂 |
| `water_shimmer` | 水面粼光 | 画面下方波纹亮线 |

循环素材：`assets/ambient/loops/{preset}_{W}x{H}_v4.mp4`（首次渲染自动生成，6s 循环）。

## 镜头分配（`resolve_ambient_layer`）

| 镜头 id | preset |
|---------|--------|
| `intro-bridge`, `open-close` | `ink_mist` |
| `open-1`, `s1`–`s5`, `open-ext1`, `open-ext2`, `s-ext2` | `dust_light` |
| `s2`, `open-ext2` **且** 章号 ∈ 水柔章 | `water_shimmer`（覆盖 dust） |
| `cover`, `ending` | 无 |
| 朗读段 / 静态帧（无推轨） | 无 |

**水柔章默认**：8, 10, 28, 43, 55, 61, 66, 76, 78。

## 渲染栈

```
推轨 motion.mp4 → composite_ambient_on_video → motion_amb.mp4 → 水印 → 字幕 → segment.mp4
```

- 仅 **kenburns/pan 推轨** 场景烘焙氛围。
- 混合方式：**`blend=all_mode=screen`** + `colorkey` 抠黑底。
- **禁止** 用 `overlay` + 低 `colorchannelmixer aa`——稀疏浮尘在暗底上肉眼不可见（已踩坑）。

## 调强度

1. 改 storyboard 里 `dust_opacity` / `ink_opacity` / `water_opacity`（screen 值，常用 0.07–0.18）。
2. 改 preset 视觉：编辑 `pipeline/ambient.py` 中 `_frame_dust` / `_frame_ink_mist` / `_frame_water_shimmer`，并 **递增 `LOOP_VERSION`** 以强制重生成循环 mp4。
3. 重渲：

```bash
# 单章 hybrid（已有 TTS 可 skip）
python3 scripts/build_chapter_hybrid.py --chapter 55 --skip-tts

# 或纯讲解 storyboard
python -m pipeline examples/storyboard-daodejing-ch55-commentary.json --skip-tts
```

## 验收

对比推轨与烘焙产物（应有明显亮部差异）：

```bash
ffmpeg -y -ss 10 -i output/ch55-hybrid/commentary.work/segments/s1_motion.mp4 -frames:v 1 /tmp/m.jpg
ffmpeg -y -ss 10 -i output/ch55-hybrid/commentary.work/segments/s1_motion_amb.mp4 -frames:v 1 /tmp/a.jpg
# 目视 /tmp/m.jpg vs /tmp/a.jpg；或 Python 算 diff mean+ > 5 即正常
```

中间文件：`commentary.work/segments/{scene}_motion_amb.mp4` 应存在。

## 相关文件

| 文件 | 作用 |
|------|------|
| `pipeline/ambient.py` | preset、循环生成、`composite_ambient_on_video` |
| `pipeline/render.py` | 推轨后调用烘焙 |
| `pipeline/models.py` | `AmbientConfig` 默认值 |
| `schemas/storyboard.schema.json` | JSON schema |
| `scripts/hybrid_storyboard_util.py` | 新章默认 `ambient` 块 |
