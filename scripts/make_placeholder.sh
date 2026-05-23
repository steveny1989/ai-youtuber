#!/usr/bin/env bash
# 生成示例占位图：正文底图 + 首页（Logo + 标题）
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/.venv/bin/python"
if [[ ! -x "$PY" ]]; then
  PY="$(command -v python3)"
fi
exec "$PY" "$ROOT/scripts/make_placeholder.py" "$@"
