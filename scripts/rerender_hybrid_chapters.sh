#!/usr/bin/env bash
# 批量重 render hybrid 成片（完整版：朗读 + 讲解 + BGM，跳过 TTS  regeneration）
# 用法:
#   ./scripts/rerender_hybrid_chapters.sh 1 81
#   ./scripts/rerender_hybrid_chapters.sh 1 39

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

FIRST="${1:-1}"
LAST="${2:-81}"
LOG="${ROOT}/output/batch-rerender-ch$(printf '%02d' "$FIRST")-$(printf '%02d' "$LAST").log"
mkdir -p "${ROOT}/output"

echo "Batch rerender ch${FIRST}–${LAST}（朗读+讲解+BGM，--skip-tts）→ ${LOG}"
echo "started $(date)" | tee "$LOG"

ok=0
fail=0
for ch in $(seq "$FIRST" "$LAST"); do
  printf '%02d' "$ch" | grep -q . || true
  work="${ROOT}/output/ch$(printf '%02d' "$ch")-hybrid/commentary.work/segments"
  if [[ -d "$work" ]]; then
    find "$work" -maxdepth 1 -name '*_motion*.mp4' -delete 2>/dev/null || true
  fi
  echo "" | tee -a "$LOG"
  echo "========== ch${ch} $(date) ==========" | tee -a "$LOG"
  if python3 scripts/build_chapter_hybrid.py --chapter "$ch" --skip-tts 2>&1 | tee -a "$LOG"; then
    ok=$((ok + 1))
  else
    fail=$((fail + 1))
    echo "FAILED ch${ch}" | tee -a "$LOG"
  fi
done

echo "" | tee -a "$LOG"
echo "done $(date)  ok=${ok} fail=${fail}" | tee -a "$LOG"
exit $(( fail > 0 ? 1 : 0 ))
