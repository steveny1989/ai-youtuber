#!/bin/bash
# 5 月 30 日 08:00 开始上传第 6–10 章（YouTube + B 站）
# 定时公开：5/30 09:00 起每天一集（留 1 小时上传缓冲）
# 安装：crontab -e 加入下面一行（路径按实际修改）
# 0 8 30 5 * /bin/bash "/Users/diyao/Desktop/AI YouTuber/scripts/run_scheduled_hybrid_upload.sh" >> "/Users/diyao/Desktop/AI YouTuber/output/scheduled-upload.log" 2>&1

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONUNBUFFERED=1

echo "=== $(date '+%Y-%m-%d %H:%M:%S %Z') 开始定时上传 ch06-10 ==="

python3 scripts/upload_hybrid_batch.py \
  --chapters 6-10 \
  --publish-start 2026-05-30T09:00:00+08:00 \
  --interval-days 1

echo "=== $(date '+%Y-%m-%d %H:%M:%S %Z') 完成 ==="
