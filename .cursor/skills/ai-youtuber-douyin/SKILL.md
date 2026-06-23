---
name: ai-youtuber-douyin
description: >-
  抖音自动上传：登录保存 Cookie、单章上传、批量定时发布、横/竖封面自动生成。
  Use when working on 抖音, douyin, upload, 定时发布, 合集, 封面, batch upload.
---

# 抖音自动上传

基于 **patchright**（反检测 Playwright）模拟浏览器操作 creator.douyin.com，
全自动完成：视频上传 → 标题/描述/话题 → 横/竖封面 → 自主声明 → 合集 → 定时/立即发布。

## 两步走

### 第一步：登录（只需做一次，Cookie 约 30 天有效）

```bash
python3 scripts/upload_douyin.py --auth-only examples/storyboard-daodejing-ch01-commentary.json
```

弹出 Chrome 窗口，扫码登录，页面跳转后自动保存到 `credentials/douyin_cookie.json`。

### 第二步：上传单章

```bash
# dry-run 预览元数据
python3 scripts/upload_douyin.py examples/storyboard-daodejing-ch01-commentary.json --dry-run --video output/daodejing-ch01-hybrid.mp4

# 真实上传（立即发布）
python3 scripts/upload_douyin.py examples/storyboard-daodejing-ch01-commentary.json --upload --video output/daodejing-ch01-hybrid.mp4

# 定时发布
python3 scripts/upload_douyin.py examples/storyboard-daodejing-ch01-commentary.json --upload --video output/daodejing-ch01-hybrid.mp4 --publish-at '2026-06-25 20:00'
```

### 批量定时发布（81章）

```bash
# 预览排期
python3 scripts/batch_upload_douyin.py --dry-run

# 从第1章开始，每天3篇（08:00 / 12:00 / 20:00），自动加入合集
python3 scripts/batch_upload_douyin.py

# 从第10章断点续传
python3 scripts/batch_upload_douyin.py --start 10

# 自定义起始日期和合集名
python3 scripts/batch_upload_douyin.py --start-date 2026-07-01 --playlist "道德经八十一讲"
```

## 封面生成

抖音需要横封面（16:9）和竖封面（9:16）。

```bash
# 生成单章竖封面
python3 scripts/make_chapter_cover.py --chapter 1 --vertical --preview

# 批量生成 81 章竖封面
python3 scripts/make_chapter_cover.py --chapters 1-81 --vertical
```

封面输出路径：
- 横封面：`assets/covers/daodejing-ch{N:02d}-cover.jpg`（1920×1080）
- 竖封面：`assets/covers/daodejing-ch{N:02d}-cover-douyin.jpg`（1080×1920）

上传时自动检测竖封面文件，不存在则自动生成。

## 上传完整流程

`upload_video()` 按顺序执行：

| 步骤 | 操作 | 选择器 / 逻辑 |
|------|------|--------------|
| 1 | 进入上传页 | `creator.douyin.com/creator-micro/content/upload` |
| 2 | 选择视频 | `div[class^='container'] input` |
| 3 | 等待跳转发布页 | 轮询 v1/v2 publish URL |
| 4 | 填写标题 | `input[placeholder*='填写作品标题']`，最多 30 字 |
| 5 | 填写描述+话题 | `div.zone-container[contenteditable="true"]`，最多 5 个 #话题 |
| 6 | 等待转码完成 | `[class^="long-card"] div:has-text("重新上传")` |
| 7 | 横封面 | 弹窗 `div.dy-creator-content-modal` → 切 tab → `input.semi-upload-hidden-input` nth(1) |
| 8 | 竖封面 | 同上，切"设置竖封面" tab → nth(1) |
| 9 | 自主声明 | "内容为个人观点或见解" |
| 10 | 合集 | "添加到合集" 入口，按名称搜索选择 |
| 11 | 定时发布 | `[class^='radio']:has-text('定时发布')` + 时间输入 |
| 12 | 点击发布 | `button[name="发布"]`，等跳转 `/content/manage` |

## Storyboard 配置（`douyin` 字段）

```json
"douyin": {
  "tags": ["道德经", "老子", "观念黑盒", "哲学", "国学"],
  "description_intro": "本章精解……",
  "playlist": "道德经八十一讲",
  "comment_type": "open",
  "privacy": "public"
}
```

**Tags fallback 链**：
1. `douyin.tags`（非默认时）
2. `bilibili.tags`（自动复用，取前 5 个）

**Description fallback 链**：
1. `douyin.description_intro`
2. `bilibili.description_intro`
3. `youtube.description_intro`
4. 第一个 scene 旁白前 100 字

## 文件结构

```
pipeline/douyin_upload.py      # 核心上传逻辑（patchright async）
scripts/upload_douyin.py       # CLI 入口（单章）
scripts/batch_upload_douyin.py # 批量定时上传脚本
scripts/make_chapter_cover.py  # 封面生成（--vertical 生成竖封面）
credentials/douyin_cookie.json # Cookie 存储（勿提交 git）
assets/covers/*-cover-douyin.jpg  # 竖封面（1080×1920）
```

## 常见问题

**Cookie 失效**：
```bash
python3 scripts/upload_douyin.py --check-cookie examples/storyboard-xxx.json
# 失效则重新登录
python3 scripts/upload_douyin.py --auth-only examples/storyboard-xxx.json
```

**封面弹窗打不开**：正式上传流程会先按 Escape 收起话题联想下拉，再清 shepherd 浮层，然后 `force=True` 点击"选择封面"。

**合集不存在**：需在抖音创作者中心手动创建同名合集后，脚本才能搜索到并选择。

**批量上传风控**：`batch_upload_douyin.py` 两次上传之间默认等待 30 秒，可用 `--interval` 调整。
