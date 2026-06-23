#!/bin/bash
# 每天上传 3 章到 YouTube + B 站（定时公开，间隔 3 小时）
# crontab 示例（每天 10:00）：
# 0 10 * * * /bin/bash "/Users/diyao/Desktop/AI YouTuber/scripts/run_daily_hybrid_upload_3.sh" >> "/Users/diyao/Desktop/AI YouTuber/output/upload-daily.log" 2>&1

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONUNBUFFERED=1
export HTTPS_PROXY="${HTTPS_PROXY:-http://127.0.0.1:7890}"

echo "=== $(date '+%Y-%m-%d %H:%M:%S %Z') 每日 3 章上传 ==="
python3 scripts/upload_hybrid_daily_3.py
