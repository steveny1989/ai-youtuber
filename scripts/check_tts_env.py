#!/usr/bin/env python3
"""检查 TTS 相关环境变量是否已配置（不打印密钥内容）。"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.env_util import load_dotenv  # noqa: E402


def _status(name: str) -> str:
    return "✓ 已设置" if os.environ.get(name, "").strip() else "✗ 未设置"


def main() -> int:
    load_dotenv()
    env_file = ROOT / ".env"
    print(f".env 文件: {env_file} ({'存在' if env_file.is_file() else '不存在'})")
    print()
    print("火山豆包（任选一种）:")
    print(f"  VOLCENGINE_API_KEY         {_status('VOLCENGINE_API_KEY')}")
    print(f"  VOLCENGINE_TTS_API_KEY     {_status('VOLCENGINE_TTS_API_KEY')}")
    print(f"  DOUBAO_TTS_APPID           {_status('DOUBAO_TTS_APPID')}")
    print(f"  DOUBAO_TTS_TOKEN           {_status('DOUBAO_TTS_TOKEN')}")
    print(f"  DOUBAO_TTS_RESOURCE_ID     {_status('DOUBAO_TTS_RESOURCE_ID')} (可选)")
    print()
    print("其他:")
    print(f"  GEMINI_API_KEY             {_status('GEMINI_API_KEY')}")
    ok = bool(
        os.environ.get("VOLCENGINE_API_KEY", "").strip()
        or os.environ.get("VOLCENGINE_TTS_API_KEY", "").strip()
        or (
            os.environ.get("DOUBAO_TTS_APPID", "").strip()
            and os.environ.get("DOUBAO_TTS_TOKEN", "").strip()
        )
    )
    if ok:
        print("\n火山 TTS 凭证齐全，可运行: python3 scripts/test_google_tts.py")
        return 0
    print("\n火山 TTS 凭证不完整。请编辑 .env 后保存，再运行本脚本确认。")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
