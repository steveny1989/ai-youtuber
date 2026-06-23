---
name: ai-youtuber-commentary-review
description: >-
  Review 观念黑盒 hybrid commentary narration before render/upload. Use for
  讲解稿质检, storyboard narration review, 垫字, 观念黑盒文本, review_commentary.py,
  or checking ch31+ long_form scripts.
---

# 观念黑盒 · 讲解稿质检

## 你在检什么

**对象**：`examples/storyboard-daodejing-chNN-commentary.json` 里各镜 `narration`（不含片尾 avatar）。

**目标**：口播像一集完整的「观念黑盒」精解，而不是：
- 为凑字数机械粘贴的套话
- 与本章无关的跨章引用
- 听感像作业/元说明的句子
- 单屏字幕放不下的超长句

**不是**：文学考据满分、引文逐字对应王弼注本。

## 自动评审（先跑）

```bash
# 单章
python3 scripts/review_commentary.py examples/storyboard-daodejing-ch36-commentary.json

# 批量
python3 scripts/review_commentary.py --chapters 31-40

# CI / 生成后门禁
python3 scripts/review_commentary.py --chapters 36-40 --fail-under 72
```

**及格**：评分 ≥72 且无 `error`。分数由规则扣分，见脚本内 `BOILERPLATE_PATTERNS`。

## Agent 人工复核清单（5 维）

每章过一遍，每维打 **OK / 需改**：

| 维 | OK 标准 | 常见 FAIL |
|----|---------|-----------|
| **1. 结构** | 11 镜齐全；intro 承上章；open-close 四条补丁 + 下章预告 | 缺镜、intro 未接上一章 |
| **2. 本章锚点** | s1–s5 能对应本章原文关键句，不是万能哲学 | 全文可搬到任意章 |
| **3. 观念黑盒声线** | 系统/黑盒/补丁语言；短句口播；少「请写笔记/对照本周」 | 作业式元指令、客服腔 |
| **4. 无垫字污染** | 同一句套话不在 11 镜里重复出现 | `_expand_for_7min` 尾句每镜一遍 |
| **5. 可播性** | 每句 ≤~55 字为宜；open-1 一句；ext 有具体现代例 | 一句 120 字、英文名乱入 |

## 一票否决（必须改完再 render）

- 全章重复 ≥8 次的同套垫字（如「请对照本周一个真实决策…」）
- 非 ch26 出现「失本或失君」
- 破译段几乎不碰本章原文
- open-ext1 只有人名堆叠、无论证

## 推荐工作流

```
写/生成 narration（CHAPTER_META + apply_scene_enrichments，勿 _expand_for_7min）
    → python3 scripts/review_commentary.py（自动）
    → 若 ch31+ 批量污染：python3 scripts/clean_commentary_batch.py --chapters 31-40 --write
    → Agent 按上表 5 维补评 + 给修改 diff 建议
    → 再跑 review 直到 PASS
    → build_chapter_hybrid.py
```

`clean_commentary_batch.py` **只改 narration**，保留配图/tts/youtube；适合已 render 过的章只洗稿不重配。

## 修改原则

1. **加长靠内容**，不靠 `_expand_for_7min` 通用尾句；宁可加本章案例、多一句原文白话。
2. **垫字只留 0–1 处**：若要有「写一条对照」，只放在 `open-close` 或 `s-ext2` 一次。
3. **互证/现代段**必须本章专属（如 ch36 写诱饵/固张，别写「失本失君」）。
4. 参照 **ch01–ch10** 分镜密度与干净度；ch31+ long_form 需人工删垫字。

## 输出格式（Agent 给用户的意见）

```markdown
## ch36 评审 — FAIL 38/100

### 必须改
- [homework_tail] 11 镜均含「请对照本周…」→ 删除，仅在 open-close 保留一句

### 建议改
- [weak_source_coverage] s3 未引「柔弱胜刚强」原文 → 首句加引号
- [subtitle_too_long] intro-bridge 最长句 92 字 → 拆两句

### 可保留
- 承上 ch35「执大象」✓
- open-ext2 平台补贴例 ✓
```
