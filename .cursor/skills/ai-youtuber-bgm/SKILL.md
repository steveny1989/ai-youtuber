---
name: ai-youtuber-bgm
description: >-
  Mix background music from assets/BGM into pipeline videos with crossfades at
  chapter boundaries. Use when adding BGM, 背景音乐, assets/BGM, mix_bgm,
  flute/guzheng tracks, or smooth audio transitions between storyboard sections.
---

# BGM 混音

成片在 `concat` 旁白轨之后，由 `pipeline/bgm.py` 自动混入 `assets/BGM/` 里的配乐。

## Storyboard 配置

```json
"bgm": {
  "enabled": true,
  "tracks": [
    "assets/BGM/Music_fx_relaxing_chinese_flute.wav",
    "assets/BGM/Music_fx_relaxing_chinese_guzheng.wav"
  ],
  "volume": 0.16,
  "crossfade_sec": 4,
  "fade_in_sec": 1.5,
  "fade_out_sec": 4,
  "switch_at_scene": "open-2"
}
```

| 字段 | 说明 |
|------|------|
| `tracks` | 按顺序使用；在 `switch_at_scene` 镜头起点 **crossfade** 切到下一首 |
| `volume` | BGM 电平（0.1–0.2 常见，勿压过人声） |
| `crossfade_sec` | 两轨衔接交叉淡化时长 |
| `fade_in_sec` / `fade_out_sec` | 全片 BGM 首尾淡入淡出 |
| `switch_at_scene` | 切换镜头 id（如 `open-2`）；留空则均分整片时长 |

## 行为说明

- BGM 短于成片时会 **循环**，再在衔接处 `acrossfade`（三角曲线）。
- 与人声 `amix`，`dropout_transition=2` 减轻硬切。
- 仅替换 BGM：改 JSON 后 `python -m pipeline <json> --skip-tts`（需已有 `output/audio` 与 segments）。

## 片头

- 时长：`cover.duration_sec`（默认 3 秒）
- 标题字号：`brand.HOME_TITLE_FONT_SIZE`（默认 68）

## 文件

- 实现：`pipeline/bgm.py`
- 默认曲目：`assets/BGM/*.wav`
