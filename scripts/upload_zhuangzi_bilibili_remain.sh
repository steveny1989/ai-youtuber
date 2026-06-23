#!/bin/bash
# 庄子内篇系列 B 站上传（续传，从养生主开始）
set -e
cd "$(dirname "$0")/.."
source .venv/bin/activate

echo "=========================================="
echo "  庄子内篇系列 · B 站续传（养生主→应帝王）"
echo "=========================================="

echo ""
echo ">>> [2/6] 养生主 → 2026-07-03 08:00"
python3 scripts/upload_bilibili.py \
  examples/storyboard-zhuangzi-yangshengzhu.json \
  --video output/yangshengzhu/zhuangzi-yangshengzhu-30min.mp4 \
  --upload \
  --publish-at "2026-07-03T08:00:00+08:00"

echo ""
echo ">>> [3/6] 人间世 → 2026-07-05 08:00"
python3 scripts/upload_bilibili.py \
  examples/storyboard-zhuangzi-renjianshi.json \
  --video output/renjianshi/zhuangzi-renjianshi-30min.mp4 \
  --upload \
  --publish-at "2026-07-05T08:00:00+08:00"

echo ""
echo ">>> [4/6] 德充符 → 2026-07-07 08:00"
python3 scripts/upload_bilibili.py \
  examples/storyboard-zhuangzi-dechongfu.json \
  --video output/dechongfu/zhuangzi-dechongfu-30min.mp4 \
  --upload \
  --publish-at "2026-07-07T08:00:00+08:00"

echo ""
echo ">>> [5/6] 大宗师 → 2026-07-09 08:00"
python3 scripts/upload_bilibili.py \
  examples/storyboard-zhuangzi-dazongshi.json \
  --video output/dazongshi/zhuangzi-dazongshi-30min.mp4 \
  --upload \
  --publish-at "2026-07-09T08:00:00+08:00"

echo ""
echo ">>> [6/6] 应帝王 → 2026-07-11 08:00"
python3 scripts/upload_bilibili.py \
  examples/storyboard-zhuangzi-yingdiwang.json \
  --video output/yingdiwang/zhuangzi-yingdiwang-30min.mp4 \
  --upload \
  --publish-at "2026-07-11T08:00:00+08:00"

echo ""
echo "=========================================="
echo "  B 站全部上传完成！"
echo "  BV号请查看 output/upload-zhuangzi-bilibili-remain.log"
echo "=========================================="
