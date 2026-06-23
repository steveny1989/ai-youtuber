#!/bin/bash
# 庄子内篇系列 YouTube 批量上传（定时发布）
set -e
cd "$(dirname "$0")/.."
source .venv/bin/activate

echo "=========================================="
echo "  庄子内篇系列 · YouTube 批量上传"
echo "  发布计划：7月1日起每两天一篇"
echo "=========================================="

echo ""
echo ">>> [1/6] 齐物论 → 2026-07-01 08:00"
python3 scripts/upload_youtube.py \
  examples/storyboard-zhuangzi-qiwulun.json \
  --video output/qiwulun/zhuangzi-qiwulun-30min.mp4 \
  --publish-at "2026-07-01T08:00:00+08:00" \
  --privacy private

echo ""
echo ">>> [2/6] 养生主 → 2026-07-03 08:00"
python3 scripts/upload_youtube.py \
  examples/storyboard-zhuangzi-yangshengzhu.json \
  --video output/yangshengzhu/zhuangzi-yangshengzhu-30min.mp4 \
  --publish-at "2026-07-03T08:00:00+08:00" \
  --privacy private

echo ""
echo ">>> [3/6] 人间世 → 2026-07-05 08:00"
python3 scripts/upload_youtube.py \
  examples/storyboard-zhuangzi-renjianshi.json \
  --video output/renjianshi/zhuangzi-renjianshi-30min.mp4 \
  --publish-at "2026-07-05T08:00:00+08:00" \
  --privacy private

echo ""
echo ">>> [4/6] 德充符 → 2026-07-07 08:00"
python3 scripts/upload_youtube.py \
  examples/storyboard-zhuangzi-dechongfu.json \
  --video output/dechongfu/zhuangzi-dechongfu-30min.mp4 \
  --publish-at "2026-07-07T08:00:00+08:00" \
  --privacy private

echo ""
echo ">>> [5/6] 大宗师 → 2026-07-09 08:00"
python3 scripts/upload_youtube.py \
  examples/storyboard-zhuangzi-dazongshi.json \
  --video output/dazongshi/zhuangzi-dazongshi-30min.mp4 \
  --publish-at "2026-07-09T08:00:00+08:00" \
  --privacy private

echo ""
echo ">>> [6/6] 应帝王 → 2026-07-11 08:00"
python3 scripts/upload_youtube.py \
  examples/storyboard-zhuangzi-yingdiwang.json \
  --video output/yingdiwang/zhuangzi-yingdiwang-30min.mp4 \
  --publish-at "2026-07-11T08:00:00+08:00" \
  --privacy private

echo ""
echo "=========================================="
echo "  YouTube 全部上传完成！"
echo "  2026-07-01  齐物论"
echo "  2026-07-03  养生主"
echo "  2026-07-05  人间世"
echo "  2026-07-07  德充符"
echo "  2026-07-09  大宗师"
echo "  2026-07-11  应帝王"
echo "=========================================="
