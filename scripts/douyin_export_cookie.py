#!/usr/bin/env python3
"""从系统 Chrome Cookie 数据库导出抖音 Cookie，转为 Playwright storage_state 格式。

需要先关闭 Chrome，或者脚本会复制 DB 文件再读（避免锁定）。
"""
import json, shutil, sqlite3, tempfile, os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COOKIE_OUT = ROOT / "credentials" / "douyin_cookie.json"
COOKIE_OUT.parent.mkdir(parents=True, exist_ok=True)

CHROME_COOKIE_DB = Path.home() / "Library/Application Support/Google/Chrome/Default/Cookies"

if not CHROME_COOKIE_DB.is_file():
    sys.exit(f"找不到 Chrome Cookie 数据库: {CHROME_COOKIE_DB}")

# 复制一份避免锁定
tmp = tempfile.mktemp(suffix=".db")
shutil.copy2(CHROME_COOKIE_DB, tmp)

try:
    con = sqlite3.connect(tmp)
    cur = con.execute("""
        SELECT host_key, name, value, path, expires_utc, is_secure, is_httponly, samesite
        FROM cookies
        WHERE host_key LIKE '%douyin.com%'
    """)
    rows = cur.fetchall()
    con.close()
finally:
    os.unlink(tmp)

if not rows:
    sys.exit("未找到抖音 Cookie，请确认已在 Chrome 里登录 creator.douyin.com")

print(f"找到 {len(rows)} 条抖音 Cookie", flush=True)

cookies = []
for host_key, name, value, path, expires_utc, is_secure, is_httponly, samesite in rows:
    # Chrome 时间戳是从 1601-01-01 开始的微秒数，转为 Unix 时间戳（秒）
    expires = (expires_utc / 1_000_000) - 11644473600 if expires_utc else -1
    samesite_map = {0: "None", 1: "Lax", 2: "Strict", -1: "None"}
    cookies.append({
        "name": name,
        "value": value,
        "domain": host_key if host_key.startswith(".") else host_key,
        "path": path,
        "expires": expires,
        "httpOnly": bool(is_httponly),
        "secure": bool(is_secure),
        "sameSite": samesite_map.get(samesite, "None"),
    })

storage_state = {
    "cookies": cookies,
    "origins": []
}

COOKIE_OUT.write_text(json.dumps(storage_state, ensure_ascii=False, indent=2))
print(f"✓ Cookie 已保存: {COOKIE_OUT} ({len(cookies)} 条)", flush=True)
