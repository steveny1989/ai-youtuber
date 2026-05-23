# Storyboard 示例

## 最小可渲染

```json
{
  "title": "测试",
  "scenes": [
    { "id": "s1", "narration": "一句旁白", "image": "assets/placeholder.jpg" }
  ]
}
```

## 标准频道结构（与 `examples/storyboard.example.json` 一致）

```json
{
  "title": "AI 如何改变内容创作",
  "chapters": [
    { "id": "1", "label": "第一章" },
    { "id": "2", "label": "第二章" }
  ],
  "ending": {
    "enabled": true,
    "image": "assets/avatar.webp",
    "duration_sec": 4,
    "narration": ""
  },
  "scenes": [
    {
      "id": "intro",
      "scene_type": "intro",
      "narration": "大家好，今天我们聊……"
    },
    {
      "id": "ch1-open",
      "scene_type": "chapter",
      "chapter": "1",
      "narration": "第一部分……",
      "duration_sec": 3.5
    },
    {
      "id": "ch1-main",
      "narration": "展开内容……",
      "image": "assets/placeholder.jpg"
    },
    {
      "id": "ch2-open",
      "scene_type": "chapter",
      "chapter": "2",
      "narration": "第二部分……",
      "duration_sec": 3.5
    },
    {
      "id": "closing",
      "narration": "订阅我们，下期见。",
      "image": "assets/placeholder.jpg"
    }
  ]
}
```

## 单章快速开场（无 chapters 表）

```json
{
  "title": "本期标题",
  "scenes": [
    { "id": "intro", "scene_type": "intro", "narration": "开场" },
    {
      "id": "special",
      "scene_type": "chapter",
      "chapter_title": "核心观点",
      "narration": "进入正题",
      "duration_sec": 3
    }
  ]
}
```

生成：`assets/chapters/chapter-special.jpg`

## 从外部脚本转换（伪代码）

```text
FOR each section IN script:
  IF section.type == "opening": scene_type = "intro"
  ELIF section.type == "chapter": scene_type = "chapter", chapter = section.chapter_id
  ELSE: image = section.broll OR "assets/placeholder.jpg"
  EMIT { id, narration: section.voiceover, ... }
EMIT top-level title from script.title
EMIT chapters[] from script.chapter_list
```

输出路径建议：`examples/` 或用户指定的 `storyboards/xxx.json`。
