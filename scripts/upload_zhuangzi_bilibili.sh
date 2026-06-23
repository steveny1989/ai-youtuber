#!/bin/bash
# 庄子内篇系列批量上传 B 站（定时发布）
set -e
cd "$(dirname "$0")/.."
source .venv/bin/activate

echo "=========================================="
echo "  庄子内篇系列 · B 站批量上传"
echo "  发布计划：7月1日起每两天一篇"
echo "=========================================="

# 1. 齐物论 2026-07-01
echo ""
echo ">>> [1/6] 齐物论 → 2026-07-01 08:00"
python3 scripts/upload_bilibili.py \
  examples/storyboard-zhuangzi-qiwulun.json \
  --video output/qiwulun/zhuangzi-qiwulun-30min.mp4 \
  --upload \
  --publish-at "2026-07-01T08:00:00+08:00"

# 2. 养生主 2026-07-03
echo ""
echo ">>> [2/6] 养生主 → 2026-07-03 08:00"
python3 scripts/upload_bilibili.py \
  examples/storyboard-zhuangzi-yangshengzhu.json \
  --video output/yangshengzhu/zhuangzi-yangshengzhu-30min.mp4 \
  --upload \
  --publish-at "2026-07-03T08:00:00+08:00"

# 3. 人间世 2026-07-05
echo ""
echo ">>> [3/6] 人间世 → 2026-07-05 08:00"
python3 scripts/upload_bilibili.py \
  examples/storyboard-zhuangzi-renjianshi.json \
  --video output/renjianshi/zhuangzi-renjianshi-30min.mp4 \
  --upload \
  --publish-at "2026-07-05T08:00:00+08:00"

# 4. 德充符 2026-07-07
echo ""
echo ">>> [4/6] 德充符 → 2026-07-07 08:00"
python3 scripts/upload_bilibili.py \
  examples/storyboard-zhuangzi-dechongfu.json \
  --video output/dechongfu/zhuangzi-dechongfu-30min.mp4 \
  --upload \
  --publish-at "2026-07-07T08:00:00+08:00"

# 5. 大宗师 2026-07-09
echo ""
echo ">>> [5/6] 大宗师 → 2026-07-09 08:00"
python3 scripts/upload_bilibili.py \
  examples/storyboard-zhuangzi-dazongshi.json \
  --video output/dazongshi/zhuangzi-dazongshi-30min.mp4 \
  --upload \
  --publish-at "2026-07-09T08:00:00+08:00"

# 6. 应帝王 2026-07-11
echo ""
echo ">>> [6/6] 应帝王 → 2026-07-11 08:00"
python3 scripts/upload_bilibili.py \
  examples/storyboard-zhuangzi-yingdiwang.json \
  --video output/yingdiwang/zhuangzi-yingdiwang-30min.mp4 \
  --upload \
  --publish-at "2026-07-11T08:00:00+08:00"

echo ""
echo "=========================================="
echo "  B 站上传全部完成！"
echo "  2026-07-01  齐物论"
echo "  2026-07-03  养生主"
echo "  2026-07-05  人间世"
echo "  2026-07-07  德充符"
echo "  2026-07-09  大宗师"
echo "  2026-07-11  应帝王"
echo "=========================================="
