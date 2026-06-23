---
name: ai-youtuber-youtube
description: >-
  Upload rendered videos to YouTube via Data API v3 OAuth. Use for YouTube
  upload, 上传 YouTube, video metadata, description, tags, playlist, OAuth.
---

# YouTube 上传

## 一次性配置

见 `credentials/README.md`：启用 YouTube Data API v3，下载 OAuth 桌面客户端 `client_secret.json`。

```bash
pip install google-api-python-client google-auth-oauthlib
python scripts/upload_youtube.py --auth-only
```

## 上传

```bash
# API 上传（默认 requests，支持 HTTPS_PROXY）
python scripts/upload_youtube.py

# 网络不稳：导出元数据，Studio 网页手动传 mp4
python scripts/upload_youtube.py --export-metadata

# 先看元数据
python scripts/upload_youtube.py --dry-run

# 设为公开（默认 unlisted）
python scripts/upload_youtube.py --privacy public
```

SSL 超时 → 用 `--export-metadata` + Studio，或 `export HTTPS_PROXY=...` 后重试。

## Storyboard `youtube` 字段

| 字段 | 说明 |
|------|------|
| `privacy_status` | `private` / `unlisted` / `public` |
| `category_id` | `27` = 教育 |
| `tags` | 最多约 30 个 |
| `description_intro` | 简介开头段落 |
| `description_footer` | 简介末尾（订阅、话题标签） |
| `timeline` | `[{ "scene": "open-1", "label": "03 论点一 · …" }]` 按分镜 id 打点 |
| `timeline_heading` | 时间轴标题（默认含「点击跳转」提示） |
| `playlist_id` | 上传后加入播放列表（可选） |

时间戳由 `output/audio/{scene_id}.mp3` 时长累加（含 cover 静音片头）。未配置 `timeline` 时，对 `intro-*` / `open-*` / `protocol-1` / `closing-1` 等自动打点；也可在单镜加 `timestamp_label`。

标题来自顶层 `title`；简介含 `cover.hook`、本期说明、章节时间轴、频道品牌文案（`channel_about_zh/en`、`channel_url`）。

OAuth 请用 **@观念黑盒** 频道对应的 Google 账号登录。
